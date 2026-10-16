# Jualans

Prototipe aplikasi pembukuan untuk usaha kecil di Indonesia (warung makan, laundry kiloan, fotokopi, jajanan).
Pemilik usaha cukup **mengetik seperti chat**, **bicara lewat mikrofon**, atau **memotret nota belanja**,
lalu Jualans mengubahnya menjadi catatan uang masuk dan uang keluar.

> Ini prototipe tampilan (frontend saja). Belum ada server, database, atau login sungguhan.
> Data disimpan di memori browser dan kembali ke data contoh setiap halaman dimuat ulang.

## Cara membuka

Buka `index.html` di Chrome (klik dua kali). Dibutuhkan koneksi internet karena React, Tailwind,
dan pembaca nota dimuat dari CDN.

Untuk mencoba mikrofon, buka lewat alamat `localhost` atau `https`, misalnya:

```bash
python3 -m http.server 8000
```

lalu buka http://localhost:8000.

## Fitur

- **Catat lewat chat**: "jual 10 cilok 50rb", "beli tepung tapioka 5kg 65rb", "bayar gas 22 ribu".
  Aplikasi membalas dengan kartu konfirmasi (Simpan / Ubah).
- **Catat pakai suara**: angka yang diucapkan ("lima puluh ribu") ikut terbaca. Ada mode simulasi
  kalau browser tidak mendukung.
- **Scan nota**: OCR di browser (Tesseract.js) membaca barang, harga, total, diskon, dan tanggal.
  Total nota dipakai untuk memeriksa dan membetulkan angka yang salah baca.
- **Beranda**: untung, uang masuk, uang keluar per hari / minggu / bulan, grafik batang, transaksi terakhir.
- **Riwayat**: pencarian, filter tanggal dan kategori, ubah dan hapus transaksi.
- **Bon pelanggan**: daftar utang pelanggan, tandai lunas (sekalian dicatat sebagai uang masuk).
- **Stok bahan**: bertambah otomatis dari belanja, berkurang lewat "pakai tepung 2kg",
  peringatan saat hampir habis.
- **Pengaturan**: profil usaha, daftar kategori, kosongkan / isi ulang data contoh.

## Isi repositori

| File | Isi |
|---|---|
| `index.html` | Seluruh aplikasi (React + Tailwind dalam satu file) |
| `PROMPT.md` | Prompt lengkap untuk membuat ulang aplikasi ini |

## Teknologi

React 18, Tailwind CSS, Babel standalone, Tesseract.js 5, Web Speech API, font Plus Jakarta Sans.
