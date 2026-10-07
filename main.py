import os
import sqlite3
from contextlib import closing

import numpy as np
import pandas as pd

FILE_DB = "data_pompa.db"
FILE_CSV = "data_pompa.csv"   # hanya dipakai SEKALI untuk memindahkan data lama ke database
KOLOM = ["id", "pompa_id", "suhu_c", "tekanan_psi", "getaran_mm_s", "status"]
FITUR = ["suhu_c", "tekanan_psi", "getaran_mm_s"]
SQL_TERAKHIR = ""             # menyimpan perintah SQL terakhir (untuk belajar)


# ---------------------------------------------------------------
# DATA CONTOH
# ---------------------------------------------------------------
def buat_data_awal():
    np.random.seed(42)
    n = 10
    return pd.DataFrame({
        "id": range(1, n + 1),
        "pompa_id": np.random.choice(["P-01", "P-02", "P-03"], n),
        "suhu_c": np.random.normal(75, 5, n).round(1),
        "tekanan_psi": np.random.normal(300, 20, n).round(1),
        "getaran_mm_s": np.random.normal(2.5, 0.6, n).round(2),
        "status": np.random.choice(["Normal", "Normal", "Normal", "Rusak"], n),
    })


def buat_data_latihan(n=300):
    """Data simulasi yang punya POLA: suhu, getaran, dan tekanan tinggi
    membuat pompa lebih mungkin Rusak. Model ML bisa belajar dari pola ini."""
    rng = np.random.default_rng(42)
    suhu = rng.normal(75, 6, n).round(1)
    tekanan = rng.normal(300, 25, n).round(1)
    getaran = rng.normal(2.5, 0.7, n).clip(0.5).round(2)
    skor = ((suhu - 75) / 6 + (getaran - 2.5) / 0.7
            + 0.5 * (tekanan - 300) / 25 + rng.normal(0, 0.6, n))
    status = np.where(skor > 1.2, "Rusak", "Normal")
    return pd.DataFrame({
        "id": range(1, n + 1),
        "pompa_id": rng.choice(["P-01", "P-02", "P-03"], n),
        "suhu_c": suhu,
        "tekanan_psi": tekanan,
        "getaran_mm_s": getaran,
        "status": status,
    })


# ---------------------------------------------------------------
# DATABASE (SQLite) - semua perintah SQL ada di bagian ini
# ---------------------------------------------------------------
def catat_sql(sql, params=()):
    global SQL_TERAKHIR
    teks = " ".join(sql.split())
    SQL_TERAKHIR = f"{teks}   {params}" if params else teks


