"""Forced alignment: MFA, Gentle, or proportional fallback."""

import json
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import requests

from config import ALIGNMENT_METHOD, GENTLE_URL, MFA_MODEL_DIR
from services.phoneme_utils import ipa_from_word_data


class BaseAligner(ABC):
    @abstractmethod
    def align(
        self,
        wav_path: Path,
        word: str,
        ipa: str,
        phonemes: list[str],
    ) -> list[dict]:
        """Return list of {ipa, start, end}."""
        ...


class FallbackAligner(BaseAligner):
    """Proportional time-split when no aligner is installed."""

    def align(self, wav_path: Path, word: str, ipa: str, phonemes: list[str]) -> list[dict]:
        from services.audio_processor import get_duration

        if not phonemes:
            phonemes = ipa_from_word_data(word, ipa, None)

        duration = get_duration(wav_path)
        if not phonemes:
            return [{"ipa": word, "start": 0.0, "end": duration}]

        # Weight vowels slightly longer
        weights = []
        for p in phonemes:
            if p in "aeiouɑæɛɪʌɜːɔʊuːaʊaɪeɪoʊɔɪ":
                weights.append(1.4)
            else:
                weights.append(1.0)
        total_w = sum(weights)
        segments = []
        t = 0.0
        for p, w in zip(phonemes, weights):
            seg_dur = (w / total_w) * duration
            segments.append({"ipa": p, "start": t, "end": t + seg_dur})
            t += seg_dur
        return segments


class GentleAligner(BaseAligner):
    """Align via Gentle HTTP API (localhost:8765)."""

    def align(self, wav_path: Path, word: str, ipa: str, phonemes: list[str]) -> list[dict]:
        if not phonemes:
            phonemes = ipa_from_word_data(word, ipa, None)

        with open(wav_path, "rb") as f:
            resp = requests.post(
                f"{GENTLE_URL}/transcriptions?async=false",
                files={"audio": f},
                data={"transcript": word},
                timeout=30,
            )
        resp.raise_for_status()
        data = resp.json()

        words = data.get("words", [])
        if not words:
            return FallbackAligner().align(wav_path, word, ipa, phonemes)

        # Map Gentle phone-level output if available
        segments = []
        for w in words:
            phones = w.get("phones", [])
            if phones:
                for ph in phones:
                    segments.append({
                        "ipa": ph.get("phone", "?"),
                        "start": ph.get("start", 0),
                        "end": ph.get("end", 0),
                    })
            elif w.get("case") == "success":
                segments.append({
                    "ipa": w.get("word", "?"),
                    "start": w.get("start", 0),
                    "end": w.get("end", 0),
                })

        if len(segments) != len(phonemes) and phonemes:
            return FallbackAligner().align(wav_path, word, ipa, phonemes)
        return segments or FallbackAligner().align(wav_path, word, ipa, phonemes)


class MFAAligner(BaseAligner):
    """Align via Montreal Forced Aligner CLI."""

    def align(self, wav_path: Path, word: str, ipa: str, phonemes: list[str]) -> list[dict]:
        if not phonemes:
            phonemes = ipa_from_word_data(word, ipa, None)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            corpus = tmp_path / "corpus"
            corpus.mkdir()
            wav_copy = corpus / f"{word}.wav"
            wav_copy.write_bytes(wav_path.read_bytes())

            lab_file = corpus / f"{word}.lab"
            lab_file.write_text(word)

            out_dir = tmp_path / "output"
            cmd = [
                "mfa", "align",
                str(corpus),
                "english_us_arpa",
                "english_us_arpa",
                str(out_dir),
            ]
            if MFA_MODEL_DIR:
                cmd = [
                    "mfa", "align",
                    str(corpus),
                    MFA_MODEL_DIR,
                    MFA_MODEL_DIR,
                    str(out_dir),
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return FallbackAligner().align(wav_path, word, ipa, phonemes)

            textgrid = out_dir / f"{word}.TextGrid"
            if not textgrid.exists():
                return FallbackAligner().align(wav_path, word, ipa, phonemes)

            return self._parse_textgrid(textgrid, phonemes)

    def _parse_textgrid(self, path: Path, phonemes: list[str]) -> list[dict]:
        import re
        content = path.read_text(encoding="utf-8", errors="ignore")
        segments = []
        in_phone_tier = False
        xmin = xmax = 0.0
        for line in content.splitlines():
            lower = line.lower()
            if "phones" in lower:
                in_phone_tier = True
            if in_phone_tier and "xmin" in line:
                m = re.search(r"[\d.]+", line)
                if m:
                    xmin = float(m.group())
            elif in_phone_tier and "xmax" in line:
                m = re.search(r"[\d.]+", line)
                if m:
                    xmax = float(m.group())
            elif in_phone_tier and 'text = "' in line:
                label = line.split('text = "')[1].rstrip('"\n')
                if label and label not in ("", "sil", "sp", "spn"):
                    segments.append({"ipa": label, "start": xmin, "end": xmax})

        if not segments:
            return FallbackAligner().align(
                path.parent.parent / "corpus" / f"{path.stem}.wav",
                path.stem, "", phonemes,
            )
        return segments


def get_aligner() -> BaseAligner:
    method = ALIGNMENT_METHOD.lower()
    if method == "gentle":
        return GentleAligner()
    if method == "mfa":
        return MFAAligner()
    return FallbackAligner()
