"""
SIMBAH - Sistem Informasi Bank Sampah
Flask application with JSON storage and PDF report generation.
"""

import os
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from fpdf import FPDF

from flask import Flask
app = Flask(__name__)
app.secret_key = "simbah_secret_key_123"
@app.template_filter('format_number')
def format_number(value):
    try:
        return "{:,.0f}".format(value).replace(",", ".")
    except:
        return value

# Konstanta file data
DATA_FILE = 'data_transaksi.json'
REPORT_FOLDER = 'reports'
os.makedirs(REPORT_FOLDER, exist_ok=True)

# ==================== HELPER FUNCTIONS ====================
def load_transactions():
    """Membaca semua transaksi dari file JSON."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_transactions(transactions):
    """Menyimpan transaksi ke file JSON."""
    with open(DATA_FILE, 'w') as f:
        json.dump(transactions, f, indent=4)

# ==================== DECORATOR LOGIN ====================
def login_required(f):
    """Decorator untuk membatasi akses hanya untuk admin yang sudah login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROUTES PUBLIC ====================
@app.route('/')
def index():
    """Landing page (splash screen) dengan tombol MASUK menuju beranda."""
    return render_template('index.html')

@app.route('/beranda')
def beranda():
    """Halaman beranda publik dengan fitur-fitur."""
    return render_template('beranda.html')

@app.route('/anggota')
def anggota():
    """Halaman profil anggota pengurus bank sampah."""
    return render_template('anggota.html')

@app.route('/dokumentasi')
def dokumentasi():
    """Halaman dokumentasi kegiatan."""
    return render_template('dokumentasi.html')

# ==================== ROUTES ADMIN (LOGIN & DASHBOARD) ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Halaman login admin. Credential sederhana."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Contoh validasi sederhana (hardcoded)
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['username'] = username
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout admin."""
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard admin: menampilkan semua transaksi dalam tabel."""
    transactions = load_transactions()
    return render_template('dashboard.html', transactions=transactions)

