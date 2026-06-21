"""Evaluate pronunciation API endpoint."""

import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.evaluator import evaluate_pronunciation

router = APIRouter()


@router.post("/evaluate")
async def evaluate(
    file: UploadFile = File(...),
    target_word: str = Form(...),
    target_ipa: str = Form(""),
    target_phonemes: str = Form(""),
):
    """
    Evaluate pronunciation from uploaded audio.

    multipart/form-data:
      - file: audio (webm/wav)
      - target_word: expected word
      - target_ipa: IPA transcription
      - target_phonemes: JSON array or comma-separated phonemes
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail={"error": "No audio file provided"})

    allowed = {".webm", ".wav", ".ogg", ".mp3", ".m4a", ".mp4"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Unsupported format: {ext}. Use webm or wav."},
        )

    if not target_word.strip():
        raise HTTPException(status_code=400, detail={"error": "target_word is required"})

    # Parse phonemes if JSON
    phonemes_raw = target_phonemes
    if target_phonemes.strip().startswith("["):
        try:
            phonemes_raw = json.loads(target_phonemes)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail={"error": "Invalid target_phonemes JSON"})

    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        if len(content) < 100:
            raise HTTPException(status_code=400, detail={"error": "Audio file too short"})
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        result = evaluate_pronunciation(
            tmp_path,
            target_word.strip(),
            target_ipa.strip(),
            phonemes_raw,
            file.filename,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Processing failed: {e}"})
    finally:
        tmp_path.unlink(missing_ok=True)
