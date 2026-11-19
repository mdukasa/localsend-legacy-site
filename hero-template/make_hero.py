"""Rebuild the hero image (two Nexus 4s) from two screenshots.

    python make_hero.py                 # writes ../img/hero-nexus4-pair.png
    python make_hero.py --layers out    # also writes the separate layers + layout.json (used by make_psd.mjs)

Inputs (768x1280 portrait screenshots, e.g. from the shot19 Android 4.4 emulator):
    screens/front.png   the phone in front (right)
    screens/back.png    the phone behind (left)
    photo.png           the two-phone product photo the screens are fitted to

Needs Python with numpy and opencv-python.
"""
import argparse, json, os
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
UP = 3            # work at 3x for clean edges
OUT_W = 880       # final width of the hero image (shown at 400px, so ~2x)
SCREEN = [[0, 0], [768, 0], [768, 1280], [0, 1280]]

# Screen corners in photo.png, from the marked dots (full screen: status bar to nav bar).
FRONT_Q = np.float32([[511.0, 129.8], [878.0, 154.0], [1044.9, 856.9], [666.0, 876.1]])
BACK_Q = np.float32([[156.9, 132.9], [596.9, 133.0], [596.9, 864.9], [156.9, 866.1]])
# Visible part of the back screen: the front phone's edge runs from (463.1,133) to (599,802).
BACK_VISIBLE = np.float32([[156.9, 132.9], [463.1, 133.0], [599.0, 802.0], [596.9, 864.9], [156.9, 866.1]])


def quad(H, pts):
    return cv2.perspectiveTransform(np.float32([pts]), H)[0]


