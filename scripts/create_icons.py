#!/usr/bin/env python3
"""
Create application icons for Windows (.ico) and macOS (.icns).

This script generates placeholder icons. For production, replace with
professionally designed icons.

Requirements:
    pip install Pillow

Usage:
    python scripts/create_icons.py
"""

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required: pip install Pillow")
    sys.exit(1)


def create_icon_image(size: int) -> Image.Image:
    """Create a simple icon image with PDF text."""
    # Create image with gradient background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background
    padding = size // 10
    radius = size // 5

    # Background gradient simulation (solid color for simplicity)
    bg_color = (41, 98, 255)  # Blue
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=radius,
        fill=bg_color
    )

    # Draw "PDF" text
    font_size = size // 3
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

    text = "PDF"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size - text_width) // 2
    y = (size - text_height) // 2 - size // 10

    draw.text((x, y), text, fill=(255, 255, 255), font=font)

    # Draw extraction arrow
    arrow_y = y + text_height + size // 15
    arrow_size = size // 6
    arrow_x = size // 2

    # Arrow pointing right
    arrow_points = [
        (arrow_x - arrow_size, arrow_y),
        (arrow_x + arrow_size // 2, arrow_y),
        (arrow_x + arrow_size // 2, arrow_y - arrow_size // 2),
        (arrow_x + arrow_size, arrow_y + arrow_size // 4),
        (arrow_x + arrow_size // 2, arrow_y + arrow_size),
        (arrow_x + arrow_size // 2, arrow_y + arrow_size // 2),
        (arrow_x - arrow_size, arrow_y + arrow_size // 2),
    ]
    draw.polygon(arrow_points, fill=(255, 255, 255))

    return img


def create_ico(output_path: Path):
    """Create Windows .ico file with multiple sizes."""
    sizes = [16, 32, 48, 64, 128, 256]
    images = [create_icon_image(size) for size in sizes]

    # Save as ICO
    images[0].save(
        output_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    print(f"Created: {output_path}")


def create_icns(output_path: Path):
    """Create macOS .icns file."""
    # macOS icon sizes
    sizes = [16, 32, 64, 128, 256, 512, 1024]

    # Create iconset directory
    iconset_dir = output_path.parent / "icon.iconset"
    iconset_dir.mkdir(exist_ok=True)

    for size in sizes:
        img = create_icon_image(size)

        # Standard resolution
        img.save(iconset_dir / f"icon_{size}x{size}.png")

        # Retina (@2x) - use next size up
        if size <= 512:
            img_2x = create_icon_image(size * 2)
            img_2x.save(iconset_dir / f"icon_{size}x{size}@2x.png")

    print(f"Created iconset: {iconset_dir}")
    print(f"To create .icns on macOS, run:")
    print(f"  iconutil -c icns {iconset_dir}")

    # Also save a PNG for reference
    png_path = output_path.parent / "icon.png"
    create_icon_image(512).save(png_path)
    print(f"Created reference PNG: {png_path}")


def main():
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    assets_dir = project_root / "assets"
    assets_dir.mkdir(exist_ok=True)

    print("Creating application icons...")
    print()

    # Create Windows icon
    create_ico(assets_dir / "icon.ico")

    # Create macOS iconset (needs iconutil on Mac to convert to .icns)
    create_icns(assets_dir / "icon.icns")

    print()
    print("Done!")
    print()
    print("Note: These are placeholder icons. For production, replace with")
    print("professionally designed icons in the assets/ directory.")


if __name__ == "__main__":
    main()
