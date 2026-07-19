#!/usr/bin/env python3
"""Link or copy listening MP3 files into public/audio/ with Live Server-friendly names."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "data" / "AUDIO HACKER"
DST_DIR = ROOT / "public" / "audio"

# Source filenames in data/AUDIO HACKER (Test 8 uses different casing)
SOURCE_NAMES = {
    1: "TEST 1.mp3",
    2: "TEST 2.mp3",
    3: "TEST 3.mp3",
    4: "TEST 4.mp3",
    5: "TEST 5.mp3",
    6: "TEST 6.mp3",
    7: "TEST 7.mp3",
    8: "Test 8.mp3",
    9: "TEST 9.mp3",
    10: "TEST 10.mp3",
}


def setup():
    DST_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old symlinks / legacy names with spaces
    for old in DST_DIR.glob("*.mp3"):
        if old.name.startswith("test"):
            continue
        old.unlink(missing_ok=True)

    ok = 0
    for num, src_name in SOURCE_NAMES.items():
        src = SRC_DIR / src_name
        dst = DST_DIR / f"test{num:02d}.mp3"
        if not src.exists():
            print(f"  SKIP test{num:02d}: missing {src}")
            continue
        dst.unlink(missing_ok=True)
        try:
            dst.hardlink_to(src)
            mode = "hardlink"
        except OSError:
            shutil.copy2(src, dst)
            mode = "copy"
        size_mb = dst.stat().st_size / (1024 * 1024)
        print(f"  test{num:02d}.mp3 ← {src_name} ({mode}, {size_mb:.1f} MB)")
        ok += 1

    print(f"\nDone: {ok}/10 audio files ready in public/audio/")
    return ok


if __name__ == "__main__":
    setup()
