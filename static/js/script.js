// script.js – interaktivitas sederhana (jika diperlukan)
console.log("SIMBAH – Sistem Informasi Bank Sampah");

// Contoh: validasi form input data (opsional)
document.addEventListener('DOMContentLoaded', function() {
    const formInput = document.getElementById('formInput');
    if (formInput) {
        formInput.addEventListener('submit', function(e) {
            const berat = document.getElementById('berat').value;
            const harga = document.getElementById('harga').value;
            if (berat <= 0 || harga <= 0) {
                alert('Berat dan harga harus lebih dari 0!');
                e.preventDefault();
            }
        });
    }
});