def glare_grid(L, H, h, w):
    """Glass glare over a screen, in screen coords (48x80 grid).
    The photo's status bar and nav bar are black, so their brightness is reflection;
    sample them and spread the values smoothly across the screen."""
    gw, gh = 48, 80
    G = np.full((gh, gw), np.nan, np.float32)

    def sample(sx, sy):
        x, y = np.round(quad(H, [[sx, sy]])[0]).astype(int)
        if 2 <= x < w - 2 and 2 <= y < h - 2:
            return float(np.median(L[y - 2:y + 3, x - 2:x + 3]))
        return None

    for ya, yb in [(4, 46), (1190, 1276)]:
        for gy in range(gh):
            sy = (gy + .5) * 1280 / gh
            if ya <= sy <= yb:
                for gx in range(gw):
                    sx = (gx + .5) * 768 / gw
                    s = [sample(sx + dx, sy + dy) for dx in (-10, 0, 10) for dy in (-6, 0, 6)]
                    s = [v for v in s if v is not None]
                    if s:
                        G[gy, gx] = min(s)          # darkest nearby sample skips status bar icons
    known = ~np.isnan(G)
    F = np.where(known, G, np.nanmean(G))
    for _ in range(4000):                          # harmonic fill between the known rows
        P = np.pad(F, 1, mode='edge')
        F = np.where(known, G, (P[:-2, 1:-1] + P[2:, 1:-1] + P[1:-1, :-2] + P[1:-1, 2:]) / 4)
    # full strength over the status bar (matches the photo), easing to 70% lower down
    ramp = np.clip((np.arange(gh)[:, None] + 0.5 - 4) / (16 - 4), 0, 1)
    F *= 1.0 - 0.3 * ramp
    Gs = cv2.resize(F, (768, 1280), interpolation=cv2.INTER_CUBIC)
    return cv2.GaussianBlur(Gs, (0, 0), 12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--front', default=os.path.join(HERE, 'screens', 'front.png'))
    ap.add_argument('--back', default=os.path.join(HERE, 'screens', 'back.png'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'img', 'hero-nexus4-pair.png'))
    ap.add_argument('--layers', help='also export layers for the PSD into this folder')
    a = ap.parse_args()

    im = cv2.imread(os.path.join(HERE, 'photo.png')).astype(np.float32)
    h, w = im.shape[:2]
    L = im.min(axis=2)                              # glare is neutral; min channel ignores the orange
    Hf = cv2.getPerspectiveTransform(np.float32(SCREEN), FRONT_Q)
    Hb = cv2.getPerspectiveTransform(np.float32(SCREEN), BACK_Q)

    # 1) paint the photo's screens (and the slivers just outside the dots) with the surrounding bezel
    hole = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(hole, FRONT_Q.round().astype(np.int32), 255)
    hole = cv2.dilate(hole, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    cv2.fillPoly(hole, [BACK_VISIBLE.round().astype(np.int32)], 255)
    cv2.rectangle(hole, (154, 128), (160, 868), 255, -1)   # back screen's left edge
    clean = cv2.inpaint(im.astype(np.uint8), hole, 6, cv2.INPAINT_TELEA).astype(np.float32)
    big = cv2.resize(clean, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
    hh, ww = big.shape[:2]
    S = np.diag([UP, UP, 1]).astype(np.float64)

    screens = {}
    for name, path, H, visible in [('back', a.back, Hb, BACK_VISIBLE), ('front', a.front, Hf, None)]:
        shot = cv2.imread(path)
        if shot is None or shot.shape[:2] != (1280, 768):
            raise SystemExit(f'{path}: expected a 768x1280 screenshot')
        G = glare_grid(L, H, h, w)
        Hu = S @ H
        m = np.zeros((hh, ww), np.uint8)
        cv2.fillConvexPoly(m, quad(Hu, SCREEN).round().astype(np.int32), 255)
        full = cv2.GaussianBlur(m, (3, 3), 0).astype(np.float32) / 255
        if visible is not None:
            v = np.zeros((hh, ww), np.uint8)
            cv2.fillPoly(v, [(visible * UP).round().astype(np.int32)], 255)
            m = cv2.bitwise_and(m, v)
        mask = cv2.GaussianBlur(m, (3, 3), 0).astype(np.float32) / 255
        warp = lambda img: cv2.warpPerspective(img, Hu, (ww, hh), flags=cv2.INTER_AREA,
                                               borderMode=cv2.BORDER_REPLICATE)
        screens[name] = dict(H=Hu, mask=mask, full=full, shot=warp(shot.astype(np.float32)), glare=warp(G))

    # 2) composite: screenshot, then screen-blend the glare, inside each screen's mask
    out = big.copy()
    for name in ('back', 'front'):
        s = screens[name]
        g = s['glare'][..., None]
        lit = 255 - (255 - s['shot']) * (255 - g) / 255
        out = out * (1 - s['mask'][..., None]) + lit * s['mask'][..., None]

    # 3) cut out of the white background, keeping the studio shadow as see-through black
    out = np.floor(np.clip(out, 0, 255))
    Lo = out.min(axis=2)
    dark = (Lo < 150).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(dark)
    keep = np.isin(lab, [i for i in range(1, n) if st[i, 4] > 20000]).astype(np.uint8) * 255
    ff = keep.copy()
    cv2.floodFill(ff, np.zeros((hh + 2, ww + 2), np.uint8), (0, 0), 128)
    core = cv2.erode((ff != 128).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    a_out = np.clip((255 - Lo) / 255, 0, 1)
    a_out[a_out < 0.03] = 0
    alpha = np.where(core, 1.0, a_out)

    def cutout(img):
        rgb = np.where(core[..., None], img,
                       np.clip((img - 255 * (1 - alpha[..., None])) / np.maximum(alpha[..., None], 1e-3), 0, 255))
        return np.dstack([rgb, alpha * 255])

    ys, xs = np.nonzero(alpha > 0.02)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    sc = OUT_W / (x1 - x0)
    size = (OUT_W, round((y1 - y0) * sc))

    def fit(img):  # crop to the phones and scale to the output size
        return cv2.resize(img[y0:y1, x0:x1], size, interpolation=cv2.INTER_AREA)

    final = np.clip(fit(cutout(out)), 0, 255).astype(np.uint8)
    cv2.imwrite(a.out, final)
    print('wrote', os.path.normpath(a.out), final.shape[1], 'x', final.shape[0])

    if a.layers:
        os.makedirs(a.layers, exist_ok=True)
        to_out = lambda pts: ((np.float32(pts) - [x0, y0]) * sc).round(3).tolist()
        layout = dict(width=size[0], height=size[1], screens={})
        cv2.imwrite(os.path.join(a.layers, 'phones.png'), np.clip(fit(cutout(big)), 0, 255).astype(np.uint8))
        for name, s in screens.items():
            m, full = fit(s['mask']), fit(s['full'])
            g = fit(s['glare'])
            # smart object pixels: the whole warped screenshot; the layer mask clips what's hidden
            cv2.imwrite(os.path.join(a.layers, f'{name}-screen.png'),
                        np.clip(np.dstack([fit(s['shot']), full * 255]), 0, 255).astype(np.uint8))
            cv2.imwrite(os.path.join(a.layers, f'{name}-mask.png'), np.clip(m * 255, 0, 255).astype(np.uint8))
            cv2.imwrite(os.path.join(a.layers, f'{name}-glare.png'),
                        np.clip(np.dstack([g, g, g, m * 255]), 0, 255).astype(np.uint8))
            layout['screens'][name] = dict(corners=to_out(quad(s['H'], SCREEN)),
                                           source=os.path.relpath(a.front if name == 'front' else a.back, a.layers))
        cv2.imwrite(os.path.join(a.layers, 'composite.png'), final)
        with open(os.path.join(a.layers, 'layout.json'), 'w') as f:
            json.dump(layout, f, indent=2)
        print('wrote layers to', os.path.normpath(a.layers))


if __name__ == '__main__':
    main()
