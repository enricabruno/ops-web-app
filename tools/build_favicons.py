"""Genera favicon.ico e varianti PNG a partire da static/img/logo.png.

Da eseguire manualmente dopo ogni modifica di logo.png:
    python3 tools/build_favicons.py
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, 'static', 'img')
SOURCE = os.path.join(IMG_DIR, 'logo.png')

PNG_SIZES = (16, 32, 48)
ICO_SIZES = [(16, 16), (32, 32), (48, 48)]
APPLE_TOUCH_SIZE = 180


def make_png_variants(source: Image.Image) -> dict:
    variants = {}
    for size in PNG_SIZES:
        resized = source.resize((size, size), Image.LANCZOS)
        out_path = os.path.join(IMG_DIR, f'favicon-{size}.png')
        resized.save(out_path, format='PNG', interlace=False, optimize=True)
        variants[size] = resized
        print(f'  {out_path}')
    return variants


def make_apple_touch_icon(source: Image.Image) -> None:
    resized = source.resize((APPLE_TOUCH_SIZE, APPLE_TOUCH_SIZE), Image.LANCZOS)
    background = Image.new('RGBA', resized.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(background, resized).convert('RGB')
    out_path = os.path.join(IMG_DIR, 'apple-touch-icon.png')
    composited.save(out_path, format='PNG', optimize=True)
    print(f'  {out_path}')


def make_favicon_ico(source: Image.Image) -> None:
    out_path = os.path.join(IMG_DIR, 'favicon.ico')
    source.save(out_path, format='ICO', sizes=ICO_SIZES)
    print(f'  {out_path}')


def main() -> None:
    source = Image.open(SOURCE).convert('RGBA')

    print('Genero PNG favicon...')
    make_png_variants(source)

    print('Genero apple-touch-icon...')
    make_apple_touch_icon(source)

    print('Genero favicon.ico multi-risoluzione...')
    make_favicon_ico(source)

    print('Fatto.')


if __name__ == '__main__':
    main()
