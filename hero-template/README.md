# Hero image template

Makes `img/hero-nexus4-pair.png`, the two Nexus 4s at the top of the site, from two app screenshots.

Screenshots must be **768×1280 portrait PNGs**: the Nexus 4's own screen size. The `shot19` emulator
(Android 4.4, 768×1280 at 320 dpi) gives you that directly. Take one with:

```
adb emu screenrecord screenshot <folder>
```

## Option 1: Photoshop (`hero-nexus4.psd`)

Each phone's screen is a smart object, already set in perspective.

1. Double-click the thumbnail of **Front phone screen** or **Back phone screen**.
2. Paste the new screenshot over the contents (it's a 768×1280 document), then save and close it.
   Photoshop puts it back on the phone in perspective.
3. **File › Export › Export As… › PNG** (transparency on), and save it over `img/hero-nexus4-pair.png`.

What's in the file, from the bottom up:

| Layer | What it does |
|---|---|
| Phones (screens painted out) | The product photo, cut out, with the original screens painted over with bezel |
| Back phone screen | Smart object. Its layer mask hides the part behind the front phone |
| Back phone glass glare | The photo's glass reflection, in **Screen** mode, so new screenshots pick up the same shine |
| Front phone screen | Smart object |
| Front phone glass glare | As above |

Tested in Photopea (photopea.com), which opens it with working smart objects. It hasn't been tested in Photoshop itself.

## Option 2: the script (no Photoshop)

Put the screenshots in `screens/front.png` (the phone on the right) and `screens/back.png`, then:

```
python make_hero.py
```

That writes `../img/hero-nexus4-pair.png` directly. It needs Python with `numpy` and `opencv-python`. This is
the exact pipeline the current image came from: it paints out the photo's screens, measures the glass glare
from the photo's black status and nav bars, fits each screenshot to the marked screen corners, and cuts the
pair out of the white background with its shadow.

To rebuild the PSD after changing the screenshots, the photo or the corner points:

```
python make_hero.py --layers build
npm install
node make_psd.mjs
```

## Notes

- Screen corners and the back phone's visible edge are set at the top of `make_hero.py` (in `photo.png` pixels).
- `photo.png` is Google's Nexus 4 press render.
