# Coffee Senja LocalStack Order App

Aplikasi sederhana bertema **Coffee Senja** dengan UI final bergaya profesional untuk pemesanan coffee shop. Backend tetap berjalan di Docker dan menggunakan cloud emulator sesuai kebutuhan tugas.

Repository GitHub target:

```text
https://github.com/raafiprawiras/coffee-senja-localstack
```

## Fitur Aplikasi

- Customer page untuk melihat menu dan membuat order kopi.
- Admin login sederhana.
- Admin dashboard untuk melihat statistik, order, dan antrean barista.
- Tambah menu langsung dari website dan otomatis aktif di halaman customer.
- Upload foto ketika menambahkan menu.
- Ganti foto menu langsung dari Admin Dashboard.
- Foto menu tersimpan permanen di folder `static/uploads/menu`.
- Order coffee masuk ke sistem antrean barista.
- Barista queue diproses dari dashboard admin.
- Receipt digital dibuat otomatis setelah pesanan diproses.

## Services LocalStack yang Digunakan

| Service | Fungsi |
|---|---|
| DynamoDB | Menyimpan admin user, menu, dan order |
| SQS | Menyimpan antrean order barista |
| S3 | Menyimpan receipt digital |

## Akun Admin Default

```text
Username: admin
Password: admin123
```

## Cara Menjalankan di Localhost Docker

Pastikan Docker Desktop sudah berjalan.

```bash
docker compose down
docker compose up --build
```

Buka aplikasi:

```text
http://localhost:5000
```

LocalStack berjalan di:

```text
http://localhost:4566
```


## Live Edit dari VS Code

Project ini sudah memakai bind mount Docker:

```yaml
volumes:
  - .:/app
```

Artinya perubahan file di VS Code akan langsung masuk ke container. File yang paling sering diedit untuk frontend:

```text
templates/base.html      -> layout utama, navbar, branding
templates/index.html     -> halaman customer dan menu
templates/login.html     -> halaman login admin
templates/admin.html     -> dashboard admin
templates/receipt.html   -> halaman receipt digital
static/style.css         -> warna, layout, card, tombol, dan animasi
```

Setelah mengubah HTML/CSS, simpan file lalu refresh browser di `http://localhost:5000`. Untuk CSS, gunakan `CTRL + F5` jika browser masih menyimpan cache lama. Untuk perubahan Python di `app.py`, Flask sudah memakai `use_reloader=True`, sehingga aplikasi akan restart otomatis di container.

## Cara Menggunakan Aplikasi

1. Buka `http://localhost:5000`.
2. Pilih menu kopi di halaman Customer.
3. Isi nama customer, quantity, dan catatan.
4. Klik **Order Coffee**.
5. Order masuk ke DynamoDB dan SQS.
6. Login admin di menu **Admin Login**.
7. Gunakan akun `admin / admin123`.
8. Di dashboard admin, klik **Process Next Barista Queue**.
9. Status order berubah menjadi `READY`.
10. Receipt digital tersimpan di S3 dan bisa dilihat dari halaman receipt.

## Menambah Menu Permanen dari Website

1. Login admin.
2. Buka Admin Dashboard.
3. Isi form **Tambah Menu**: nama, kategori, harga, deskripsi, ikon, dan foto.
4. Klik **Simpan Menu Aktif**.
5. Menu langsung aktif dan muncul di halaman customer.
6. Data menu tersimpan di database lokal emulator selama volume Docker tidak dihapus. Gunakan `docker compose down` biasa, jangan `docker compose down -v`, jika ingin data tetap tersimpan.

## Mengganti Foto Menu dari Website

1. Login admin.
2. Buka bagian **Daftar Menu** di dashboard.
3. Pada kolom **Ganti Foto**, pilih file gambar.
4. Klik **Upload**.
5. Foto baru langsung tampil di dashboard dan halaman customer setelah refresh browser.

Format foto yang didukung: PNG, JPG, JPEG, WEBP, GIF, dan SVG. Foto yang diupload tersimpan di folder:

```text
static/uploads/menu
```

Karena project memakai bind mount Docker `.:/app`, foto yang diupload dari web akan muncul juga di folder project lokal dan tetap ada setelah container direstart.

## File Penting

```text
app.py                 -> logic utama Flask dan route aplikasi
aws_clients.py         -> koneksi boto3 ke LocalStack
init_resources.py      -> membuat DynamoDB table, SQS queue, S3 bucket, dan seed data
templates/             -> frontend HTML
static/style.css       -> desain UI elegan
static/uploads/menu/    -> foto menu bawaan dan foto hasil upload admin
requirements.txt       -> dependency Python
docker-compose.yml     -> container Flask app + LocalStack
Dockerfile             -> build image aplikasi Flask
```

## Troubleshooting

### Port 4566 sudah dipakai

Jika muncul error `port is already allocated`, hentikan container LocalStack lama:

```bash
docker ps
docker stop localstack
```

Lalu jalankan ulang:

```bash
docker compose up --build
```

### Rebuild dari awal

```bash
docker compose down
docker compose build --no-cache
docker compose up
```

## Upload ke GitHub

Jalankan dari folder project:

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

Jika repository lama sudah ada, gunakan:

```bash
git remote set-url origin https://github.com/raafiprawiras/coffee-senja-localstack.git
git push
```
