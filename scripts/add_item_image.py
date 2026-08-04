"""Normalize an item photo to the project convention and install it.

Convention: 4:3 landscape, 960×720, JPEG quality 85, white background.
The homepage card frame is 4:3 (`aspect-ratio: 4/3` in style.css), so a
normalized image is never cropped or letterboxed when rendered.

Usage:
    uv run python scripts/add_item_image.py <source-image> <slug>
    uv run python scripts/add_item_image.py ~/Downloads/shrimp-photo.png shrimp

Writes app/static/images/items/<slug>.jpg and prints the CSV path to put in
the `picture_of_items` column. Pass --replace to overwrite an existing file.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

TARGET_WIDTH = 960
TARGET_HEIGHT = 720
JPEG_QUALITY = 85
ITEMS_DIR = Path(__file__).resolve().parent.parent / "app" / "static" / "images" / "items"


def normalize(source: Path) -> Image.Image:
    image = Image.open(source)

    # Flatten transparency (PNG cutouts) onto white so it blends with the card.
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    else:
        image = image.convert("RGB")

    # Center-crop to 4:3, then resize to the target dimensions.
    width, height = image.size
    target_ratio = TARGET_WIDTH / TARGET_HEIGHT
    if width / height > target_ratio:
        crop_width = round(height * target_ratio)
        left = (width - crop_width) // 2
        image = image.crop((left, 0, left + crop_width, height))
    else:
        crop_height = round(width / target_ratio)
        top = (height - crop_height) // 2
        image = image.crop((0, top, width, top + crop_height))

    return image.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="Path to the downloaded image")
    parser.add_argument("slug", help="Output name, e.g. 'shrimp' -> shrimp.jpg")
    parser.add_argument("--replace", action="store_true", help="Overwrite an existing image")
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Source image not found: {args.source}", file=sys.stderr)
        return 1

    destination = ITEMS_DIR / f"{args.slug}.jpg"
    if destination.exists() and not args.replace:
        print(f"{destination} already exists — pass --replace to overwrite.", file=sys.stderr)
        return 1

    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    normalize(args.source).save(destination, "JPEG", quality=JPEG_QUALITY, optimize=True)

    print(f"Saved {destination} ({TARGET_WIDTH}x{TARGET_HEIGHT})")
    print(f"CSV picture_of_items value: /static/images/items/{args.slug}.jpg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
