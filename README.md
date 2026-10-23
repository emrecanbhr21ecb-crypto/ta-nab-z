# TaşNabız

Bazalt taşının gündüz ısısı ile toprağın serinliği arasındaki farktan elektrik üreten, pilsiz ve kablosuz iklim sensörünün 3B tanıtım sitesi (Tech4Climate Ideathon 2026, Diyarbakır).

| Sürüm | Adres | İçerik |
|---|---|---|
| v1 | `/` | Kaydırmalı 3B sensör dünyası |
| v2 | `/v2/` | Diyarbakır panoraması (2.5B), kuraklık canlandırması, taşa dalış, enerji simülatörü; Tarım (çiftçi telefonu + toprak dilimi: su, karbon, organik madde, azot), Kuyu, Hevsel, Dicle (kirlilik, temizlik, alg), Fabrika (toksik profil, arke önerisi), Dağkapı (gece merdiven/yol ışıkları, taş sağlık kartı), Atık (akıllı kutu, rota), uyarı motoru, pilot planı |
| A-MedBox | `/ai-box/` | Akıllı e-atık toplama kutusu: 3B kutu, uygulama ekranları, tara-okut-bırak simülasyonu, patlatılmış parça görünümü, ısıdan enerji, güvenlik (kamera, kilitli kapak, yağmur), şahıs/kurum teşviki (Yeşil Sertifika), belediye haritası, pikap talebi |

Canlı: https://emrecanbhr21ecb-crypto.github.io/ta-nab-z/ ve https://emrecanbhr21ecb-crypto.github.io/ta-nab-z/v2/

## Yerelde çalıştır

```bash
git clone https://github.com/emrecanbhr21ecb-crypto/ta-nab-z.git
cd ta-nab-z
python3 -m http.server 8000
# v1: http://localhost:8000   v2: http://localhost:8000/v2/   A-MedBox: http://localhost:8000/ai-box/
```

v2 katman ve görsel listelerini `fetch` ile okuduğu için dosyayı çift tıklayarak değil, yukarıdaki gibi bir sunucuyla aç.

## Görsel boru hattı (v2)

```
prompt / kod  →  görsel dosyası  →  manifest.json  →  site 3B olarak canlandırır
```

### 1. Panorama katmanları (kodla üretilir)

```bash
pip install numpy pillow
python3 tools/katman_uret.py
```

`v2/assets/katmanlar/` altına gökyüzü, Karacadağ, surlar, Hevsel, Dicle (su ayrı), kuraklık çatlakları ve ön plan taşlarını yazar. Site her katmanı derinliğine göre ayrı bir düzleme koyar; fare ve kaydırma ile paralaks, ısı dalgası, kuraklıkta renk ve su seviyesi değişimi uygulanır. Bir katmanı Gemini, Flow ya da kendi çizdiğin bir görselle değiştirmek için **aynı adla** üzerine yaz (saydam PNG/WebP, 2400×1200).

### 2. Gerçek fotoğraflar: "Sahadan" şeridi

Diyarbakır'dan kendi çektiğiniz fotoğrafları (Dicle, kuruyan tarla, surlar) `v2/assets/foto/` içine koyun ve `v2/assets/foto/manifest.json` dosyasını doldurun:

```json
[
  { "file": "dicle-kiyi.jpg", "baslik": "Dicle, Hevsel kıyısı", "kaynak": "Takım çekimi, Ekim 2026" }
]
```

Liste boşsa bölüm hiç görünmez. Doluysa giriş panoramasının hemen ardından, 3B eğim ve yavaş yakınlaşma ile gösterilir. Bu bölüm "bu gerçekten oluyor" kanıtıdır; buraya yapay zekâ görseli koymayın.

### 3. Konsept görseller (Gemini)

```bash
export GEMINI_API_KEY=...          # https://aistudio.google.com/apikey — repoya asla yazma
node tools/gemini_gorsel.mjs        # tools/promptlar.json'daki her prompt için görsel üretir
```

Görseller `v2/assets/uretilen/` altına iner, manifest otomatik güncellenir ve "Modüler kafa" bölümünde "yapay zekâ ile üretildi" etiketiyle görünür. Model `GEMINI_IMAGE_MODEL` ile değiştirilebilir. Flow'da ürettiğin görselleri de aynı klasöre koyup manifeste elle ekleyebilirsin.

## Yayın

GitHub Pages, `main` dalının kökünden yayınlanır (Settings → Pages → Branch: main / root).

> Panorama ve 3B sahneler temsili görsellerdir. Sayılar örnek veri ve tasarım hesabıdır; pilotta sahada doğrulanacaktır.
