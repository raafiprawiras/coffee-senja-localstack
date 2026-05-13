# Manual Penggunaan - Coffee Senja

Coffee Senja adalah aplikasi coffee shop modern berbasis Flask yang berjalan menggunakan Docker Compose dan LocalStack. Manual ini menjelaskan fitur-fitur terbaru termasuk sistem membership, keranjang belanja, dan dashboard operasional.

## 1. Persiapan Awal
Pastikan Docker Desktop sudah aktif, lalu jalankan aplikasi:
```bash
docker compose up --build
```
Akses melalui browser di `http://localhost:5000`.

## 2. Fitur Membership (Akun Pelanggan)
Aplikasi kini mendukung sistem akun untuk pelanggan:
1. **Registrasi**: Buka halaman **Login**, pilih tab **Daftar Member**.
2. **Login**: Masuk dengan username yang sudah didaftarkan.
3. **Keuntungan**: Member dapat melihat riwayat pesanan mereka di halaman **Pesanan Saya**.
4. **Promo**: Member memiliki akses ke promo-promo eksklusif (jika diaktifkan oleh admin).

## 3. Alur Pemesanan (Customer)
1. **Eksplorasi**: Pilih kategori menu (Coffee, Non-Coffee, dsb).
2. **Keranjang**: Klik **Tambah** pada menu, isi jumlah dan catatan, lalu klik **Tambahkan ke Keranjang**.
3. **Checkout**:
   - Klik ikon keranjang di pojok kanan bawah.
   - Masukkan **Kode Promo** (contoh: SENJA20) jika ada.
   - Isi Nama Customer dan klik **Buat Pesanan**.
4. **Struk**: Anda akan diarahkan ke halaman Receipt. Jika status masih `QUEUED`, struk digital S3 belum bisa dibuka.

## 4. Dashboard Operasional (Admin)
Admin memiliki dua tampilan utama yang dapat diakses dari navbar:

### A. Dashboard Harian (Operations)
Tampilan untuk pemantauan cepat:
- **Metrik Hari Ini**: Total pendapatan dan jumlah transaksi hari ini.
- **Peringatan Stok**: Daftar bahan baku (simulasi) yang perlu segera diisi ulang.
- **Aktivitas Terbaru**: List pesanan yang baru saja masuk.

### B. Admin Utama (Management)
Tampilan untuk pengelolaan data:
- **Proses Antrean**: Klik **Proses Antrean Berikutnya** untuk memproses pesanan di SQS.
- **Manajemen Menu**:
  - **Tambah**: Isi form menu baru dan upload foto.
  - **Edit**: Klik **Edit** pada tabel menu untuk mengubah data atau **Ganti Foto**.
  - **Hapus**: Menghapus menu secara permanen.
- **Manajemen Promo**: Tambah atau hapus kode promo untuk diskon pelanggan.

## 5. Pengelolaan Media (Foto Menu)
- **Lokasi**: Foto yang diupload tersimpan di `static/uploads/menu/`.
- **Keamanan Data**: Karena menggunakan Docker volumes, foto tidak akan hilang saat container dimatikan.
- **Format**: Gunakan format PNG, JPG, atau WEBP untuk hasil terbaik.

## 6. Detail Akun Default
- **Admin**: `admin` / `admin123`
- **Member**: Silakan daftar akun baru melalui halaman registrasi.

## 7. Pemeliharaan Database (LocalStack)
- **Persistensi**: Data DynamoDB tersimpan selama volume docker tidak dihapus.
- **Reset Data**: Jika ingin membersihkan database, jalankan `docker compose down -v`.

---
© 2025 Coffee Senja - Specialty Coffee Experience.
