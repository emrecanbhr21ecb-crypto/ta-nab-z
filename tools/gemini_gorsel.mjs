// TaşNabız — Gemini ile görsel üretici.
//
// promptlar.json'daki her prompt için Gemini'den görsel ister, dosyayı
// v2/assets/uretilen/ altına yazar ve manifest.json'u günceller. Site bu
// manifesti okur ve görselleri "Konsept kareler" şeridinde 3B eğimle canlandırır.
//
// Kullanım (Node 18+):
//   export GEMINI_API_KEY=...            # anahtar asla repoya girmez
//   node tools/gemini_gorsel.mjs          # hepsini üret
//   node tools/gemini_gorsel.mjs konsept-tarla   # yalnız birini üret
//
// Model değiştirmek için: GEMINI_IMAGE_MODEL=... (varsayılan aşağıda)
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..');
const KEY = process.env.GEMINI_API_KEY;
const MODEL = process.env.GEMINI_IMAGE_MODEL || 'gemini-2.5-flash-image';
const ENDPOINT = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`;

if (!KEY) {
  console.error('GEMINI_API_KEY tanımlı değil. Anahtarı https://aistudio.google.com/apikey adresinden al ve terminalde export et.');
  process.exit(1);
}

const prompts = JSON.parse(await fs.readFile(path.join(here, 'promptlar.json'), 'utf8'));
const only = process.argv[2];
const outDir = path.join(root, 'v2', 'assets', 'uretilen');
const manifestPath = path.join(outDir, 'manifest.json');
await fs.mkdir(outDir, { recursive: true });
let manifest = [];
try { manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8')); } catch {}

for (const p of prompts) {
  if (only && p.id !== only) continue;
  process.stdout.write(`→ ${p.id} üretiliyor… `);
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-goog-api-key': KEY },
    body: JSON.stringify({
      contents: [{ parts: [{ text: p.prompt }] }],
      generationConfig: { responseModalities: ['IMAGE'] }
    })
  });
  if (!res.ok) {
    console.log(`HATA ${res.status}: ${(await res.text()).slice(0, 300)}`);
    continue;
  }
  const data = await res.json();
  const part = data.candidates?.[0]?.content?.parts?.find(x => x.inlineData);
  if (!part) { console.log('yanıtta görsel yok'); continue; }
  const ext = part.inlineData.mimeType === 'image/jpeg' ? 'jpg' : 'png';
  const file = `${p.id}.${ext}`;
  await fs.writeFile(path.join(outDir, file), Buffer.from(part.inlineData.data, 'base64'));
  manifest = manifest.filter(m => m.id !== p.id);
  manifest.push({ id: p.id, file, baslik: p.baslik, kaynak: `Gemini (${MODEL}) · yapay zekâ ile üretildi` });
  console.log(`yazıldı: v2/assets/uretilen/${file}`);
}
await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
console.log('manifest güncellendi:', path.relative(root, manifestPath));
