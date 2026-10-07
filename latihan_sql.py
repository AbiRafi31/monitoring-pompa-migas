import os
import sqlite3
import pandas as pd


FILE_DB = "data_pompa.db"

if not os.path.exists(FILE_DB):
    print("File data_pompa.db tidak ditemukan.")
    print("Jalankan main.py dulu agar databasenya terbentuk,")
    print("pastikan latihan_sql.py ada di folder yang sama.")
    raise SystemExit

# Salin isi database ke memori (aman: database asli tidak berubah)
sumber = sqlite3.connect(FILE_DB)
df = pd.read_sql_query("SELECT * FROM pompa", sumber)
sumber.close()

conn = sqlite3.connect(":memory:")
df.to_sql("pompa", conn, index=False)

pd.set_option("display.width", 120)


def jalankan(sql):
    """Menjalankan query. SELECT ditampilkan sebagai tabel."""
    perintah = sql.strip().rstrip(";")
    if not perintah:
        return
    try:
        if perintah.lower().startswith(("select", "with", "pragma")):
            hasil = pd.read_sql_query(perintah, conn)
            if hasil.empty:
                print("(tidak ada hasil)")
            else:
                print(hasil.to_string(index=False))
        else:
            kursor = conn.execute(perintah)
            conn.commit()
            print(f"OK, {kursor.rowcount} baris terpengaruh.")
    except Exception as e:
        print("Error SQL:", e)


# ---------------------------------------------------------------
# BAGIAN 1: CONTOH QUERY (baca, jalankan, lalu pahami hasilnya)
# ---------------------------------------------------------------
contoh = [
    ("1. Lihat 5 data pertama (SELECT, LIMIT)",
     "SELECT * FROM pompa LIMIT 5"),

    ("2. Pompa rusak dengan getaran tertinggi (WHERE, ORDER BY)",
     "SELECT id, pompa_id, suhu_c, getaran_mm_s FROM pompa "
     "WHERE status = 'Rusak' ORDER BY getaran_mm_s DESC LIMIT 5"),

    ("3. Ringkasan per pompa (GROUP BY, COUNT, AVG)",
     "SELECT pompa_id, COUNT(*) AS jumlah, ROUND(AVG(suhu_c), 1) AS rata_suhu, "
     "ROUND(AVG(getaran_mm_s), 2) AS rata_getaran FROM pompa GROUP BY pompa_id"),

    ("4. Persentase rusak per pompa",
     "SELECT pompa_id, COUNT(*) AS total, SUM(status = 'Rusak') AS rusak, "
     "ROUND(100.0 * SUM(status = 'Rusak') / COUNT(*), 1) AS persen_rusak "
     "FROM pompa GROUP BY pompa_id ORDER BY persen_rusak DESC"),

    ("5. Pompa dengan rata-rata getaran di atas rata-rata keseluruhan (HAVING, subquery)",
     "SELECT pompa_id, ROUND(AVG(getaran_mm_s), 2) AS rata_getaran FROM pompa "
     "GROUP BY pompa_id HAVING AVG(getaran_mm_s) > (SELECT AVG(getaran_mm_s) FROM pompa)"),
]

print("=" * 60)
print("BAGIAN 1: CONTOH QUERY")
print("=" * 60)
for judul, sql in contoh:
    print(f"\n{judul}")
    print(f"SQL: {sql}\n")
    jalankan(sql)

# ---------------------------------------------------------------
# BAGIAN 2: MODE BEBAS (ketik query sendiri)
# ---------------------------------------------------------------
print("\n" + "=" * 60)
print("BAGIAN 2: MODE BEBAS")
print("=" * 60)
print("Nama tabel: pompa")
print("Kolom: id, pompa_id, suhu_c, tekanan_psi, getaran_mm_s, status")
print("Boleh juga INSERT / UPDATE / DELETE (hanya di salinan memori,")
print("file CSV aslimu tidak berubah). Ketik 'keluar' untuk berhenti.\n")

while True:
    sql = input("sql> ").strip()
    if sql.lower() in ("keluar", "exit", "quit"):
        print("Sampai jumpa!")
        break
    jalankan(sql)