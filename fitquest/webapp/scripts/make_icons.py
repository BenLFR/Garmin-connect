"""Generate the PWA icons from the hero pixel sprite (one-shot).

    cd fitquest/webapp && python scripts/make_icons.py

The 16x16 map + rodeur palette are duplicated from src/sprites.jsx on
purpose: the generated PNGs are committed, so this script only runs when
the sprite changes — no build-time dependency on Pillow.
"""

from pathlib import Path

from PIL import Image

HERO_MAP = [
    '....HHHHHH......',
    '...HHHHHHHH.....',
    '..HHHHHHHHHH....',
    '..HHSSSSSSHH....',
    '..HSSESSESSH....',
    '...SSSSSSSS.....',
    '....SSSSSS......',
    '..CCCCCCCCCC....',
    '.CCCCCCCCCCCC...',
    '.CWWCCCCCCWWC...',
    '.CWWCCCCCCWWC...',
    '..CBBBBBBBBC....',
    '...LLL..LLL.....',
    '...LLL..LLL.....',
    '...OOO..OOO.....',
    '..OOOO..OOOO....',
]

PALETTE = {  # rodeur
    'H': '#1f8f74', 'C': '#14513f', 'B': '#0d3328', 'L': '#1c2a24',
    'O': '#3ee6c1', 'W': '#3ee6c1', 'S': '#e8b88a', 'E': '#101528',
}
BG = '#0b0e1a'

OUT = Path(__file__).resolve().parent.parent / 'public' / 'icons'


def _hex(color: str):
    color = color.lstrip('#')
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def sprite_16() -> Image.Image:
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(HERO_MAP):
        for x, ch in enumerate(row):
            if ch in PALETTE:
                img.putpixel((x, y), _hex(PALETTE[ch]))
    return img


def icon(size: int, sprite_share: float) -> Image.Image:
    """Sprite centered on the abyss background, nearest-neighbour upscale."""
    img = Image.new('RGBA', (size, size), _hex(BG))
    sprite_px = int(size * sprite_share) // 16 * 16  # multiple of 16: crisp
    sprite = sprite_16().resize((sprite_px, sprite_px), Image.NEAREST)
    off = (size - sprite_px) // 2
    img.alpha_composite(sprite, (off, off))
    return img


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    icon(192, 0.85).save(OUT / 'icon-192.png')
    icon(512, 0.85).save(OUT / 'icon-512.png')
    icon(512, 0.60).save(OUT / 'maskable-512.png')  # safe zone for masks
    icon(180, 0.85).save(OUT / 'apple-touch-icon.png')
    print(f'✓ icons written to {OUT}')
