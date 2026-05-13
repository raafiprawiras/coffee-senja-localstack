# Coffee Senja LocalStack Order App

Aplikasi coffee shop premium bertema **Coffee Senja** dengan antarmuka modern dan profesional. Aplikasi ini mengintegrasikan sistem pemesanan lengkap dengan pengelolaan inventaris dan sistem membership, berjalan di atas Docker dengan cloud emulator LocalStack.

Repository GitHub:
```text
https://github.com/raafiprawiras/coffee-senja-localstack
```

## Fitur Unggulan

### 🛍️ Pengalaman Belanja (Customer)
- **Katalog Menu Interaktif**: Lihat menu berdasarkan kategori (Coffee, Non-Coffee, Snack, Dessert).
- **Sistem Keranjang (Cart)**: Tambahkan beberapa item sekaligus dengan catatan khusus untuk barista.
- **Sistem Promo**: Gunakan kode promo untuk mendapatkan potongan harga langsung.
- **Membership**: Daftarkan akun member untuk melihat riwayat pesanan pribadi dan mendapatkan promo eksklusif.
- **Digital Receipt**: Ambil struk digital otomatis dari S3 setelah pesanan selesai diproses.

### ☕ Manajemen Operasional (Admin)
- **Monitoring Dashboard**: Pantau pendapatan harian, jumlah transaksi, dan peringatan stok inventaris secara real-time.
- **Antrean Barista (SQS)**: Kelola antrean pesanan masuk melalui sistem queue yang reliabel.
- **Manajemen Menu**: Tambah, edit, atau nonaktifkan menu langsung dari dashboard (termasuk upload foto).
- **Manajemen Promo**: Buat dan hapus kode promo marketing secara dinamis.

## Services LocalStack yang Digunakan

| Service | Fungsi |
|---|---|
| **DynamoDB** | Penyimpanan database untuk User (Admin/Member), Menu, Pesanan, dan Promo. |
| **SQS** | Manajemen antrean pesanan (Barista Queue) untuk pemrosesan asinkron. |
| **S3** | Penyimpanan objek struk digital (Digital Receipt) dalam format JSON. |

## Akun Akses Default

### Admin Utama
```text
Username: admin
Password: admin123
```
*Catatan: Anda juga bisa mendaftar sebagai Member melalui halaman Login.*

## Cara Menjalankan

1. Pastikan **Docker Desktop** sudah aktif.
2. Jalankan perintah di folder project:
   ```bash
   docker compose up --build
   ```
3. Akses aplikasi di browser:
   - **Web App**: [http://localhost:5000](http://localhost:5000)
   - **LocalStack Health**: [http://localhost:4566](http://localhost:4566)

## Alur Penggunaan

### 1. Alur Customer & Member
- Pilih menu favorit dan klik **Tambah**.
- Atur jumlah dan catatan, lalu masukkan ke **Keranjang**.
- Buka Keranjang (ikon mengambang di kanan bawah), masukkan kode promo jika ada, dan isi nama.
- Klik **Buat Pesanan**.
- (Opsional) Login/Register sebagai Member untuk melihat riwayat pesanan di menu **Pesanan Saya**.

### 2. Alur Admin & Barista
- Login sebagai `admin`.
- Gunakan **Dashboard Harian** untuk memantau performa toko hari ini.
- Masuk ke **Admin Utama** untuk memproses antrean.
- Klik **Proses Antrean Berikutnya** untuk menyelesaikan pesanan pelanggan.
- Status pesanan akan berubah menjadi `READY` dan receipt digital akan terbit.

## Manajemen Menu (Admin)
- **Tambah Menu**: Gunakan form "Tambah Menu Baru" di dashboard admin. Upload foto untuk tampilan premium.
- **Edit Menu**: Klik tombol **Edit** pada daftar menu untuk mengubah detail atau **mengganti foto menu**.
- **Foto Menu**: File tersimpan di `static/uploads/menu` dan tetap ada meskipun container direstart (berkat Docker bind mount).

## Troubleshooting

- **Port Conflict (4566/5000)**: Pastikan tidak ada service LocalStack atau Flask lain yang berjalan di background. Gunakan `docker compose down` untuk membersihkan.
- **CSS Tidak Berubah**: Gunakan `CTRL + F5` untuk force refresh cache browser.
- **Data Terhapus**: Jangan gunakan flag `-v` saat mematikan container (`docker compose down -v`) jika ingin data DynamoDB tetap tersimpan.

---
© 2025 Coffee Senja - Specialty Coffee Experience.