def siapkan_database():
    """Membuat tabel jika belum ada. Jika tabel kosong, isi dari CSV lama
    (kalau ada), atau dari data contoh."""
    with closing(sqlite3.connect(FILE_DB)) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pompa (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    pompa_id      TEXT NOT NULL,
                    suhu_c        REAL NOT NULL,
                    tekanan_psi   REAL NOT NULL,
                    getaran_mm_s  REAL NOT NULL,
                    status        TEXT NOT NULL CHECK (status IN ('Normal', 'Rusak'))
                )
            """)
        jumlah = conn.execute("SELECT COUNT(*) FROM pompa").fetchone()[0]

    if jumlah > 0:
        return
    if os.path.exists(FILE_CSV):
        try:
            isi_tabel(pd.read_csv(FILE_CSV)[KOLOM])
            print("Data lama dari data_pompa.csv sudah dipindahkan ke database.")
            return
        except Exception:
            pass   # CSV rusak/tidak cocok -> pakai data contoh
    isi_tabel(buat_data_awal())


def isi_tabel(df):
    """Mengganti seluruh isi tabel dengan data dari DataFrame."""
    baris = [(int(r.id), str(r.pompa_id), float(r.suhu_c), float(r.tekanan_psi),
              float(r.getaran_mm_s), str(r.status)) for r in df.itertuples(index=False)]
    sql = ("INSERT INTO pompa (id, pompa_id, suhu_c, tekanan_psi, getaran_mm_s, status) "
           "VALUES (?, ?, ?, ?, ?, ?)")
    with closing(sqlite3.connect(FILE_DB)) as conn:
        with conn:   # semua langkah di bawah satu transaksi: gagal = dibatalkan semua
            conn.execute("DELETE FROM pompa")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'pompa'")
            conn.executemany(sql, baris)
    catat_sql(f"DELETE FROM pompa; lalu {len(baris)}x {sql}")


# ---------- READ ----------
def baca_semua(urut_kolom="id", naik=True, kata="", catat=True):
    if urut_kolom not in KOLOM:      # nama kolom tidak bisa pakai "?", jadi dicek manual
        urut_kolom = "id"
    arah = "ASC" if naik else "DESC"
    sql = "SELECT * FROM pompa"
    params = ()
    kata = kata.strip()
    if kata:
        sql += " WHERE pompa_id LIKE ?"
        params = (f"%{kata}%",)
    sql += f" ORDER BY {urut_kolom} {arah}"
    with closing(sqlite3.connect(FILE_DB)) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    if catat:
        catat_sql(sql, params)
    return df


def baca_satu(id_data):
    sql = "SELECT * FROM pompa WHERE id = ?"
    with closing(sqlite3.connect(FILE_DB)) as conn:
        df = pd.read_sql_query(sql, conn, params=(id_data,))
    catat_sql(sql, (id_data,))
    return None if df.empty else df.iloc[0].to_dict()


# ---------- CREATE ----------
def db_tambah(pompa_id, suhu, tekanan, getaran, status):
    sql = ("INSERT INTO pompa (pompa_id, suhu_c, tekanan_psi, getaran_mm_s, status) "
           "VALUES (?, ?, ?, ?, ?)")
    params = (pompa_id, suhu, tekanan, getaran, status)
    with closing(sqlite3.connect(FILE_DB)) as conn:
        with conn:
            id_baru = conn.execute(sql, params).lastrowid
    catat_sql(sql, params)
    return id_baru


# ---------- UPDATE ----------
def db_ubah(id_data, pompa_id, suhu, tekanan, getaran, status):
    sql = ("UPDATE pompa SET pompa_id = ?, suhu_c = ?, tekanan_psi = ?, "
           "getaran_mm_s = ?, status = ? WHERE id = ?")
    params = (pompa_id, suhu, tekanan, getaran, status, id_data)
    with closing(sqlite3.connect(FILE_DB)) as conn:
        with conn:
            jumlah = conn.execute(sql, params).rowcount
    catat_sql(sql, params)
    return jumlah


# ---------- DELETE ----------
def db_hapus(id_data):
    sql = "DELETE FROM pompa WHERE id = ?"
    with closing(sqlite3.connect(FILE_DB)) as conn:
        with conn:
            jumlah = conn.execute(sql, (id_data,)).rowcount
    catat_sql(sql, (id_data,))
    return jumlah


# ---------------------------------------------------------------
# MACHINE LEARNING
# ---------------------------------------------------------------
def latih_model(df):
    """Melatih Random Forest. Mengembalikan (model, teks_laporan)."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report

    hitung = df["status"].value_counts()
    if len(df) < 30 or len(hitung) < 2 or hitung.min() < 5:
        return None, ("Data belum cukup untuk melatih model.\n"
                      "Syarat: minimal 30 baris, dan masing-masing status\n"
                      "(Normal dan Rusak) minimal 5 data.")

    X = df[FITUR]
    y = df["status"]
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)

    laporan = (
        f"Data latih: {len(X_tr)} baris | Data uji: {len(X_te)} baris\n"
        f"Akurasi: {accuracy_score(y_te, pred) * 100:.1f}%\n\n"
        + classification_report(y_te, pred, zero_division=0)
        + "\nPengaruh tiap sensor terhadap prediksi:\n"
    )
    pentingnya = sorted(zip(FITUR, model.feature_importances_), key=lambda t: -t[1])
    for nama, nilai in pentingnya:
        laporan += f"  {nama:<14} {nilai * 100:5.1f}%\n"
    return model, laporan


def prediksi(model, suhu, tekanan, getaran):
    """Mengembalikan (label, peluang_rusak)."""
    x = pd.DataFrame([[suhu, tekanan, getaran]], columns=FITUR)
    label = model.predict(x)[0]
    peluang = dict(zip(model.classes_, model.predict_proba(x)[0]))
    return label, float(peluang.get("Rusak", 0.0))


# ---------------------------------------------------------------
# FUNGSI BANTU UNTUK INPUT (MODE TERMINAL)
# ---------------------------------------------------------------
def input_angka(pesan, tipe=float, boleh_kosong=False):
    while True:
        teks = input(pesan).strip()
        if teks == "" and boleh_kosong:
            return None
        try:
            return tipe(teks.replace(",", "."))
        except ValueError:
            print("  Input harus berupa angka, coba lagi.")


