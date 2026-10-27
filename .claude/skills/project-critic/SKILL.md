---
name: project-critic
description: Mengkritisi dan mengecek project analisis sentimen game ini secara menyeluruh — keamanan (secret/cookie yang ter-commit, data pribadi hasil scraping), reproducibility, kualitas pipeline scraping → preprocessing → sentimen → dashboard, validitas metodologi (labeling, PMI, evaluasi, bias sampel), dan kualitas kode/notebook. Gunakan saat user minta "kritisi project", "cek project", "review project", "audit", "apa yang kurang", atau sebelum presentasi/sidang/submit laporan.
argument-hint: "[lengkap|cepat] [fokus: keamanan|data|metodologi|kode|dashboard]"
---

# Project Critic — AnalizeGameSentiment

Tugasmu: bertindak sebagai reviewer yang kritis tapi adil (seperti dosen penguji + senior engineer).
Cari masalah nyata yang bisa dibuktikan dari isi repo, bukan saran generik. Setiap temuan harus
punya bukti (`path:line` atau nama cell notebook) dan alasan kenapa itu penting.

Jawab dalam Bahasa Indonesia kecuali user memakai bahasa lain.

## Argumen

- `cepat` → hanya bagian 1 (Keamanan) dan 3 (Pipeline data) + 5 temuan teratas lainnya.
- `lengkap` (default) → semua bagian.
- Kata fokus (`keamanan`, `data`, `metodologi`, `kode`, `dashboard`) → hanya bagian itu, tapi lebih dalam.

## Langkah kerja

1. **Petakan project dulu.** Jalankan `git ls-files`, baca `README.md`, `requirements.txt`,
   `pyproject.toml`, `.gitignore`, dan pahami alur:
   `scrapers/*.py` → `data/raw/` → `src/acs_sentiment/pipeline.py` (pakai `config`, `text`, `pmi`,
   `evaluation`) → `output/` → `dashboard/app.py` dan `notebooks/analisis_sentimen.ipynb`.
   `notebooks/legacy/` adalah arsip, bukan bagian dari hasil.
2. **Baca file yang relevan, jangan menebak.** Notebook besar (>200KB): baca dengan Read
   (mendukung .ipynb) atau grep dulu bagian kode (`"cell_type": "code"`), abaikan output cell
   yang panjang. Untuk CSV cukup lihat header + beberapa baris + jumlah baris.
3. **Periksa per kategori** (daftar di bawah). Verifikasi setiap dugaan sebelum dilaporkan —
   misalnya cek apakah path yang dibaca script benar-benar ada di repo.
4. **Tulis laporan** dengan format di bagian akhir.

Jangan mengubah file apa pun kecuali user memintanya. Jangan mencetak isi secret
(token, cookie, password) ke output — cukup sebut nama key dan lokasinya.

## Checklist

### 1. Keamanan & privasi
- File sensitif yang ter-commit atau tidak ter-ignore: `.env`, `session.json`,
  `user_cache.json`, cookie/authorization data, API key di script.
  Cek dengan `git ls-files` dan `git log --all -- <file>` (secret tetap ada di history
  walau file sudah dihapus — sarankan rotasi kredensial + `git filter-repo`).
- Kesalahan `.gitignore` (typo pola, baris tanpa newline sehingga dua pola tergabung,
  folder checkpoint yang salah eja).
- Data pribadi di hasil scraping (username, user ID, link profil) yang ikut di-commit
  atau ditampilkan di dashboard — sarankan anonimisasi/hash.
- Kepatuhan ToS / etika scraping (scraping tanpa API, rate limit, User-Agent palsu).

### 2. Reproducibility
- Dependensi tidak lengkap atau tidak dipin (library yang di-import tapi tidak ada di
  requirements; versi bebas).
- Path hardcoded yang tidak cocok dengan struktur repo (mis. script membaca `data/...`
  padahal data ada di `scraped/`).
- Urutan menjalankan notebook/script tidak terdokumentasi; tidak ada README.
- File sampah ter-commit: `.DS_Store`, `.ipynb_checkpoints/`, folder `_tmp`, CSV duplikat.
- Konfigurasi khusus mesin tertentu (mis. "Mac-compatible", memori Spark hardcoded).
- Random seed, tanggal pengambilan data, dan jumlah data per sumber tercatat atau tidak.

### 3. Pipeline data
- Scraper: penanganan error/retry, pagination, deduplikasi, rentang tanggal, filter bahasa.
- Preprocessing: apakah semua platform benar-benar melewati cleaning & lexicon yang sama
  (kalau beda, perbandingan antar platform jadi tidak adil), penanganan
  emoji, slang, bahasa campuran, teks kosong setelah cleaning, encoding.
- Logika analisis harus hanya ada di `src/acs_sentiment/`; notebook & dashboard tidak boleh menduplikasinya.
- Jalankan `pytest` (butuh `.venv`) dan laporkan hasilnya.
- Output: skema kolom konsisten antar sumber? Ada baris hilang/NaN tanpa disadari?

### 4. Metodologi sentimen
- Bagaimana label sentimen ditentukan (lexicon, PMI, model, rating Steam)? Apakah
  pendekatannya valid untuk teks game/gamer (sarkasme, slang, istilah game)?
- PMI: seed words apa yang dipakai, ambang frekuensi minimum, smoothing, dan apakah
  hasilnya diverifikasi manual.
- **Evaluasi**: apakah ada ground truth / sampel berlabel manual, dan metrik
  (accuracy, F1, confusion matrix)? Tanpa evaluasi, klaim sentimen tidak bisa dipertanggungjawabkan.
- Bias sampel: ukuran data per platform, distribusi waktu, bot/spam, self-selection
  (orang yang review cenderung ekstrem).
- Ketidakseimbangan kelas dan cara pelaporannya (persentase vs jumlah absolut).
- Kesimpulan yang ditarik (di notebook/dashboard) apakah benar-benar didukung data.

### 5. Kualitas kode
- Kode level-atas tanpa `if __name__ == "__main__":` / fungsi.
- Exception yang ditelan diam-diam, `except:` kosong.
- Magic number, nama variabel tidak jelas, kode mati, komentar yang menyesatkan.
- Penggunaan Spark untuk data kecil (overkill) vs pandas.

### 6. Dashboard (`dashboard/app.py`)
- Path data yang dibaca cocok dengan `output/`? Apa yang terjadi jika file tidak ada?
- Pemakaian `@st.cache_data`, angka KPI dihitung dengan benar, label/legend menyesatkan.
- Konsistensi dengan hasil di notebook dan angka di README (cek `output/summary.csv`, `output/evaluation.json`).

## Format laporan

```
# Kritik Project: AnalizeGameSentiment

## Ringkasan
<3–5 kalimat: kondisi umum, risiko terbesar, kesiapan untuk dipresentasikan>

## Temuan (urut dari paling parah)
### 🔴 Kritis
- **<judul singkat>** — `path:line`
  Masalah: ...
  Dampak: ...
  Perbaikan: ...
### 🟠 Penting
...
### 🟡 Minor
...

## Pertanyaan yang kemungkinan ditanyakan penguji/reviewer
1. ...

## Yang sudah baik
- ...

## Rencana perbaikan (prioritas)
1. ...
```

Batasi ke temuan yang benar-benar terbukti. Kalau ragu, tandai sebagai "perlu dicek"
dan jelaskan apa yang harus diverifikasi. Tawarkan untuk langsung memperbaiki
temuan tertentu setelah laporan selesai.
