# Aplikasi Monitoring Sensor Pompa Migas

![Tampilan GUI](foto/image.png)

Aplikasi desktop (Python) untuk mengelola data sensor pompa, menganalisisnya,
dan memprediksi apakah sebuah pompa berisiko rusak menggunakan machine learning.
Dibuat sebagai proyek belajar Data Science, dengan studi kasus industri minyak dan gas.

## Fitur

- **CRUD data sensor** (tambah, ubah, hapus, cari) dengan database SQLite
- **GUI** berbasis tkinter dan **mode terminal**
- **Pengurutan** data dengan klik judul kolom, dan **pewarnaan baris** (merah = rusak, kuning = risiko tinggi)
- **Analisis data**: statistik deskriptif, rata-rata per pompa, grafik boxplot
- **Machine learning**: Logistic Regression untuk memprediksi status pompa (Normal / Rusak) beserta peluangnya, dengan ambang keputusan yang bisa diatur
- **Eksperimen model**: perbandingan beberapa algoritma dengan cross-validation dan analisis ambang keputusan
- **Ekspor** data ke Excel / CSV
- Panel **"SQL terakhir"** yang menampilkan perintah SQL di balik setiap aksi

## Teknologi

Python, SQLite, pandas, NumPy, scikit-learn, matplotlib, tkinter

## Cara Menjalankan

```bash
git clone https://github.com/AbiRafi31/monitoring-pompa-migas.git
cd monitoring-pompa-migas
pip install -r requirements.txt
python main.py
```

Pilih `2` untuk mode GUI. Klik **Data Latihan (300)** untuk mengisi data simulasi,
lalu **Latih Model** dan **Prediksi**.

Untuk menjalankan eksperimen perbandingan model (setelah data latihan terisi):

```bash
python eksperimen_model.py
```

## Struktur Proyek

```
main.py               # aplikasi utama (database, CRUD, ML, GUI, mode terminal)
eksperimen_model.py   # perbandingan model dan analisis ambang keputusan
latihan_sql.py        # latihan query SQL pada salinan data
requirements.txt      # daftar library
```

## Hasil Eksperimen Model

Perbandingan dengan 5-fold cross-validation pada 300 data simulasi
(presisi, recall, dan F1 dihitung untuk kelas "Rusak"). Skrip: `eksperimen_model.py`.

| Model | Akurasi | Presisi | Recall | F1 |
|---|---|---|---|---|
| Tebak "Normal" terus (pembanding) | 81,7% | 0% | 0% | 0% |
| Random Forest | 87,0% | 72,8% | 49,1% | 57,6% |
| Random Forest + class_weight | 86,3% | 66,8% | 47,3% | 54,8% |
| Logistic Regression + class_weight | 90,0% | 67,1% | 90,9% | 77,0% |
| Decision Tree + class_weight | 84,0% | 54,9% | 80,0% | 63,8% |

Temuan:

- Akurasi menyesatkan pada data tidak seimbang: menebak "Normal" untuk semua pompa
  sudah mencapai 81,7%, tetapi tidak mendeteksi satu pun pompa rusak.
- `class_weight` tidak membantu Random Forest pada data ini.
- Logistic Regression unggul dengan recall 90,9%. Hasil ini kemungkinan dipengaruhi
  data simulasi yang dibangkitkan dengan rumus linear, sehingga perlu diuji ulang
  pada data sensor sungguhan.
- Menurunkan ambang keputusan dari 0,5 ke 0,2 menaikkan recall dari 90,9% ke 98,2%,
  dengan konsekuensi alarm palsu naik dari 25 ke 71. Pemilihan ambang adalah
  keputusan bisnis (biaya pompa rusak yang terlewat vs. inspeksi sia-sia).

## Hal yang Dipelajari

- Membersihkan dan menganalisis data dengan pandas
- Operasi SQL (SELECT, INSERT, UPDATE, DELETE, ORDER BY, LIKE) dengan query berparameter
  untuk mencegah SQL injection, serta constraint dan transaksi pada SQLite
- Pipeline machine learning: train/test split, cross-validation, evaluasi
  (akurasi, presisi, recall, F1), dan feature importance
- Menangani data tidak seimbang dan memilih ambang keputusan
- Membuat antarmuka GUI dengan tkinter

## Catatan

- Seluruh data adalah **data simulasi** untuk keperluan belajar, bukan data operasional sungguhan.
- Tombol di aplikasi masih memakai Random Forest. Hasil eksperimen menunjukkan
  Logistic Regression lebih baik pada data simulasi ini, tetapi belum dipasang ke aplikasi.

## Rencana Pengembangan

- [x] Memasang model terbaik ke aplikasi
- [ ] Mencoba dataset terbuka NASA C-MAPSS (predictive maintenance)
- [ ] Dashboard visualisasi (Power BI / Tableau)