def input_status(pesan, boleh_kosong=False):
    while True:
        teks = input(pesan).strip().capitalize()
        if teks == "" and boleh_kosong:
            return None
        if teks in ("Normal", "Rusak"):
            return teks
        print("  Status harus 'Normal' atau 'Rusak'.")


def input_pompa(pesan):
    while True:
        teks = input(pesan).strip().upper()
        if teks:
            return teks
        print("  ID Pompa tidak boleh kosong.")


# ---------------------------------------------------------------
# CRUD (MODE TERMINAL)
# ---------------------------------------------------------------
def tampilkan_data():
    df = baca_semua()
    print("\n--- DATA SENSOR POMPA ---")
    if df.empty:
        print("Data kosong.")
    else:
        print(df.to_string(index=False))
        print(f"Total: {len(df)} data")
    print(f"SQL: {SQL_TERAKHIR}")
    return df


def cari_data():
    print("\n--- CARI DATA ---")
    kode = input("ID Pompa yang dicari (misal P-01): ").strip()
    hasil = baca_semua(kata=kode)
    if hasil.empty:
        print("Data tidak ditemukan.")
    else:
        print(hasil.to_string(index=False))
    print(f"SQL: {SQL_TERAKHIR}")


def tambah_data():
    print("\n--- TAMBAH DATA ---")
    pompa_id = input_pompa("ID Pompa (misal P-01): ")
    suhu = input_angka("Suhu (C): ")
    tekanan = input_angka("Tekanan (psi): ")
    getaran = input_angka("Getaran (mm/s): ")
    status = input_status("Status (Normal/Rusak): ")

    id_baru = db_tambah(pompa_id, suhu, tekanan, getaran, status)
    print(f"Data berhasil ditambahkan dengan id {id_baru}.")
    print(f"SQL: {SQL_TERAKHIR}")


def ubah_data():
    df = tampilkan_data()
    if df.empty:
        return
    id_ubah = input_angka("\nID data yang mau diubah: ", int)
    lama = baca_satu(id_ubah)
    if lama is None:
        print("ID tidak ditemukan.")
        return

    print("Tekan Enter jika tidak ingin mengubah kolom tersebut.")
    pompa = input(f"ID Pompa [{lama['pompa_id']}]: ").strip().upper() or lama["pompa_id"]

    suhu = input_angka(f"Suhu [{lama['suhu_c']}]: ", float, True)
    tekanan = input_angka(f"Tekanan [{lama['tekanan_psi']}]: ", float, True)
    getaran = input_angka(f"Getaran [{lama['getaran_mm_s']}]: ", float, True)
    status = input_status(f"Status [{lama['status']}]: ", True)

    db_ubah(
        id_ubah, pompa,
        float(lama["suhu_c"]) if suhu is None else suhu,
        float(lama["tekanan_psi"]) if tekanan is None else tekanan,
        float(lama["getaran_mm_s"]) if getaran is None else getaran,
        lama["status"] if status is None else status,
    )
    print("Data berhasil diubah.")
    print(f"SQL: {SQL_TERAKHIR}")


def hapus_data():
    df = tampilkan_data()
    if df.empty:
        return
    id_hapus = input_angka("\nID data yang mau dihapus: ", int)
    if baca_satu(id_hapus) is None:
        print("ID tidak ditemukan.")
        return

    yakin = input(f"Yakin hapus data id {id_hapus}? (y/n): ").strip().lower()
    if yakin == "y":
        db_hapus(id_hapus)
        print("Data berhasil dihapus.")
        print(f"SQL: {SQL_TERAKHIR}")
    else:
        print("Penghapusan dibatalkan.")


# ---------------------------------------------------------------
# ANALISIS & GRAFIK (MODE TERMINAL)
# ---------------------------------------------------------------
def tampilkan_analisis(df):
    print("\n--- RINGKASAN ANALISIS ---")
    if df.empty:
        print("Data kosong.")
        return
    print("\nStatistik deskriptif:")
    print(df[FITUR].describe().round(2))
    print("\nRata-rata sensor per pompa:")
    print(df.groupby("pompa_id")[FITUR].mean().round(2))
    print("\nJumlah status per pompa:")
    print(pd.crosstab(df["pompa_id"], df["status"]))