@app.route('/input-data', methods=['GET', 'POST'])
@login_required
def input_data():
    if request.method == 'POST':
        nama = request.form['nama']
        # Ambil data sebagai list
        barangs = request.form.getlist('barang[]')
        berats = request.form.getlist('berat[]')
        hargas = request.form.getlist('harga[]')
        
        hari = request.form['hari']
        tanggal = int(request.form['tanggal'])
        bulan = request.form['bulan']
        tahun = int(request.form['tahun'])
        waktu = request.form['waktu']

        transactions = load_transactions()

        # Gabungkan semua barang menjadi satu string atau buat entri terpisah
        # Di sini kita buat entri terpisah untuk setiap jenis barang agar tabel tetap rapi
        for i in range(len(barangs)):
            if barangs[i]: # Pastikan nama barang tidak kosong
                b_berat = float(berats[i])
                b_harga = float(hargas[i])
                new_trans = {
                    "nama": nama,
                    "barang": barangs[i],
                    "berat": b_berat,
                    "harga": b_harga,
                    "total": b_berat * b_harga,
                    "hari": hari,
                    "tanggal": tanggal,
                    "bulan": bulan,
                    "tahun": tahun,
                    "waktu": waktu
                }
                transactions.append(new_trans)

        save_transactions(transactions)
        flash(f'Berhasil menyimpan {len(barangs)} jenis sampah.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('input_data.html')
    # --- FITUR HAPUS SATU DATA ---
@app.route('/delete-transaction', methods=['POST'])
@login_required
def delete_transaction():
    """Menghapus seluruh grup transaksi berdasarkan nama dan waktu."""
    nama = request.form.get('nama')
    waktu = request.form.get('waktu')
    
    transactions = load_transactions()
    
    # Filter: Hanya simpan transaksi yang TIDAK cocok dengan nama DAN waktu yang dikirim
    # Ini akan menghapus semua barang dalam satu sesi transaksi tersebut
    new_transactions = [
        t for t in transactions 
        if not (t['nama'] == nama and t['waktu'] == waktu)
    ]
    
    save_transactions(new_transactions)
    flash(f'Seluruh transaksi atas nama {nama} berhasil dihapus.', 'success')
    
    return redirect(url_for('dashboard'))
# --- FITUR HAPUS SEMUA DATA ---
@app.route('/delete-all-transactions', methods=['POST'])
@login_required
def delete_all_transactions():
    save_transactions([]) 
    flash('Seluruh data berhasil dihapus.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/generate-laporan', methods=['POST'])
@login_required
def generate_laporan():
    """
    Generate PDF laporan berdasarkan bulan dan tahun yang dipilih.
    """
    bulan = request.form['bulan']
    tahun = int(request.form['tahun'])

    # Filter transaksi berdasarkan bulan dan tahun
    transactions = load_transactions()
    filtered = [
        t for t in transactions
        if t['bulan'].lower() == bulan.lower() and t['tahun'] == tahun
    ]

    if not filtered:
        flash('Tidak ada transaksi untuk periode tersebut.', 'warning')
        return redirect(url_for('dashboard'))

    # Hitung total berat dan total nilai
    total_berat = sum(t['berat'] for t in filtered)
    total_nilai = sum(t['total'] for t in filtered)

    # Buat PDF
    pdf = FPDF(orientation='L', unit='mm', format='A4')  # Landscape
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)

    # Judul
    pdf.cell(0, 10, 'LAPORAN TRANSAKSI BANK SAMPAH PELANGI', ln=1, align='C')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'BANK SAMPAH PELANGI DAN MAGOT', ln=1, align='C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, f'Periode: {bulan} {tahun}', ln=1, align='C')
    pdf.ln(5)

    # Header tabel
    pdf.set_font('Arial', 'B', 9)
    headers = ['No', 'Nama', 'Barang', 'Berat (Kg)', 'Harga/Kg', 'Total', 'Hari', 'Tanggal', 'Waktu']
    col_widths = [10, 35, 30, 20, 25, 25, 20, 20, 25]

    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, align='C')
    pdf.ln()

    # Data tabel
    pdf.set_font('Arial', '', 8)
    last_name = ""
    last_time = ""
    
    for idx, t in enumerate(filtered, start=1):
        # Cek apakah ini transaksi yang sama dengan baris sebelumnya
        is_same_group = (t['nama'] == last_name and t['waktu'] == last_time)
        
        # Jika sama, kosongkan kolom nama, hari, tgl, dan waktu
        display_no = str(idx) if not is_same_group else ""
        display_nama = t['nama'] if not is_same_group else ""
        display_hari = t['hari'] if not is_same_group else ""
        display_tgl = str(t['tanggal']) if not is_same_group else ""
        display_waktu = t['waktu'] if not is_same_group else ""

        row = [
            display_no,
            display_nama,
            t['barang'],
            f"{t['berat']:.2f}",
            f"Rp {t['harga']:,.0f}".replace(",", "."),
            f"Rp {t['total']:,.0f}".replace(",", "."),
            display_hari,
            display_tgl,
            display_waktu
        ]
        for i, value in enumerate(row):
            pdf.cell(col_widths[i], 8, value, border=1, align='C')
        pdf.ln()

        # Update penanda untuk baris berikutnya
        last_name = t['nama']
        last_time = t['waktu']

    # Ringkasan
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, f"Total Berat Sampah Bulan Ini: {total_berat:.2f} Kg", ln=1)
    pdf.cell(0, 8, f"Total Nilai Pembelian Sampah: Rp {total_nilai:,.0f}", ln=1)

    # Simpan file PDF
    filename = f"laporan_{bulan}_{tahun}.pdf"
    filepath = os.path.join(REPORT_FOLDER, filename)
    pdf.output(filepath)

    return send_file(filepath, as_attachment=True, download_name=filename)

# ==================== JALANKAN APLIKASI ====================
if __name__ == '__main__':
    app.run(debug=True)