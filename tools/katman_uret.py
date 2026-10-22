"""TaşNabız v2 — Diyarbakır panoraması katman üretici.

Gökyüzü, Karacadağ, surlar, Hevsel Bahçeleri, Dicle ve On Gözlü Köprü,
ön plandaki bazalt taşları ve kuraklık çatlakları ayrı PNG katmanları olarak
üretilir. Site bu katmanları derinliklerine göre 3B sahneye dizip canlandırır.

Çalıştır:  python3 tools/katman_uret.py
Çıktı:     v2/assets/katmanlar/*.png + manifest.json

Bir katmanı Gemini/Flow ile ürettiğin ya da kendi çizdiğin bir görselle
değiştirmek istersen aynı adla üzerine yaz; kod dosyanın adına bağlıdır.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 2400, 1200
OUT = os.path.join(os.path.dirname(__file__), '..', 'v2', 'assets', 'katmanlar')
rng = np.random.default_rng(23)


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def value_noise(w, h, cell, seed):
    r = np.random.default_rng(seed)
    gw, gh = w // cell + 2, h // cell + 2
    g = r.random((gh, gw))
    ys, xs = np.mgrid[0:h, 0:w] / cell
    x0, y0 = xs.astype(int), ys.astype(int)
    fx, fy = xs - x0, ys - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = g[y0, x0], g[y0, x0 + 1]
    c, d = g[y0 + 1, x0], g[y0 + 1, x0 + 1]
    return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy


def fbm(w, h, cell, seed, octaves=4):
    out, amp, tot = np.zeros((h, w)), 1.0, 0.0
    for o in range(octaves):
        out += value_noise(w, h, max(2, cell >> o), seed + o) * amp
        tot += amp
        amp *= 0.5
    return out / tot


def fbm1d(n, scale, seed, octaves=5):
    r = np.random.default_rng(seed)
    x = np.arange(n)
    out, amp = np.zeros(n), 1.0
    for o in range(octaves):
        step = max(2, scale >> o)
        pts = r.random(n // step + 3)
        xi = x / step
        i0 = xi.astype(int)
        f = xi - i0
        f = f * f * (3 - 2 * f)
        out += (pts[i0] + (pts[i0 + 1] - pts[i0]) * f) * amp
        amp *= 0.5
    return out


def grain(img, strength=10, seed=1):
    a = np.asarray(img).astype(np.float32)
    n = np.random.default_rng(seed).normal(0, strength, a.shape[:2])[..., None]
    a[..., :3] = np.clip(a[..., :3] + n, 0, 255)
    return Image.fromarray(a.astype(np.uint8), img.mode)


def texture(img, dark, light, cell=40, seed=5, amount=0.35):
    """Silüetin opak piksellerine taş/bitki dokusu ver."""
    a = np.asarray(img).astype(np.float32)
    n = fbm(W, H, cell, seed)[..., None]
    d, l = np.array(dark, np.float32), np.array(light, np.float32)
    col = d + (l - d) * n
    a[..., :3] = a[..., :3] * (1 - amount) + col * amount
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def vertical_shade(img, top_mul=1.25, bot_mul=0.7, y0=0, y1=H):
    a = np.asarray(img).astype(np.float32)
    t = np.clip((np.arange(H) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    m = top_mul + (bot_mul - top_mul) * t
    a[..., :3] = np.clip(a[..., :3] * m, 0, 255)
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


# ---------------------------------------------------------------- gökyüzü
def gok():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    zen, mid, hor = np.array(hexrgb('#16203a')), np.array(hexrgb('#6b4a5c')), np.array(hexrgb('#f0a35a'))
    t = np.clip(y / 0.62, 0, 1)[..., None]
    col = np.where(t < 0.55, zen + (mid - zen) * (t / 0.55), mid + (hor - mid) * ((t - 0.55) / 0.45))
    col = np.broadcast_to(col, (H, W, 3)).copy()
    sx, sy = 0.27, 0.56
    d = np.sqrt(((x - sx) * 2.0) ** 2 + (y - sy) ** 2)
    glow = np.exp(-d * 5.5)[..., None]
    col += np.array([255, 170, 90]) * glow * 0.55
    disk = (d < 0.028)[..., None]
    col = np.where(disk, np.array([255, 236, 200]), col)
    clouds = fbm(W, H, 220, 11)
    band = np.exp(-((y - 0.34) / 0.1) ** 2) + 0.6 * np.exp(-((y - 0.47) / 0.05) ** 2)
    cl = np.clip((clouds - 0.52) * 3.2, 0, 1) * band
    ccol = np.array([255, 160, 120]) * (0.55 + 0.45 * glow[..., 0:1]) * 0.85
    col = col * (1 - cl[..., None] * 0.55) + ccol * cl[..., None] * 0.55
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    return grain(img, 4, 2)


def silhouette(ys, color):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(0, H)] + [(i, float(ys[i])) for i in range(0, W, 2)] + [(W, float(ys[-1])), (W, H)]
    d.polygon(pts, fill=color + (255,))
    return img, d


# ---------------------------------------------------------------- Karacadağ
def karacadag():
    x = np.arange(W)
    shield = 590 - 120 * np.exp(-((x - 1650) / 520.0) ** 2) - 40 * np.exp(-((x - 600) / 300.0) ** 2)
    ys = shield + (fbm1d(W, 180, 3) - 0.5) * 40
    img, _ = silhouette(ys, hexrgb('#7a5a68'))
    img = texture(img, hexrgb('#6a4d5d'), hexrgb('#9a6f72'), 90, 7, 0.4)
    return vertical_shade(img, 1.08, 0.82, 430, 700)


# ---------------------------------------------------------------- surlar ve şehir
def sur():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = lambda X: 700 - 0.03 * (X - 1200) + 10 * math.sin(X / 260.0)
    wall_dark, roof = hexrgb('#2b2629'), hexrgb('#3a3136')
    # şehir dokusu: evler, kubbeler, minareler
    r = np.random.default_rng(9)
    X = 380
    while X < 2300:
        w = int(r.integers(26, 70)); h = int(r.integers(30, 85))
        top = base(X) - 120 - h
        d.rectangle([X, top, X + w, base(X)], fill=roof + (255,))
        if r.random() < 0.55:
            for k in range(int(r.integers(1, 4))):
                wx = X + int(r.integers(4, max(6, w - 8))); wy = top + int(r.integers(8, h))
                d.rectangle([wx, wy, wx + 5, wy + 7], fill=(255, 196, 120, 255))
        X += w + int(r.integers(-6, 6))
    for cx, rad in [(980, 46), (1420, 38), (1880, 52)]:
        yb = base(cx) - 150
        d.pieslice([cx - rad, yb - rad, cx + rad, yb + rad], 180, 360, fill=roof + (255,))
        d.rectangle([cx - rad, yb, cx + rad, yb + 40], fill=roof + (255,))
    # Ulu Cami'nin kare gövdeli minaresi ve dört ayaklı minare
    for mx, mh, sq in [(1100, 260, True), (1560, 230, False), (2050, 210, False)]:
        yb = base(mx) - 110
        w = 30 if sq else 18
        d.rectangle([mx - w // 2, yb - mh, mx + w // 2, yb], fill=wall_dark + (255,))
        if sq:
            d.rectangle([mx - w // 2 - 6, yb - mh - 10, mx + w // 2 + 6, yb - mh], fill=wall_dark + (255,))
            d.polygon([(mx - 10, yb - mh - 10), (mx + 10, yb - mh - 10), (mx, yb - mh - 40)], fill=wall_dark + (255,))
        else:
            d.rectangle([mx - 14, yb - mh + 40, mx + 14, yb - mh + 50], fill=wall_dark + (255,))
            d.polygon([(mx - 9, yb - mh), (mx + 9, yb - mh), (mx, yb - mh - 46)], fill=wall_dark + (255,))
    # sur duvarı
    pts = [(300, H)]
    for X in range(300, W + 1, 4):
        pts.append((X, base(X) - 90))
    pts.append((W, H))
    d.polygon(pts, fill=wall_dark + (255,))
    for X in range(300, W, 22):
        d.rectangle([X, base(X) - 104, X + 12, base(X) - 89], fill=wall_dark + (255,))
    # burçlar: Diyarbakır surlarının yuvarlak ve çokgen burçları
    for i, X in enumerate(range(360, W, 175)):
        bw = 80 if i % 3 else 104
        top = base(X) - 150 - (20 if i % 3 == 0 else 0)
        tower = hexrgb('#353034')
        d.rectangle([X - bw // 2, top, X + bw // 2, base(X) + 40], fill=tower + (255,))
        d.ellipse([X - bw // 2, top - 14, X + bw // 2, top + 14], fill=tower + (255,))
        d.rectangle([X - bw // 2, top, X - bw // 2 + bw // 4, base(X) + 40], fill=hexrgb('#4a3d3a') + (255,))
        d.rectangle([X + bw // 4, top, X + bw // 2, base(X) + 40], fill=hexrgb('#262124') + (255,))
        for k in range(-bw // 2, bw // 2, 16):
            d.rectangle([X + k, top - 26, X + k + 9, top - 8], fill=tower + (255,))
        d.rectangle([X - 3, top + 30, X + 3, top + 44], fill=(255, 190, 110, 255))
    # şehrin üstünde durduğu bazalt yamaç
    slope = [(0, H)]
    for X in range(0, W + 1, 6):
        slope.append((X, base(X) + 6 + 30 * math.sin(X / 140.0) * 0.3 + (0 if X > 300 else (300 - X) * 0.4)))
    slope.append((W, H))
    d.polygon(slope, fill=hexrgb('#231e20') + (255,))
    img = texture(img, hexrgb('#1c181a'), hexrgb('#4a3e40'), 18, 21, 0.45)
    a = np.asarray(img).astype(np.float32)
    rim = np.zeros(a.shape[:2], np.float32)
    alpha = a[..., 3] > 0
    up = np.roll(alpha, 3, axis=0)
    rim[alpha & ~up] = 1
    rim = np.asarray(Image.fromarray((rim * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))) / 255.0
    a[..., :3] += rim[..., None] * np.array([150, 80, 40]) * 0.9
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


# ---------------------------------------------------------------- Hevsel Bahçeleri
def hevsel():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = np.random.default_rng(31)
    greens = [hexrgb(c) for c in ('#2d3d22', '#38492a', '#435630', '#2a3620', '#4b5a2e')]
    for _ in range(2600):
        x = r.uniform(-40, W + 40)
        y = 845 + 30 * math.sin(x / 300.0) + abs(r.normal(0, 26))
        if r.random() < 0.22:
            w, h = r.uniform(12, 22), r.uniform(80, 140)
        else:
            w = r.uniform(26, 62); h = w * r.uniform(0.75, 1.05)
        c = greens[int(r.integers(0, len(greens)))]
        lift = int(r.uniform(-14, 14))
        d.ellipse([x - w, y - h, x + w, y + h * 0.4], fill=(c[0] + lift, c[1] + lift, c[2] + lift // 2, 255))
    d.rectangle([0, 880, W, H], fill=(36, 44, 26, 255))
    img = texture(img, hexrgb('#1e2a16'), hexrgb('#5e6e38'), 14, 41, 0.3)
    a = np.asarray(img).astype(np.float32)
    lit = np.clip(1.0 - (np.arange(W)[None, :] / W), 0, 1)[..., None]
    a[..., :3] *= (0.85 + 0.35 * lit)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


# ---------------------------------------------------------------- Dicle ve On Gözlü Köprü
def dicle():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top = lambda X: 905 + 12 * math.sin(X / 380.0)
    bot = lambda X: 1010 + 22 * math.sin(X / 300.0 + 1)
    # On Gözlü Köprü: bazalt, on kemer
    x0, x1, deck = 1320, 2240, 872
    stone = hexrgb('#2a2426')
    d.rectangle([x0, deck, x1, 990], fill=stone + (255,))
    d.rectangle([x0, deck - 10, x1, deck], fill=hexrgb('#3a3033') + (255,))
    span = (x1 - x0) / 10
    for i in range(10):
        cx = x0 + span * (i + 0.5)
        half = span / 2 - 9
        d.ellipse([cx - half, deck + 22, cx + half, deck + 22 + half * 2.1], fill=(0, 0, 0, 0))
        d.rectangle([cx - half, deck + 22 + half * 1.05, cx + half, 990], fill=(0, 0, 0, 0))
    # su ve kemer boşluklarını yeniden boya (kemerin arkasında nehir görünür)
    img = Image.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, 0)), img)
    # köprünün sudaki yansıması
    # kıyı şeridi
    d = ImageDraw.Draw(img)
    d.polygon([(X, bot(X) - 2) for X in range(0, W + 1, 8)] + [(W, H), (0, H)], fill=hexrgb('#3b2c22') + (255,))
    return img


def dicle_water_only():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top = lambda X: 905 + 12 * math.sin(X / 380.0)
    bot = lambda X: 1010 + 22 * math.sin(X / 300.0 + 1)
    d.polygon([(X, top(X)) for X in range(0, W + 1, 8)] + [(X, bot(X)) for X in range(W, -1, -8)], fill=(255, 255, 255, 255))
    a = np.asarray(img).astype(np.float32)
    ys = np.arange(H)[:, None]
    t = np.clip((ys - 900) / 120.0, 0, 1)
    water = np.array([238, 160, 110]) * (1 - t[..., None]) * 0.7 + np.array([40, 82, 98]) * t[..., None]
    sheen = (np.sin(ys * 0.9 + np.sin(np.arange(W)[None, :] * 0.02) * 3) > 0.92) * 0.35
    water = water + sheen[..., None] * np.array([255, 210, 170])
    mask = a[..., 3] > 0
    a[..., :3] = np.where(mask[..., None], water, 0)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


# ---------------------------------------------------------------- ön plan: bazalt taşları
def boulder(d, cx, cy, rx, ry, seed, light=(104, 92, 88), dark=(28, 25, 26)):
    r = np.random.default_rng(seed)
    n = 11
    pts = []
    for i in range(n):
        a = math.pi + math.pi * i / (n - 1)
        rr = 1 + r.uniform(-0.14, 0.08)
        pts.append((cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr * (1.05 if 2 < i < 8 else 1)))
    poly = pts + [(cx + rx * 0.98, cy + 6), (cx - rx * 0.98, cy + 6)]
    d.polygon(poly, fill=dark + (255,))
    mid = tuple((dark[j] + light[j]) // 2 for j in range(3))
    # orta ton gövde ve ışık alan sol üst omuz
    body = [(cx + (x - cx) * 0.86 - rx * 0.05, cy + (y - cy) * 0.9) for x, y in pts[1:8]] + [(cx + rx * 0.1, cy - ry * 0.15)]
    d.polygon(body, fill=mid + (255,))
    cap = [(cx + (x - cx) * 0.62 - rx * 0.18, cy + (y - cy) * 0.82 - ry * 0.05) for x, y in pts[2:6]] + [(cx - rx * 0.05, cy - ry * 0.45)]
    d.polygon(cap, fill=light + (255,))
    # bazaltın gaz boşlukları (vezikül)
    for _ in range(int(rx * ry / 200)):
        px = cx + r.uniform(-rx * 0.8, rx * 0.8); py = cy - r.uniform(0.05, 0.85) * ry
        s_ = r.uniform(1.2, 3.4)
        d.ellipse([px - s_, py - s_ * 0.7, px + s_, py + s_ * 0.7], fill=(14, 12, 13, 255))


def on_plan():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ground = lambda X: 1040 + 20 * math.sin(X / 210.0)
    d.polygon([(X, ground(X)) for X in range(0, W + 1, 6)] + [(W, H), (0, H)], fill=hexrgb('#4a3628') + (255,))
    r = np.random.default_rng(77)
    for _ in range(1800):
        x = r.uniform(0, W); y = ground(x) + r.uniform(-4, 160)
        h = r.uniform(8, 30)
        c = (int(r.uniform(150, 200)), int(r.uniform(120, 150)), int(r.uniform(70, 90)), 255)
        d.line([(x, y), (x + r.uniform(-6, 6), y - h)], fill=c, width=2)
    boulder(d, 1700, 1130, 230, 150, 3)
    boulder(d, 420, 1150, 150, 90, 5)
    boulder(d, 2150, 1160, 120, 70, 8)
    boulder(d, 980, 1175, 80, 44, 9)
    img = texture(img, hexrgb('#2a1f18'), hexrgb('#7a5a40'), 10, 61, 0.25)
    return img


# ---------------------------------------------------------------- kuraklık çatlakları
def kurak():
    w, h = 1200, 120
    r = np.random.default_rng(5)
    n = 260
    px = r.uniform(0, w, n); py = r.uniform(0, h, n) ** 1.2 / h ** 0.2
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    ys2 = ys * 1.8
    best, second = np.full((h, w), 1e9, np.float32), np.full((h, w), 1e9, np.float32)
    for i in range(n):
        dd = (xs - px[i]) ** 2 + (ys2 - py[i] * 1.8) ** 2
        m = dd < best
        second = np.where(m, best, np.minimum(second, dd))
        best = np.where(m, dd, best)
    edge = np.sqrt(second) - np.sqrt(best)
    crack = np.clip(1 - edge / (1.2 + ys / h * 3.0), 0, 1)
    soil = np.zeros((h, w, 4), np.float32)
    soil[..., 0] = 168; soil[..., 1] = 122; soil[..., 2] = 82
    soil[..., :3] *= (0.8 + 0.25 * fbm(w, h, 30, 3))[..., None]
    soil[..., :3] = soil[..., :3] * (1 - crack[..., None]) + np.array([38, 24, 18]) * crack[..., None]
    soil[..., 3] = 255 * np.clip((ys / h) * 2.2, 0, 1)
    tile = Image.fromarray(soil.astype(np.uint8), 'RGBA').resize((W, h * 2), Image.BICUBIC)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    img.alpha_composite(tile, (0, H - h * 2 + 50))
    return img


LAYERS = [
    ('gok', gok, 0.0),
    ('karacadag', karacadag, 0.12),
    ('sur', sur, 0.3),
    ('hevsel', hevsel, 0.48),
    ('dicle_su', dicle_water_only, 0.6),
    ('dicle', dicle, 0.62),
    ('kurak', kurak, 0.85),
    ('on_plan', on_plan, 1.0),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    for name, fn, depth in LAYERS:
        img = fn()
        if name == 'gok':
            file = name + '.jpg'
            img.convert('RGB').save(os.path.join(OUT, file), quality=86)
        else:
            file = name + '.webp'
            img.save(os.path.join(OUT, file), quality=84, method=6)
        manifest.append({'id': name, 'file': file, 'depth': depth})
        print('yazıldı', file)
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump({'width': W, 'height': H, 'layers': manifest}, f, ensure_ascii=False, indent=2)
