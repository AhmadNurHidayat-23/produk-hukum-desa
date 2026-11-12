# Produk Hukum Desa

Arsip dan publikasi peraturan desa. Prototipe portofolio independen; seluruh dokumen adalah contoh tanpa kekuatan hukum.

## Fitur utama

- CRUD metadata nomor/tahun/kategori, status Berlaku/Dicabut, pencarian/filter serta arsip dan pemulihan.
- Unggah PDF contoh maksimal 5 MB/100 halaman, pemeriksaan isi/format, penyimpanan privat, versi berkas dan unduhan terkontrol.
- Hubungan perubahan/pencabutan tanpa siklus; pencabutan memperbarui status dalam satu transaksi.
- Katalog publik hanya memuat dokumen yang sengaja dipublikasikan. Admin mengelola arsip; Petugas menelusuri dan mengunduh.

## Teknologi

Python 3.13, Flask, SQLite, pypdf, HTML, CSS, JavaScript.

## Cara instalasi

~~~powershell
cd C:\laragon\www\produk-hukum-desa
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m core.users --role Admin
~~~

Ulangi dengan --role Petugas bila diperlukan. Tidak ada akun bawaan.

## Cara menjalankan

~~~powershell
.venv\Scripts\python run.py
~~~

Buka http://127.0.0.1:5491 dan /kelola untuk pengelola. SQLite serta unggahan privat dibuat otomatis di instance; APP_INSTANCE mengganti lokasi. SECURE_COOKIE=1 untuk HTTPS. Tes: .venv\Scripts\python -m pytest -q. Gunakan PDF contoh yang tersedia pada aplikasi. Judul wajib memuat Contoh atau Demonstrasi; PDF wajib memuat DEMONSTRASI dan TIDAK RESMI, tanpa enkripsi, formulir, aksi aktif atau lampiran. Publikasi memerlukan PDF. Setiap unggahan versi baru menonaktifkan publikasi hingga ditinjau dan dipublikasikan kembali. Arsip/pemulihan selalu menonaktifkan publikasi.
