"""
Generates icon.ico and icon.png for Cryptogreek.

Pillow-only (no cairo / no SVG renderer needed). Draws the icon by
compositing layers: dark hexagon, gold rim, wine ring, Greek key motif,
glowing gold Phi in the center.
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------- Palette ----------
INK_DARK    = (10, 8, 6)
INK_LIGHT   = (42, 34, 24)
GOLD        = (201, 169, 97)
GOLD_BRIGHT = (243, 217, 138)
GOLD_DEEP   = (138, 111, 58)
WINE        = (107, 31, 31)


def hex_points(cx, cy, r):
    pts = []
    for i in range(6):
        a = math.radians(60 * i - 30)   # flat sides top/bottom
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def radial_fill(size, color_inner, color_outer):
    """Radial gradient `size x size` RGBA, inner color at center."""
    img = Image.new("RGBA", (size, size), color_outer + (255,))
    px = img.load()
    cx = cy = size / 2
    max_d = math.hypot(cx, cy)
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - cx, y - cy) / max_d
            d = max(0.0, min(1.0, d))
            r = int(color_inner[0] * (1 - d) + color_outer[0] * d)
            g = int(color_inner[1] * (1 - d) + color_outer[1] * d)
            b = int(color_inner[2] * (1 - d) + color_outer[2] * d)
            px[x, y] = (r, g, b, 255)
    return img


def find_font(candidates, size):
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def draw_meander(draw, x, y, units, unit_w, unit_h, color, width, mirror=False):
    for i in range(units):
        ux = x + i * unit_w
        if mirror:
            pts = [(ux, y), (ux, y + unit_h - 4), (ux + 14, y + unit_h - 4),
                   (ux + 14, y), (ux + 6, y), (ux + 6, y + 6)]
        else:
            pts = [(ux, y + unit_h), (ux, y + 4), (ux + 14, y + 4),
                   (ux + 14, y + unit_h), (ux + 6, y + unit_h), (ux + 6, y + 8)]
        draw.line(pts, fill=color, width=width, joint="curve")


def render(size: int) -> Image.Image:
    # Supersample to 1024-2048px internal, downsample with Lanczos.
    # Small icons get the most supersampling (4x or 8x); big ones less
    # (since they're already large), but we never go below 1024 internal.
    target_internal = max(size * 4, 1024)
    if target_internal > 2048:
        target_internal = 2048
    scale = max(1, target_internal // size)
    S = size * scale
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Dark hex with radial sheen
    sheen = radial_fill(S, INK_LIGHT, INK_DARK)
    mask = Image.new("L", (S, S), 0)
    mdraw = ImageDraw.Draw(mask)
    outer_r = S * 0.47
    outer_pts = hex_points(S / 2, S / 2, outer_r)
    mdraw.polygon(outer_pts, fill=255)
    canvas.paste(sheen, (0, 0), mask)

    draw = ImageDraw.Draw(canvas)

    # Gold rim
    draw.line(outer_pts + [outer_pts[0]], fill=GOLD, width=max(2, S // 64))
    inner_rim_pts = hex_points(S / 2, S / 2, outer_r * 0.92)
    draw.line(inner_rim_pts + [inner_rim_pts[0]],
              fill=GOLD_DEEP, width=max(1, S // 200))

    # Wine ring
    wine_pts = hex_points(S / 2, S / 2, outer_r * 0.78)
    draw.line(wine_pts + [wine_pts[0]], fill=WINE, width=max(1, S // 180))

    # Meander (only at sizes that can show it)
    if size >= 48:
        unit_w = max(8, S // 28)
        unit_h = max(6, S // 36)
        line_w = max(1, S // 200)
        units = 5
        total_w = unit_w * units
        top_y = int(S * 0.20)
        bot_y = int(S * 0.74)
        mx = (S - total_w) // 2
        draw_meander(draw, mx, top_y, units, unit_w, unit_h, GOLD, line_w)
        draw_meander(draw, mx, bot_y, units, unit_w, unit_h, GOLD, line_w,
                     mirror=True)

    # Soft gold glow behind Phi
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([S * 0.22, S * 0.22, S * 0.78, S * 0.78],
                  fill=(GOLD[0], GOLD[1], GOLD[2], 80))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=S // 20))
    canvas = Image.alpha_composite(canvas, glow)
    draw = ImageDraw.Draw(canvas)

    # The big Phi
    font_candidates = [
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/georgia.ttf",
        "C:/Windows/Fonts/timesbd.ttf",
        "C:/Windows/Fonts/times.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "DejaVuSerif-Bold.ttf",
    ]
    font_size = int(S * 0.60)
    font = find_font(font_candidates, font_size)

    text = "Φ"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (S - tw) // 2 - bbox[0]
    ty = (S - th) // 2 - bbox[1]

    # Embossed dark stroke, then gold body
    offset = max(1, S // 200)
    for dx, dy in [(-offset, -offset), (offset, offset),
                   (-offset, offset), (offset, -offset)]:
        draw.text((tx + dx, ty + dy), text, font=font, fill=(40, 30, 16, 255))
    draw.text((tx, ty), text, font=font, fill=GOLD_BRIGHT)

    # Tiny flourish
    if size >= 32:
        flourish_font = find_font(font_candidates, max(8, S // 18))
        ftext = "·❦·"
        fbbox = draw.textbbox((0, 0), ftext, font=flourish_font)
        fw = fbbox[2] - fbbox[0]
        fx = (S - fw) // 2 - fbbox[0]
        fy = int(S * 0.13)
        draw.text((fx, fy), ftext, font=flourish_font, fill=GOLD)

    if scale > 1:
        canvas = canvas.resize((size, size), Image.LANCZOS)
    return canvas


def main():
    here = os.path.dirname(os.path.abspath(__file__))

    # Embed every standard Windows icon size up to 256.  Windows picks the
    # closest match for each context (16 for the title bar, 32-40 for the
    # taskbar, 256 for the "Extra Large icons" view in Explorer).
    ico_sizes = [16, 24, 32, 48, 64, 96, 128, 192, 256]
    images = [render(s) for s in ico_sizes]
    ico_path = os.path.join(here, "icon.ico")
    images[-1].save(ico_path, format="ICO", sizes=[(s, s) for s in ico_sizes])
    print(f"Wrote {ico_path} ({len(ico_sizes)} embedded sizes)")

    # A big PNG for previews and for Chrome's --app= window icon. Chrome can
    # use a high-res PNG via <link rel="icon"> and downsample it crisply
    # for the taskbar; that looks sharper than the legacy ICO scaling.
    for sz in (256, 512, 1024):
        p = os.path.join(here, f"icon-{sz}.png")
        render(sz).save(p)
        print(f"Wrote {p}")

    # Convenience copy at the default name.
    render(512).save(os.path.join(here, "icon.png"))
    print(f"Wrote {os.path.join(here, 'icon.png')}")


if __name__ == "__main__":
    main()
