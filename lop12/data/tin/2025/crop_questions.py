#!/usr/bin/env python3.11
"""Re-crop Tin học 2025 exam questions from page images."""

from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parent
PAGES = BASE / "pages"
OUT = BASE / "crops"

LEFT = 78
RIGHT = 1110
TOP_PAD = 6
BOTTOM_PAD = 10

# (output_id, [(page_number, y_start, y_end), ...])
REGIONS = {
  "y25i1": [(1, 305, 339)],
  "y25i2": [(1, 339, 427)],
  "y25i3": [(1, 427, 571)],
  "y25i4": [(1, 571, 731)],
  "y25i5": [(1, 731, 779)],
  "y25i6": [(1, 779, 843)],
  "y25i7": [(1, 843, 1067)],
  "y25i8": [(1, 1067, 1219)],
  "y25i9": [(1, 1219, 1299)],
  "y25i10": [(1, 1299, 1363)],
  "y25i11": [(1, 1363, 1510)],
  "y25i12": [(1, 1520, 1570), (2, 60, 186)],
  "y25i13": [(2, 187, 323)],
  "y25i14": [(2, 323, 467)],
  "y25i15": [(2, 467, 579)],
  "y25i16": [(2, 579, 699)],
  "y25i17": [(2, 699, 947)],
  "y25i18": [(2, 955, 1163)],
  "y25i19": [(2, 1163, 1307)],
  "y25i20": [(2, 1307, 1403)],
  "y25i21": [(2, 1403, 1491)],
  "y25i22": [(2, 1491, 1615)],
  "y25i23": [(3, 75, 159)],
  "y25i24": [(3, 159, 330)],
  "y25i25": [(3, 395, 707)],
  "y25i26": [(3, 707, 1205)],
  "y25i27": [(4, 675, 927)],
  "y25i28": [(4, 927, 1375)],
}


def load_page(page_num: int) -> Image.Image:
  return Image.open(PAGES / f"page-{page_num}.png")


def crop_region(page: Image.Image, y0: int, y1: int) -> Image.Image:
  y0 = max(0, y0 - TOP_PAD)
  y1 = min(page.height, y1 + BOTTOM_PAD)
  return page.crop((LEFT, y0, RIGHT, y1))


def stitch(parts: list[Image.Image]) -> Image.Image:
  width = max(part.width for part in parts)
  height = sum(part.height for part in parts)
  canvas = Image.new("RGB", (width, height), "white")
  y = 0
  for part in parts:
    canvas.paste(part, (0, y))
    y += part.height
  return canvas


def main() -> None:
  OUT.mkdir(parents=True, exist_ok=True)
  page_cache: dict[int, Image.Image] = {}

  for name, regions in REGIONS.items():
    parts = []
    for page_num, y0, y1 in regions:
      if page_num not in page_cache:
        page_cache[page_num] = load_page(page_num)
      parts.append(crop_region(page_cache[page_num], y0, y1))

    image = parts[0] if len(parts) == 1 else stitch(parts)
    out_path = OUT / f"{name}.png"
    image.save(out_path)
    print(f"{name}: {image.size[0]}x{image.size[1]}")


if __name__ == "__main__":
  main()
