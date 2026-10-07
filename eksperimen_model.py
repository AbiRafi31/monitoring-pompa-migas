"""
Eksperimen model: membandingkan beberapa algoritma untuk memprediksi pompa Rusak,
dengan fokus pada RECALL kelas "Rusak" (pompa rusak yang tidak terdeteksi = risiko terbesar).
Data dibaca dari data_pompa.db (dibuat oleh main.py).
"""
import os
import sqlite3
import warnings

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, make_scorer,
                             precision_score, recall_score, f1_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore")

FILE_DB = "data_pompa.db"
FITUR = ["suhu_c", "tekanan_psi", "getaran_mm_s"]

# ---------------------------------------------------------------
# 1. MUAT DATA
# ---------------------------------------------------------------
if not os.path.exists(FILE_DB):
    print("data_pompa.db tidak ditemukan. Jalankan main.py dulu,")
    print("klik 'Data Latihan (300)', lalu jalankan file ini lagi.")
    raise SystemExit

conn = sqlite3.connect(FILE_DB)
df = pd.read_sql_query("SELECT * FROM pompa", conn)
conn.close()

hitung = df["status"].value_counts()
if len(df) < 100 or len(hitung) < 2 or hitung.min() < 20:
    print(f"Data kurang memadai untuk eksperimen ({len(df)} baris, {hitung.to_dict()}).")
    print("Di main.py, klik 'Data Latihan (300)' dulu, lalu jalankan lagi.")
    raise SystemExit

X = df[FITUR]
y = df["status"]

print("=" * 70)
print("DATA")
print("=" * 70)
print(f"Jumlah baris : {len(df)}")
print(f"Komposisi    : {hitung.to_dict()}")
persen_normal = hitung.get("Normal", 0) / len(df) * 100
print(f"Kalau model menebak 'Normal' untuk SEMUA pompa, akurasinya {persen_normal:.1f}%")
print("(tapi tidak satu pun pompa rusak yang terdeteksi -> akurasi saja menyesatkan)")

# ---------------------------------------------------------------
# 2. BANDINGKAN MODEL (cross-validation 5 lipatan)
# ---------------------------------------------------------------
# Cross-validation: data dibagi 5 bagian, model dilatih & diuji 5 kali bergantian.
# Hasilnya lebih stabil daripada satu kali train/test split, apalagi data
# "Rusak" yang sedikit (satu split hanya punya ~11 contoh di data uji).
model_model = {
    "Tebak 'Normal' terus (pembanding)": DummyClassifier(strategy="most_frequent"),
    "Random Forest (awal)": RandomForestClassifier(n_estimators=100, random_state=42),
    "Random Forest + balanced": RandomForestClassifier(
        n_estimators=100, random_state=42, class_weight="balanced"),
    "Logistic Regression + balanced": make_pipeline(
        StandardScaler(), LogisticRegression(class_weight="balanced")),
    "Decision Tree + balanced": DecisionTreeClassifier(
        max_depth=4, random_state=42, class_weight="balanced"),
}

skor = {
    "akurasi": "accuracy",
    "presisi": make_scorer(precision_score, pos_label="Rusak", zero_division=0),
    "recall": make_scorer(recall_score, pos_label="Rusak", zero_division=0),
    "f1": make_scorer(f1_score, pos_label="Rusak", zero_division=0),
}
lipat = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print("\n" + "=" * 70)
print("PERBANDINGAN MODEL (rata-rata 5 lipatan; presisi/recall/F1 untuk kelas 'Rusak')")
print("=" * 70)
print(f"{'Model':<36}{'Akurasi':>9}{'Presisi':>9}{'Recall':>9}{'F1':>7}")
print("-" * 70)

hasil = {}
for nama, m in model_model.items():
    cv = cross_validate(m, X, y, cv=lipat, scoring=skor)
    r = {k: cv[f"test_{k}"].mean() for k in skor}
    hasil[nama] = r
    print(f"{nama:<36}{r['akurasi']*100:>8.1f}%{r['presisi']*100:>8.1f}%"
          f"{r['recall']*100:>8.1f}%{r['f1']*100:>6.1f}%")

# ---------------------------------------------------------------
# 3. ATUR AMBANG KEPUTUSAN (threshold)
# ---------------------------------------------------------------
# Model memberi PELUANG rusak. Biasanya "rusak" kalau peluang >= 0.5.
# Kita bisa menurunkan ambang: lebih banyak pompa ditandai rusak ->
# recall naik, tapi alarm palsu (presisi turun) juga naik.
kandidat = {n: r for n, r in hasil.items() if "pembanding" not in n}
terbaik = max(kandidat, key=lambda n: kandidat[n]["f1"])
print(f"\nModel dengan F1 tertinggi: {terbaik}")

peluang = cross_val_predict(model_model[terbaik], X, y, cv=lipat, method="predict_proba")
idx_rusak = list(model_model[terbaik].fit(X, y).classes_).index("Rusak")
p_rusak = peluang[:, idx_rusak]

print("\n" + "=" * 70)
print(f"EFEK AMBANG KEPUTUSAN pada '{terbaik}'")
print("=" * 70)
print(f"{'Ambang':>8}{'Terdeteksi':>12}{'Terlewat':>10}{'Alarm palsu':>13}{'Recall':>9}{'Presisi':>9}")
print("-" * 70)
for ambang in (0.5, 0.4, 0.3, 0.2):
    pred = np.where(p_rusak >= ambang, "Rusak", "Normal")
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=["Normal", "Rusak"]).ravel()
    rec = tp / (tp + fn) if (tp + fn) else 0
    pre = tp / (tp + fp) if (tp + fp) else 0
    print(f"{ambang:>8.1f}{tp:>12}{fn:>10}{fp:>13}{rec*100:>8.1f}%{pre*100:>8.1f}%")

print("\nCara baca:")
print("  Terdeteksi  = pompa rusak yang berhasil ditandai")
print("  Terlewat    = pompa rusak yang LOLOS (paling berbahaya di lapangan)")
print("  Alarm palsu = pompa normal yang salah ditandai rusak (biaya: inspeksi sia-sia)")
print("\nKeputusan ambang adalah keputusan BISNIS: seberapa mahal pompa rusak yang")
print("terlewat dibandingkan inspeksi yang sia-sia? Di migas, biasanya terlewat jauh lebih mahal.")