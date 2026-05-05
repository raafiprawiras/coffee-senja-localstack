# Manual Penggunaan - Coffee Senja

## 1. Deskripsi Aplikasi

Coffee Senja adalah aplikasi coffee shop modern bernuansa senja berbasis Flask yang berjalan di localhost menggunakan Docker Compose dan LocalStack. Aplikasi ini menggunakan tiga layanan cloud emulator: DynamoDB, SQS, dan S3.

Link kode GitHub:

```text
https://github.com/raafiprawiras/coffee-senja-localstack
```

## 2. Service Cloud yang Digunakan

1. DynamoDB: menyimpan data admin, menu, dan order customer.
2. SQS: menyimpan antrean order untuk diproses barista.
3. S3: menyimpan receipt digital setelah order selesai.

## 3. Cara Menjalankan

Pastikan Docker Desktop aktif, lalu buka terminal di folder project:

```bash
cd C:/python/coffee-senja-localstack
docker compose up --build
```

Buka aplikasi di browser:

```text
http://localhost:5000
```


## 4. Edit Tampilan Langsung dari VS Code

Project sudah terhubung dengan Docker bind mount:

```yaml
volumes:
  - .:/app
```

Jadi file yang diedit di VS Code langsung terbaca oleh web localhost. Untuk mengubah tampilan, edit file berikut:

```text
templates/base.html    = navbar, logo, branding
templates/index.html   = halaman customer dan kartu menu
templates/login.html   = halaman login admin
templates/admin.html   = dashboard admin
templates/receipt.html = tampilan receipt digital
static/style.css       = warna, layout, tombol, glassmorphism, animasi
```

Setelah menyimpan perubahan, refresh `http://localhost:5000`. Jika CSS belum berubah, tekan `CTRL + F5`.

## 5. Alur Customer

1. Buka halaman utama.
2. Pilih menu kopi.
3. Isi nama customer, jumlah pesanan, dan catatan.
4. Klik Order Coffee.
5. Order masuk ke DynamoDB dan dikirim ke SQS sebagai antrean barista.
6. Customer dapat membuka halaman receipt. Jika belum diproses, receipt S3 belum tersedia.

## 6. Alur Admin

Login admin:

```text
Username: admin
Password: admin123
```

Setelah login, admin dapat:

1. Melihat dashboard dan statistik order.
2. Menambahkan menu baru langsung dari website.
3. Melihat antrean order barista.
4. Klik Process Next Barista Queue untuk memproses order dari SQS.
5. Setelah diproses, status order menjadi READY dan receipt JSON tersimpan di S3.

## 7. Upload GitHub

Buat repository GitHub kosong dengan nama:

```text
coffee-senja-localstack
```

Lalu jalankan:

```bash
git init
git config user.name "raafiprawiras"
git config user.email "raafiprawiras@gmail.com"
git add .
git commit -m "Initial commit - Coffee Senja LocalStack app"
git branch -M main
git remote add origin https://github.com/raafiprawiras/coffee-senja-localstack.git
git push -u origin main
```

Jika diminta password saat push, gunakan Personal Access Token GitHub, bukan password biasa.

## 8. Digunakan Orang Lain di Localhost

Orang lain cukup menjalankan:

```bash
git clone https://github.com/raafiprawiras/coffee-senja-localstack.git
cd coffee-senja-localstack
docker compose up --build
```

Lalu buka:

```text
http://localhost:5000
```

## Tambah Menu Permanen dan Upload Foto

1. Login admin melalui tombol **Admin**.
2. Masuk ke dashboard.
3. Isi form **Tambah Menu**.
4. Pilih foto menu pada field **Foto Menu**.
5. Klik **Simpan Menu Aktif**.
6. Menu baru langsung muncul di halaman customer sebagai menu aktif.

Untuk mengganti foto menu lama, gunakan bagian **Daftar Menu** pada dashboard, pilih file di kolom **Ganti Foto**, lalu klik **Upload**.

Data menu tersimpan di database lokal emulator. Foto menu tersimpan di folder project `static/uploads/menu`, sehingga tetap ada ketika container direstart. Jangan menjalankan `docker compose down -v` jika ingin data database tetap tersimpan.
