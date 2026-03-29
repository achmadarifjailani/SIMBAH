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
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_transactions(transactions):
    with open(DATA_FILE, 'w') as f:
        json.dump(transactions, f, indent=4)

# ==================== DECORATOR LOGIN ====================
def login_required(f):
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
    return render_template('index.html')

@app.route('/beranda')
def beranda():
    return render_template('beranda.html')

@app.route('/anggota')
def anggota():
    return render_template('anggota.html')

@app.route('/dokumentasi')
def dokumentasi():
    return render_template('dokumentasi.html')

# ==================== ROUTES ADMIN ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
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
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    transactions = load_transactions()
    return render_template('dashboard.html', transactions=transactions)

@app.route('/input-data', methods=['GET', 'POST'])
@login_required
def input_data():
    if request.method == 'POST':
        nama = request.form['nama']
        metode_bayar = request.form['metode_bayar']
        nomor_pembayaran = request.form['nomor_pembayaran']
        
        hari = request.form['hari']
        tanggal = request.form['tanggal']
        bulan = request.form['bulan']
        tahun = int(request.form['tahun'])
        waktu = request.form['waktu']

        barangs = request.form.getlist('barang[]')
        berats = request.form.getlist('berat[]')
        hargas = request.form.getlist('harga[]')

        transactions = load_transactions()
        
        for i in range(len(barangs)):
            if barangs[i]:
                b_berat = float(berats[i])
                b_harga = float(hargas[i])
                new_trans = {
                    "nama": nama,
                    "metode_bayar": metode_bayar,
                    "nomor_pembayaran": nomor_pembayaran,
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
        flash('Transaksi Multi-Sampah berhasil disimpan!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('input_data.html')

@app.route('/delete-transaction', methods=['POST'])
@login_required
def delete_transaction():
    nama = request.form.get('nama')
    waktu = request.form.get('waktu')
    
    transactions = load_transactions()
    new_transactions = [
        t for t in transactions 
        if not (t['nama'] == nama and t['waktu'] == waktu)
    ]
    
    save_transactions(new_transactions)
    flash(f'Transaksi atas nama {nama} pada jam {waktu} berhasil dihapus.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete-all-transactions', methods=['POST'])
@login_required
def delete_all_transactions():
    save_transactions([]) 
    flash('Seluruh database transaksi telah dikosongkan.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/generate-laporan', methods=['POST'])
@login_required
def generate_laporan():
    bulan = request.form['bulan']
    tahun = int(request.form['tahun'])

    transactions = load_transactions()
    filtered = [
        t for t in transactions
        if t['bulan'].lower() == bulan.lower() and t['tahun'] == tahun
    ]

    if not filtered:
        flash('Tidak ada transaksi untuk periode tersebut.', 'warning')
        return redirect(url_for('dashboard'))

    total_berat = sum(t['berat'] for t in filtered)
    total_nilai = sum(t['total'] for t in filtered)

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'REKAPITULASI SETORAN NASABAH', ln=1, align='C')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'BANK SAMPAH PELANGI RUMAH MAGGOT', ln=1, align='C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, f'Periode Laporan: {bulan} {tahun}', ln=1, align='C')
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 9)
    col_widths = [10, 55, 35, 20, 25, 25, 20, 20, 25]
    headers = ['No', 'Nama Nasabah & Pembayaran', 'Jenis Barang', 'Berat', 'Harga/Kg', 'Subtotal', 'Hari', 'Tgl', 'Waktu']

    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, align='C')
    pdf.ln()

    # --- BAGIAN DATA TABEL (DENGAN INDENTASI YANG BENAR) ---
    pdf.set_font('Arial', '', 8)
    last_name = ""
    last_time = ""
    display_no_counter = 0

    for t in filtered:
        is_same_group = (t['nama'] == last_name and t['waktu'] == last_time)

        if not is_same_group:
            display_no_counter += 1
            display_no = str(display_no_counter)
            display_nama = f"{t['nama']} ({t['metode_bayar']}: {t['nomor_pembayaran']})"
            display_hari = t['hari']
            display_tgl = str(t['tanggal'])
            display_waktu = t['waktu']
        else:
            display_no = ""
            display_nama = ""
            display_hari = ""
            display_tgl = ""
            display_waktu = ""

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

        last_name = t['nama']
        last_time = t['waktu']

    # Footer Ringkasan
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, f"Total Berat Terkumpul: {total_berat:.2f} Kg", ln=1)
    pdf.cell(0, 8, f"Total Dana Keluar: Rp {total_nilai:,.0f}".replace(",", "."), ln=1)

    filename = f"laporan_{bulan}_{tahun}.pdf"
    filepath = os.path.join(REPORT_FOLDER, filename)
    pdf.output(filepath)
    return send_file(filepath, as_attachment=True, download_name=filename)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