def tampilkan_grafik(df):
    import matplotlib.pyplot as plt

    if df.empty:
        print("Data kosong.")
        return
    df.boxplot(column="getaran_mm_s", by="status")
    plt.title("Getaran berdasarkan status pompa")
    plt.suptitle("")
    plt.ylabel("mm/s")
    plt.show()


# ---------------------------------------------------------------
# DATA LATIHAN & ML (MODE TERMINAL)
# ---------------------------------------------------------------
def ganti_dengan_data_latihan():
    print("\nIni akan MENGGANTI seluruh data dengan 300 data simulasi.")
    yakin = input("Lanjutkan? (y/n): ").strip().lower()
    if yakin != "y":
        print("Dibatalkan.")
        return
    isi_tabel(buat_data_latihan(300))
    print("Berhasil. Sekarang ada 300 data simulasi (siap dipakai untuk ML).")


def menu_ml_terminal(df):
    print("\n--- LATIH MODEL MACHINE LEARNING ---")
    try:
        model, laporan = latih_model(df)
    except ImportError:
        print("Library scikit-learn belum terpasang.")
        print("Jalankan: python -m pip install scikit-learn")
        return
    print(laporan)
    if model is None:
        return

    while True:
        lagi = input("Mau coba prediksi pompa baru? (y/n): ").strip().lower()
        if lagi != "y":
            break
        suhu = input_angka("Suhu (C): ")
        tekanan = input_angka("Tekanan (psi): ")
        getaran = input_angka("Getaran (mm/s): ")
        label, p_rusak = prediksi(model, suhu, tekanan, getaran)
        print(f"Prediksi: {label} (peluang rusak {p_rusak * 100:.0f}%)")


# ---------------------------------------------------------------
# MENU TERMINAL
# ---------------------------------------------------------------
def main():
    while True:
        print("\n===== MENU DATA POMPA MIGAS (SQLite) =====")
        print("1. Tampilkan semua data")
        print("2. Cari data berdasarkan ID Pompa")
        print("3. Tambah data")
        print("4. Ubah data")
        print("5. Hapus data")
        print("6. Ringkasan analisis")
        print("7. Tampilkan grafik")
        print("8. Ganti dengan data latihan (300 baris)")
        print("9. Latih model & prediksi (ML)")
        print("0. Keluar")
        pilihan = input("Pilih menu: ").strip()

        if pilihan == "1":
            tampilkan_data()
        elif pilihan == "2":
            cari_data()
        elif pilihan == "3":
            tambah_data()
        elif pilihan == "4":
            ubah_data()
        elif pilihan == "5":
            hapus_data()
        elif pilihan == "6":
            tampilkan_analisis(baca_semua(catat=False))
        elif pilihan == "7":
            tampilkan_grafik(baca_semua(catat=False))
        elif pilihan == "8":
            ganti_dengan_data_latihan()
        elif pilihan == "9":
            menu_ml_terminal(baca_semua(catat=False))
        elif pilihan == "0":
            print("Sampai jumpa!")
            break
        else:
            print("Pilihan tidak valid.")


