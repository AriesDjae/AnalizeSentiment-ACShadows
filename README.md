# Analisis Sentimen Pemain *Assassin's Creed Shadows*

Analisis sentimen ±13.700 ulasan dan komentar pemain *Assassin's Creed Shadows* dari **Steam**, **Reddit**,
dan **YouTube** dengan PySpark. Setiap komentar dilabeli dengan satu lexicon yang sama untuk semua platform.
Topik yang paling terkait dengan sentimen positif/negatif dicari dengan **PMI** (*Pointwise Mutual Information*).
Hasilnya ditampilkan di dashboard Streamlit.

## Latar belakang

Penjualan gim ini dilaporkan menurun dibanding seri sebelumnya. Project ini mencari tahu bagaimana
persepsi pemain sebenarnya, dan apa sumber utama sentimen positif maupun negatif, sebagai dasar
keputusan bisnis.

## Hasil utama

| Platform | Komentar | Positif* | Negatif* | Netral** | Periode |
|----------|---------:|---------:|---------:|---------:|---------|
| Steam    | 11.925   | 84%      | 16%      | 28%      | Mar – Nov 2025 |
| Reddit   | 591      | 80%      | 20%      | 29%      | Des 2024 – Des 2025 |
| YouTube  | 1.146    | 68%      | 32%      | 63%      | (tanggal relatif) |

\* dari komentar bersentimen (positif + negatif) · \** dari semua komentar (tanpa kata sentimen)

- **Validasi**: label lexicon cocok dengan label asli Steam (*Recommended / Not Recommended*) pada
  **90,6%** ulasan (macro-F1 0,835), di atas baseline kelas mayoritas (81,3%). Porsi *Recommended* asli
  di Steam adalah 79%.
- **Topik positif** (Steam): *detailed, flawless, refreshing, goty, customize*, serta perbandingan dengan *Valhalla*.
- **Topik negatif** (Steam): didominasi masalah teknis (*freeze, directx, deleted, verify, uninstalled*)
  dan kekecewaan pada Ubisoft, bukan gameplay inti.

Penjelasan lengkap ada di [`notebooks/analisis_sentimen.ipynb`](notebooks/analisis_sentimen.ipynb).

## Rekomendasi bisnis

Karena sentimen umumnya positif dan keluhan didominasi masalah teknis, bukan konten:

- **Prioritaskan stabilitas dan performa** (freeze, crash, kompatibilitas DirectX) sebelum menambah konten.
- **Pertahankan arah konten**: detail dunia dan kualitas keseluruhan justru menjadi alasan ulasan positif.
- **Perkuat QA dan testing** sebelum rilis atau patch besar.
- **Komunikasikan perbaikan teknis** secara terbuka untuk memulihkan kepercayaan pemain yang kecewa
  pada Ubisoft. Pertimbangkan momentum promosi ulang setelah perbaikan dirilis.

## Struktur project

```
├── data/
│   ├── raw/                      # hasil scraping (Steam, Reddit, YouTube)
│   └── annotation/               # sampel 200 komentar untuk dilabeli manual
├── src/acs_sentiment/            # paket analisis (satu sumber kebenaran)
│   ├── config.py                 #   lokasi file, lexicon, parameter
│   ├── text.py                   #   cleaning, tokenisasi, filter bahasa, skor lexicon
│   ├── pmi.py                    #   perhitungan PMI
│   ├── evaluation.py             #   metrik validasi
│   └── pipeline.py               #   pipeline PySpark end-to-end
├── notebooks/
│   ├── analisis_sentimen.ipynb   # analisis & interpretasi hasil
│   └── legacy/                   # notebook eksplorasi awal (arsip)
├── dashboard/app.py              # dashboard Streamlit
├── scrapers/                     # script pengambil data
├── output/                       # hasil pipeline (dibaca dashboard)
└── tests/                        # unit test + smoke test dashboard
```

## Menjalankan

**Prasyarat**: Python 3.9+, Java 8/11/17 dengan `JAVA_HOME` terset. Di Windows, set juga
`HADOOP_HOME` ke folder yang berisi `bin/winutils.exe`.

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

python -m acs_sentiment.pipeline  # ±15 detik; menulis output/
streamlit run dashboard/app.py    # dashboard di http://localhost:8501
pytest                            # 20 tes
```

### Output pipeline

| File | Isi |
|------|-----|
| `output/documents.csv` | satu baris per komentar: platform, tanggal, label lexicon, label asli (Steam), teks |
| `output/word_sentiment.csv` | per platform & kata: jumlah di komentar positif/negatif, PMI, skor sentimen |
| `output/summary.csv` | ringkasan per platform |
| `output/evaluation.json` | metrik validasi lexicon |

### Mengambil data baru (opsional)

```bash
python scrapers/steam.py <steam_appid>
python scrapers/reddit.py                 # --test untuk uji cepat
FIREFOX_PROFILE_PATH="<profil Firefox>" python scrapers/youtube.py
```

Hasilnya masuk ke `data/raw/`. `scrapers/instagram.py` butuh `.env` berisi `INSTAGRAM_USERNAME` dan
`INSTAGRAM_PASSWORD`, dan datanya tidak dipakai di analisis. **Jangan commit `.env` atau `session.json`.**

## Metodologi

1. **Cleaning**: lowercase, hapus URL, angka, dan simbol, gabungkan kontraksi (*don't → dont*), buang
   stopword dan kata umum (*game, play, …*). Ulasan non-Inggris dibuang (63 ulasan Steam).
2. **Label sentimen**: skor = jumlah seed word positif − negatif (32 positif, 32 negatif). Polaritas dibalik bila
   seed word didahului negasi dalam 3 kata (*not good*, *don't recommend*). Skor > 0 positif, < 0 negatif,
   0 netral. Komentar netral tidak dipakai untuk PMI.
3. **PMI**: untuk setiap kata *w*, skor = PMI(*w*, positif) − PMI(*w*, negatif) dengan Laplace smoothing.
   Seed word dikeluarkan dari ranking topik karena skornya sirkular, dan kata dengan < 10 kemunculan diabaikan.
4. **Validasi**: label lexicon dibandingkan dengan rekomendasi asli Steam. Untuk Reddit/YouTube, isi kolom
   `gold_label` (`positive` / `negative` / `neutral`) di `data/annotation/sample_for_labeling.csv`.
   Pipeline otomatis menghitung metrik validasi manual.

## Keterbatasan

- Lexicon tidak menangkap sarkasme dan konteks kompleks. Recall kelas negatif 67% di Steam, sehingga porsi
  negatif cenderung sedikit lebih rendah dari kenyataan.
- Komentar YouTube berasal dari satu video dan hanya punya tanggal relatif. Data Reddit relatif kecil (591),
  sehingga topik di kedua platform ini lebih bising.
- Perbedaan antar platform juga dipengaruhi demografi pengguna, bukan hanya opini terhadap game.

## Etika data

Data diambil dari halaman publik. Kolom pengguna (username/Steam ID) **tidak** ikut di `output/` maupun
dashboard. Data mentah di `data/raw/` masih memuatnya, jadi hapus atau hash kolom tersebut sebelum dibagikan.
