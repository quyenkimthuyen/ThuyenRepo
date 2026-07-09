#!/usr/bin/env python3.11
"""Crop code/table images for Tin học 2025 questions."""

from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parent
PAGES = BASE / "pages"
OUT = BASE / "images"

# (page, left, top, right, bottom)
CODE_REGIONS = {
  "q18": (2, 52, 992, 1138, 1126),
}


def main() -> None:
  OUT.mkdir(parents=True, exist_ok=True)

  for name, (page_num, left, top, right, bottom) in CODE_REGIONS.items():
    page = Image.open(PAGES / f"page-{page_num}.png")
    image = page.crop((left, top, right, bottom))
    image.save(OUT / f"{name}.png")
    print(f"{name}: {image.size[0]}x{image.size[1]}")


if __name__ == "__main__":
  main()