# ---------------------------------------------------------------
# MODE GUI (tkinter)
# ---------------------------------------------------------------
def main_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox

    df = baca_semua(catat=False)
    model = None                          # model ML, diisi setelah klik "Latih Model"
    urut = {"kol": "id", "naik": True}    # kolom & arah urutan tabel

    root = tk.Tk()
    root.title("Data Sensor Pompa Migas (SQLite)")
    root.geometry("1000x680")
    ttk.Style().theme_use("clam")

    # Variabel untuk form dan pencarian
    var_pompa = tk.StringVar()
    var_suhu = tk.StringVar()
    var_tekanan = tk.StringVar()
    var_getaran = tk.StringVar()
    var_status = tk.StringVar(value="Normal")
    var_cari = tk.StringVar()
    var_info = tk.StringVar()
    var_sql = tk.StringVar()

    # ---------- FORM INPUT ----------
    frm = ttk.LabelFrame(root, text="Form Data", padding=10)
    frm.pack(fill="x", padx=10, pady=(10, 5))

    judul_form = ["ID Pompa", "Suhu (C)", "Tekanan (psi)", "Getaran (mm/s)", "Status"]
    for i, teks in enumerate(judul_form):
        ttk.Label(frm, text=teks).grid(row=0, column=i, sticky="w", padx=5)

    ttk.Combobox(frm, textvariable=var_pompa, values=["P-01", "P-02", "P-03"],
                 width=12).grid(row=1, column=0, padx=5, pady=3)
    ttk.Entry(frm, textvariable=var_suhu, width=14).grid(row=1, column=1, padx=5)
    ttk.Entry(frm, textvariable=var_tekanan, width=14).grid(row=1, column=2, padx=5)
    ttk.Entry(frm, textvariable=var_getaran, width=14).grid(row=1, column=3, padx=5)
    ttk.Combobox(frm, textvariable=var_status, values=["Normal", "Rusak"],
                 state="readonly", width=12).grid(row=1, column=4, padx=5)

    # ---------- BAR PENCARIAN & AKSI ----------
    frm_cari = ttk.Frame(root)
    frm_cari.pack(fill="x", padx=10, pady=5)

    ttk.Label(frm_cari, text="Cari ID Pompa:").pack(side="left")
    ttk.Entry(frm_cari, textvariable=var_cari, width=12).pack(side="left", padx=5)

    # ---------- TABEL ----------
    frm_tabel = ttk.Frame(root)
    frm_tabel.pack(fill="both", expand=True, padx=10, pady=5)

    kolom = ("id", "pompa_id", "suhu_c", "tekanan_psi", "getaran_mm_s", "status")
    judul = ("ID", "Pompa", "Suhu (C)", "Tekanan (psi)", "Getaran (mm/s)", "Status")
    tabel = ttk.Treeview(frm_tabel, columns=kolom, show="headings", selectmode="browse")
    for k, j in zip(kolom, judul):
        tabel.heading(k, text=j, command=lambda c=k: urutkan(c))
        tabel.column(k, width=110, anchor="center")
    tabel.column("id", width=50)

    # Warna baris: merah = rusak, kuning = risiko tinggi
    tabel.tag_configure("rusak", background="#ffd6d6")
    tabel.tag_configure("risiko", background="#fff3c4")

    scroll = ttk.Scrollbar(frm_tabel, orient="vertical", command=tabel.yview)
    tabel.configure(yscrollcommand=scroll.set)
    tabel.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    ttk.Label(root, textvariable=var_info).pack(anchor="w", padx=12, pady=(0, 2))
    ttk.Label(root, textvariable=var_sql, font=("Consolas", 9), foreground="#555555",
              wraplength=960, justify="left").pack(anchor="w", padx=12, pady=(0, 8))

    # ---------- FUNGSI BANTU ----------
    def refresh(data=None):
        tampil = df if data is None else data
        tabel.delete(*tabel.get_children())
        for _, r in tampil.iterrows():
            tag = ()
            if r["status"] == "Rusak":
                tag = ("rusak",)
            elif r["getaran_mm_s"] > 3.0 and r["suhu_c"] > 80:
                tag = ("risiko",)
            tabel.insert("", "end", iid=str(int(r["id"])), tags=tag, values=(
                int(r["id"]), r["pompa_id"], r["suhu_c"],
                r["tekanan_psi"], r["getaran_mm_s"], r["status"]))

        if df.empty:
            var_info.set("Data kosong")
        else:
            rusak = int((df["status"] == "Rusak").sum())
            var_info.set(
                f"Menampilkan {len(tampil)} dari {len(df)} data  |  "
                f"Rusak: {rusak}  |  Rata-rata suhu: {df['suhu_c'].mean():.1f} C  |  "
                f"Merah = rusak, Kuning = risiko tinggi (getaran > 3.0 dan suhu > 80)"
            )
        var_sql.set("SQL terakhir: " + (SQL_TERAKHIR or "(belum ada)"))

    def segarkan():
        """Baca ulang data dari database (menghormati urutan & kata pencarian)."""
        nonlocal df
        df = baca_semua(urut["kol"], urut["naik"], catat=False)
        kata = var_cari.get().strip()
        if kata:
            refresh(baca_semua(urut["kol"], urut["naik"], kata, catat=False))
        else:
            refresh()

    def bersihkan_form():
        var_pompa.set("")
        var_suhu.set("")
        var_tekanan.set("")
        var_getaran.set("")
        var_status.set("Normal")
        tabel.selection_remove(tabel.selection())

    def ambil_sensor():
        """Membaca suhu, tekanan, getaran dari form. None jika tidak valid."""
        try:
            return (float(var_suhu.get().replace(",", ".")),
                    float(var_tekanan.get().replace(",", ".")),
                    float(var_getaran.get().replace(",", ".")))
        except ValueError:
            messagebox.showwarning("Peringatan",
                                   "Suhu, tekanan, dan getaran harus berupa angka.")
            return None

    def ambil_form():
        pompa = var_pompa.get().strip().upper()
        if not pompa:
            messagebox.showwarning("Peringatan", "ID Pompa wajib diisi.")
            return None
        sensor = ambil_sensor()
        if sensor is None:
            return None
        return (pompa,) + sensor + (var_status.get(),)

    def id_terpilih():
        pilihan = tabel.selection()
        if not pilihan:
            messagebox.showinfo("Info", "Pilih satu baris di tabel dulu.")
            return None
        return int(pilihan[0])

    def isi_form(event=None):
        pilihan = tabel.selection()
        if not pilihan:
            return
        baris = df[df["id"] == int(pilihan[0])]
        if baris.empty:
            return
        r = baris.iloc[0]
        var_pompa.set(r["pompa_id"])
        var_suhu.set(str(r["suhu_c"]))
        var_tekanan.set(str(r["tekanan_psi"]))
        var_getaran.set(str(r["getaran_mm_s"]))
        var_status.set(r["status"])

    tabel.bind("<<TreeviewSelect>>", isi_form)

    def tampil_teks(judul_jendela, teks, lebar=600, tinggi=520):
        win = tk.Toplevel(root)
        win.title(judul_jendela)
        win.geometry(f"{lebar}x{tinggi}")
        box = tk.Text(win, font=("Consolas", 10), wrap="none")
        box.pack(fill="both", expand=True)
        box.insert("1.0", teks)
        box.config(state="disabled")

    # ---------- CREATE (INSERT) ----------
    def tambah():
        data = ambil_form()
        if data is None:
            return
        try:
            id_baru = db_tambah(*data)
        except sqlite3.Error as e:
            messagebox.showerror("Error database", str(e))
            return
        segarkan()
        bersihkan_form()
        messagebox.showinfo("Berhasil", f"Data ditambahkan dengan id {id_baru}.")

    # ---------- UPDATE ----------
    def ubah():
        id_ubah = id_terpilih()
        if id_ubah is None:
            return
        data = ambil_form()
        if data is None:
            return
        try:
            db_ubah(id_ubah, *data)
        except sqlite3.Error as e:
            messagebox.showerror("Error database", str(e))
            return
        segarkan()
        bersihkan_form()
        messagebox.showinfo("Berhasil", "Data berhasil diubah.")

    # ---------- DELETE ----------
    def hapus():
        id_hapus = id_terpilih()
        if id_hapus is None:
            return
        if messagebox.askyesno("Konfirmasi", f"Yakin hapus data id {id_hapus}?"):
            try:
                db_hapus(id_hapus)
            except sqlite3.Error as e:
                messagebox.showerror("Error database", str(e))
                return
            segarkan()
            bersihkan_form()

    # ---------- CARI (SELECT ... WHERE ... LIKE) ----------
    def cari():
        kata = var_cari.get().strip()
        if not kata:
            tampil_semua()
            return
        refresh(baca_semua(urut["kol"], urut["naik"], kata))

    def tampil_semua():
        var_cari.set("")
        segarkan()

    # ---------- SORTING (SELECT ... ORDER BY) ----------
    def urutkan(kol):
        if urut["kol"] == kol:
            urut["naik"] = not urut["naik"]   # klik lagi di kolom yang sama = balik arah
        else:
            urut["kol"], urut["naik"] = kol, True
        segarkan()

    # ---------- ANALISIS & GRAFIK ----------
    def analisis():
        if df.empty:
            messagebox.showinfo("Info", "Data kosong.")
            return
        teks = (
            "Statistik deskriptif:\n" + df[FITUR].describe().round(2).to_string()
            + "\n\nRata-rata sensor per pompa:\n"
            + df.groupby("pompa_id")[FITUR].mean().round(2).to_string()
            + "\n\nJumlah status per pompa:\n"
            + pd.crosstab(df["pompa_id"], df["status"]).to_string()
        )
        tampil_teks("Ringkasan Analisis", teks, 580, 520)

    def grafik():
        import matplotlib.pyplot as plt
        if df.empty:
            messagebox.showinfo("Info", "Data kosong.")
            return
        df.boxplot(column="getaran_mm_s", by="status")
        plt.title("Getaran berdasarkan status pompa")
        plt.suptitle("")
        plt.ylabel("mm/s")
        plt.show()

    # ---------- EKSPOR ----------
    def ekspor():
        from tkinter import filedialog
        if df.empty:
            messagebox.showinfo("Info", "Data kosong.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
            initialfile="laporan_pompa")
        if not path:
            return
        try:
            if path.endswith(".csv"):
                df.to_csv(path, index=False)
            else:
                df.to_excel(path, index=False)
            messagebox.showinfo("Berhasil", f"Data diekspor ke:\n{path}")
        except ImportError:
            messagebox.showerror("Error", "Untuk Excel, jalankan dulu: python -m pip install openpyxl")

    # ---------- DATA LATIHAN & MACHINE LEARNING ----------
    def data_latihan():
        nonlocal model
        if messagebox.askyesno(
                "Konfirmasi",
                "Seluruh data akan DIGANTI dengan 300 data simulasi.\nLanjutkan?"):
            isi_tabel(buat_data_latihan(300))
            model = None
            segarkan()
            bersihkan_form()
            messagebox.showinfo("Berhasil", "300 data simulasi siap dipakai untuk ML.")

    def latih():
        nonlocal model
        try:
            hasil, laporan = latih_model(df)
        except ImportError:
            messagebox.showerror(
                "Error", "scikit-learn belum terpasang.\nJalankan: python -m pip install scikit-learn")
            return
        if hasil is None:
            messagebox.showwarning("Data belum cukup", laporan)
            return
        model = hasil
        tampil_teks("Hasil Pelatihan Model", laporan, 560, 440)

    def prediksi_gui():
        if model is None:
            messagebox.showinfo("Info", "Latih model dulu dengan tombol 'Latih Model'.")
            return
        sensor = ambil_sensor()
        if sensor is None:
            return
        label, p_rusak = prediksi(model, *sensor)
        pesan = f"Prediksi: {label}\nPeluang rusak: {p_rusak * 100:.0f}%"
        if label == "Rusak":
            messagebox.showwarning("Hasil Prediksi", pesan)
        else:
            messagebox.showinfo("Hasil Prediksi", pesan)

    # ---------- TOMBOL ----------
    frm_tombol = ttk.Frame(frm)
    frm_tombol.grid(row=2, column=0, columnspan=5, sticky="w", pady=(10, 0))
    ttk.Button(frm_tombol, text="Tambah", command=tambah).pack(side="left", padx=3)
    ttk.Button(frm_tombol, text="Ubah", command=ubah).pack(side="left", padx=3)
    ttk.Button(frm_tombol, text="Hapus", command=hapus).pack(side="left", padx=3)
    ttk.Button(frm_tombol, text="Bersihkan Form", command=bersihkan_form).pack(side="left", padx=3)
    ttk.Separator(frm_tombol, orient="vertical").pack(side="left", fill="y", padx=10)
    ttk.Button(frm_tombol, text="Data Latihan (300)", command=data_latihan).pack(side="left", padx=3)
    ttk.Button(frm_tombol, text="Latih Model", command=latih).pack(side="left", padx=3)
    ttk.Button(frm_tombol, text="Prediksi", command=prediksi_gui).pack(side="left", padx=3)

    ttk.Button(frm_cari, text="Cari", command=cari).pack(side="left", padx=3)
    ttk.Button(frm_cari, text="Tampilkan Semua", command=tampil_semua).pack(side="left", padx=3)
    ttk.Button(frm_cari, text="Ekspor", command=ekspor).pack(side="right", padx=3)
    ttk.Button(frm_cari, text="Grafik", command=grafik).pack(side="right", padx=3)
    ttk.Button(frm_cari, text="Analisis", command=analisis).pack(side="right", padx=3)

    refresh()
    root.mainloop()


# ---------------------------------------------------------------
# PROGRAM UTAMA
# ---------------------------------------------------------------
if __name__ == "__main__":
    siapkan_database()
    print("1. Mode terminal")
    print("2. Mode GUI")
    mode = input("Pilih mode: ").strip()
    if mode == "2":
        main_gui()
    else:
        main()