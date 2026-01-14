# Game Sentiment Analysis

Project ini bertujuan untuk menganalisis sentimen pemain terhadap sebuah gim berdasarkan ulasan dan komentar pengguna menggunakan pendekatan **Text Analytics Pipeline**. Analisis difokuskan untuk memahami persepsi pemain serta faktor yang memengaruhi penurunan performa penjualan gim.

---

## 📌 Problem Statement
Gim mengalami penurunan penjualan signifikan dibandingkan seri sebelumnya. Oleh karena itu, diperlukan analisis sentimen pemain untuk mengidentifikasi persepsi publik serta sumber utama sentimen positif dan negatif.

---

## 🔄 Text Analytics Pipeline

Project ini menggunakan alur berikut:

1. **Data Collection**  
   Pengumpulan data ulasan dan komentar pemain dari platform online (misalnya forum atau media sosial).

2. **Pre-Processing**  
   Pembersihan dan normalisasi teks melalui:
   - Case folding  
   - Tokenization  
   - Noise removal  
   - Stopword filtering  

3. **Analysis**  
   Analisis sentimen dilakukan menggunakan pendekatan statistik berbasis asosiasi kata, seperti:
   - Co-occurrence analysis  
   - Pointwise Mutual Information (PMI)  
   - Sentiment scoring  

4. **Visualization & Insight**  
   Visualisasi hasil analisis untuk mengidentifikasi topik dengan sentimen positif dan negatif serta menarik insight bisnis.

---

## 📊 Key Insights
- Mayoritas sentimen pemain bersifat positif.
- Aspek yang paling diapresiasi: story, combat, dan atmosfer dunia game.
- Sentimen negatif didominasi oleh masalah teknis seperti bug, optimasi, dan crash.
- Persepsi negatif tidak berasal dari konten cerita, melainkan dari performa teknis.

---

## 💡 Business Decisions
Berdasarkan hasil analisis, keputusan bisnis yang direkomendasikan meliputi:
- Prioritas perbaikan bug dan performa.
- Mempertahankan konten utama game.
- Melakukan relaunch setelah perbaikan teknis.
- Memperkuat proses quality assurance dan testing.

---

## 🛠 Tools & Technologies
- Python  
- NLP libraries (NLTK / spaCy / Spark NLP – sesuai implementasi)
- Data visualization libraries (Matplotlib / Seaborn)

---
