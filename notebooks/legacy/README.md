# Notebook lama (arsip)

Notebook eksplorasi awal, disimpan untuk referensi. **Tidak dipakai lagi** untuk hasil akhir karena:

- tiap platform memakai seed word, rumus PMI, dan basis logaritma yang berbeda, sehingga hasilnya tidak sebanding;
- `preProcess_yt.ipynb` membaca CSV tanpa `multiLine`, sehingga komentar multi-baris rusak (1.148 komentar terbaca 1.309 baris);
- banyak cell yang dihitung tetapi tidak dipakai untuk output akhir.

Notebook ini butuh `spark-nlp==6.2.2` (tidak termasuk di `requirements.txt`).
Analisis yang berlaku ada di [`../analisis_sentimen.ipynb`](../analisis_sentimen.ipynb) dan paket `src/acs_sentiment/`.
