#!/usr/bin/env python3
"""Compose the main visual, title, corner copy, logo, and QR into one poster."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat


BASE_SIZE = (1080, 2333)
LOGO_BOX = (398, 162, 268, 48)
TITLE_BOX = (90, 280, 840, 700)
COPY_BOX = (96, 2048, 600, 148)
QR_BOX = (788, 1982, 176, 208)
SKILL_DIR = Path(__file__).resolve().parents[1]
BRAND_DIR = SKILL_DIR / "assets" / "brand"
BUNDLED_COPY_FONT = SKILL_DIR / "assets" / "fonts" / "AlimamaFangYuanTiVF-Thin.ttf"
DEFAULT_COPY_FONT = (
    BUNDLED_COPY_FONT
    if BUNDLED_COPY_FONT.exists()
    else Path.home() / "Library/Fonts/AlimamaFangYuanTiVF-Thin.ttf"
)


def parse_box(value: str) -> tuple[int, int, int, int]:
    try:
        box = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Box must be x,y,w,h integers.") from error
    if len(box) != 4 or any(part < 0 for part in box) or min(box[2:]) == 0:
        raise argparse.ArgumentTypeError("Box requires non-negative x,y and positive w,h.")
    return box


def parse_size(value: str) -> tuple[int, int]:
    try:
        width, height = (int(part) for part in value.lower().split("x", 1))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Size must be WIDTHxHEIGHT.") from error
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Size values must be positive.")
    if abs(width / height - BASE_SIZE[0] / BASE_SIZE[1]) > 0.002:
        raise argparse.ArgumentTypeError("Size must keep the 1080:2333 aspect ratio.")
    return width, height


def load_rgba(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Asset does not exist: {path}")
    with Image.open(path) as image:
        return image.convert("RGBA")


def cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_ratio = size[0] / size[1]
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        crop_width = round(image.height * target_ratio)
        left = (image.width - crop_width) // 2
        image = image.crop((left, 0, left + crop_width, image.height))
    elif source_ratio < target_ratio:
        crop_height = round(image.width / target_ratio)
        top = (image.height - crop_height) // 2
        image = image.crop((0, top, image.width, top + crop_height))
    return image.resize(size, Image.Resampling.LANCZOS)


def scale_box(box: tuple[int, int, int, int], size: tuple[int, int]) -> tuple[int, int, int, int]:
    scale = size[0] / BASE_SIZE[0]
    return tuple(round(value * scale) for value in box)


def paste_contained(
    canvas: Image.Image,
    asset: Image.Image,
    box: tuple[int, int, int, int],
) -> None:
    x, y, width, height = box
    fitted = ImageOps.contain(asset, (width, height), Image.Resampling.LANCZOS)
    canvas.alpha_composite(
        fitted,
        (x + (width - fitted.width) // 2, y + (height - fitted.height) // 2),
    )


def trim_alpha(image: Image.Image) -> Image.Image:
    bounds = image.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError("Title artwork contains no visible pixels.")
    return image.crop(bounds)


def key_solid_background(image: Image.Image, color: str, tolerance: int = 24) -> Image.Image:
    target = ImageColor.getrgb(color)
    channels = image.convert("RGBA").split()
    differences = [
        ImageChops.difference(channel, Image.new("L", image.size, target_value))
        for channel, target_value in zip(channels[:3], target)
    ]
    distance = ImageChops.lighter(ImageChops.lighter(differences[0], differences[1]), differences[2])
    feather = max(4, tolerance // 2)
    mask = distance.point(
        lambda value: 0
        if value <= tolerance
        else 255
        if value >= tolerance + feather
        else round((value - tolerance) * 255 / feather)
    )
    result = image.convert("RGBA")
    result.putalpha(ImageChops.multiply(channels[3], mask))
    return result


def key_neutral_checkerboard(image: Image.Image) -> Image.Image:
    result = image.convert("RGBA")
    red, green, blue, original_alpha = result.split()
    maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    minimum = ImageChops.darker(ImageChops.darker(red, green), blue)
    colorfulness = ImageChops.subtract(maximum, minimum)
    mask = colorfulness.point(
        lambda value: 0 if value <= 3 else 255 if value >= 20 else round((value - 3) * 255 / 17)
    ).filter(ImageFilter.GaussianBlur(0.6))
    visible = mask.getbbox()
    if visible is None:
        raise ValueError(
            "The title has no real alpha and no separable colored strokes. "
            "Regenerate it on a solid key color or use --title-text with --title-font."
        )
    result.putalpha(ImageChops.multiply(original_alpha, mask))
    return result


def prepare_title(path: Path, background: str) -> Image.Image:
    title = load_rgba(path)
    alpha_min, alpha_max = title.getchannel("A").getextrema()
    if alpha_max == 0:
        raise ValueError("Title artwork is fully transparent.")
    if alpha_min < 250:
        return trim_alpha(title)
    if background != "auto":
        title = key_solid_background(title, background)
    else:
        title = key_neutral_checkerboard(title)
    return trim_alpha(title)


def load_font(path: Path, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(f"Font does not exist: {path}")
    font = ImageFont.truetype(str(path), size)
    if bold and hasattr(font, "get_variation_axes"):
        axes = font.get_variation_axes()
        if axes:
            font.set_variation_by_axes([axis["maximum"] for axis in axes])
    return font


def fit_font(
    text: str,
    path: Path,
    target_size: int,
    max_width: int,
    bold: bool = False,
) -> ImageFont.FreeTypeFont:
    size = target_size
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    while size >= 16:
        font = load_font(path, size, bold)
        if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
            return font
        size -= 2
    raise ValueError(f"Text cannot fit the configured box: {text}")


def draw_fallback_title(
    canvas: Image.Image,
    text: str,
    font_path: Path,
    box: tuple[int, int, int, int],
    color: str,
) -> None:
    x, y, width, height = box
    lines = text.replace("\\n", "\n").splitlines()
    draw = ImageDraw.Draw(canvas)
    font = fit_font(max(lines, key=len), font_path, min(360, height), width)
    bounds = draw.multiline_textbbox((0, 0), "\n".join(lines), font=font, spacing=8, align="center")
    text_width = bounds[2] - bounds[0]
    text_height = bounds[3] - bounds[1]
    draw.multiline_text(
        (x + (width - text_width) // 2, y + (height - text_height) // 2),
        "\n".join(lines),
        font=font,
        fill=color,
        spacing=8,
        align="center",
    )


def draw_corner_copy(
    canvas: Image.Image,
    text: str,
    font_path: Path,
    box: tuple[int, int, int, int],
    scale: float,
) -> None:
    lines = [line.strip() for line in text.replace("\\n", "\n").splitlines() if line.strip()]
    if not lines:
        return
    x, y, width, height = box
    # Historical Sunny & Molly posters keep every copy line at the same level:
    # 43 px on the 1080 px master, with a compact 12 px leading gap.
    sizes = [round(43 * scale)] * len(lines)
    fonts = [fit_font(line, font_path, size, width, bold=True) for line, size in zip(lines, sizes)]
    gap = round(12 * scale)
    measure = ImageDraw.Draw(canvas)
    line_bounds = [measure.textbbox((0, 0), line, font=font) for line, font in zip(lines, fonts)]
    line_heights = [bounds[3] - bounds[1] for bounds in line_bounds]
    total_height = sum(line_heights) + gap * (len(lines) - 1)
    positions: list[tuple[int, int]] = []
    visible_top = y + max(0, height - total_height)
    for bounds, line_height in zip(line_bounds, line_heights):
        positions.append((x, visible_top - bounds[1]))
        visible_top += line_height + gap

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    for position, line, font in zip(positions, lines, fonts):
        shadow_draw.text(
            (position[0], position[1] + round(2 * scale)),
            line,
            font=font,
            fill=(20, 28, 30, 88),
        )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(max(1, round(3 * scale)))))

    draw = ImageDraw.Draw(canvas)
    for position, line, font in zip(positions, lines, fonts):
        draw.text(
            position,
            line,
            font=font,
            fill=(255, 253, 247, 255),
        )


def select_logo(canvas: Image.Image, requested: str, box: tuple[int, int, int, int]) -> Path:
    if requested not in {"auto", "white", "dark"}:
        return Path(requested).expanduser()
    choice = requested
    if choice == "auto":
        x, y, width, height = box
        mean = ImageStat.Stat(canvas.crop((x, y, x + width, y + height)).convert("RGB")).mean
        luminance = 0.2126 * mean[0] + 0.7152 * mean[1] + 0.0722 * mean[2]
        choice = "dark" if luminance >= 150 else "white"
    return BRAND_DIR / ("logo-dark-gray.png" if choice == "dark" else "logo-white.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=parse_size, default=BASE_SIZE)
    title = parser.add_mutually_exclusive_group(required=True)
    title.add_argument("--title-art", type=Path)
    title.add_argument("--title-text")
    parser.add_argument("--title-font", type=Path)
    parser.add_argument("--title-color", default="#FFFDF4")
    parser.add_argument("--title-bg", default="auto", help="auto or a solid #RRGGBB key color.")
    parser.add_argument("--title-box", type=parse_box, default=TITLE_BOX)
    parser.add_argument("--copy", help=r"Lower-left copy. Use \n for a line break.")
    parser.add_argument("--copy-font", type=Path, default=DEFAULT_COPY_FONT)
    parser.add_argument("--copy-box", type=parse_box, default=COPY_BOX)
    parser.add_argument("--logo", default="auto", help="auto, white, dark, or a PNG path.")
    parser.add_argument("--qr", default="auto", help="auto or a QR PNG path.")
    parser.add_argument("--no-brand", action="store_true")
    parser.add_argument("--quality", type=int, default=95)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    canvas = cover_resize(load_rgba(args.input), args.size)
    scale = args.size[0] / BASE_SIZE[0]

    if args.title_art:
        paste_contained(
            canvas,
            prepare_title(args.title_art, args.title_bg),
            scale_box(args.title_box, args.size),
        )
    else:
        if args.title_font is None:
            raise ValueError("--title-text requires --title-font.")
        draw_fallback_title(
            canvas,
            args.title_text,
            args.title_font,
            scale_box(args.title_box, args.size),
            args.title_color,
        )

    if args.copy:
        draw_corner_copy(
            canvas,
            args.copy,
            args.copy_font.expanduser(),
            scale_box(args.copy_box, args.size),
            scale,
        )

    if not args.no_brand:
        logo_box = scale_box(LOGO_BOX, args.size)
        qr_box = scale_box(QR_BOX, args.size)
        paste_contained(canvas, load_rgba(select_logo(canvas, args.logo, logo_box)), logo_box)
        qr_path = BRAND_DIR / "qr-module.png" if args.qr == "auto" else Path(args.qr).expanduser()
        paste_contained(canvas, load_rgba(qr_path), qr_box)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() in {".jpg", ".jpeg"}:
        rgb = Image.new("RGB", canvas.size, "white")
        rgb.paste(canvas, mask=canvas.getchannel("A"))
        rgb.save(args.output, quality=args.quality, subsampling=0)
    else:
        canvas.save(args.output)
    print(f"saved={args.output} size={canvas.width}x{canvas.height}")


if __name__ == "__main__":
    main()
