// Builds hero-nexus4.psd: the two screens are smart objects, set in perspective on the phones.
// To swap a screen in Photoshop: double-click its thumbnail, paste a 768x1280 screenshot, save, close.
//
//   python make_hero.py --layers build   # renders the layers into ./build
//   node make_psd.mjs                     # writes ./hero-nexus4.psd
import { readFileSync, writeFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PNG } from 'pngjs';
import { writePsdBuffer } from 'ag-psd';

const here = dirname(fileURLToPath(import.meta.url));
const build = join(here, 'build');
const layout = JSON.parse(readFileSync(join(build, 'layout.json'), 'utf8'));
const { width, height } = layout;

const png = (file) => {
  const p = PNG.sync.read(readFileSync(join(build, file)));
  return { width: p.width, height: p.height, data: new Uint8ClampedArray(p.data.buffer, p.data.byteOffset, p.data.length) };
};
const gray = (file) => {          // single-channel mask -> RGBA pixel data ag-psd expects
  const p = PNG.sync.read(readFileSync(join(build, file)));
  const d = new Uint8ClampedArray(p.width * p.height * 4);
  for (let i = 0; i < p.width * p.height; i++) {
    const v = p.data[i * 4];
    d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = v; d[i * 4 + 3] = 255;
  }
  return { width: p.width, height: p.height, data: d };
};
const full = { top: 0, left: 0, bottom: height, right: width };

const linkedFiles = [];
const screenLayers = (name, label) => {
  const s = layout.screens[name];
  const id = randomUUID();
  const source = resolve(build, s.source);
  linkedFiles.push({ id, name: `${name}-screen.png`, type: 'png ', creator: '8BIM', data: new Uint8Array(readFileSync(source)) });
  const c = s.corners;    // top-left, top-right, bottom-right, bottom-left
  const transform = [c[0][0], c[0][1], c[1][0], c[1][1], c[2][0], c[2][1], c[3][0], c[3][1]];
  const screen = {
    name: `${label} screen (double-click to replace)`,
    ...full,
    imageData: png(`${name}-screen.png`),
    placedLayer: { id, placed: id, type: 'raster', transform, nonAffineTransform: transform, width: 768, height: 1280 },
  };
  if (name === 'back') {
    // hides the part behind the front phone; edit this if you move things
    screen.mask = { ...full, defaultColor: 0, imageData: gray(`${name}-mask.png`) };
  }
  const glare = {
    name: `${label} glass glare`,
    ...full,
    blendMode: 'screen',
    imageData: png(`${name}-glare.png`),
  };
  return [screen, glare];
};

const psd = {
  width, height,
  imageData: png('composite.png'),
  linkedFiles,
  children: [
    { name: 'Phones (screens painted out)', ...full, imageData: png('phones.png') },
    ...screenLayers('back', 'Back phone'),
    ...screenLayers('front', 'Front phone'),
  ],
};

const out = join(here, 'hero-nexus4.psd');
writeFileSync(out, Buffer.from(writePsdBuffer(psd, { generateThumbnail: false, noBackground: true, compress: true })));
console.log('wrote', out);
