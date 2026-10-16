Buatkan prototipe aplikasi web (frontend saja) bernama Jualans. Ini aplikasi
pembukuan untuk usaha kecil di Indonesia, seperti warung makan, laundry kiloan,
fotokopi, dan jajanan.

MASALAH YANG DISELESAIKAN
Pemilik usaha kecil jarang mencatat keuangan karena mengisi form terasa
merepotkan. Di aplikasi ini mereka mencatat dengan cara yang paling cepat:
mengetik bebas seperti chat ("jual 3 nasi ayam 45rb"), bicara lewat mikrofon,
atau memotret nota belanja. Aplikasi lalu mengubahnya menjadi data transaksi.

PENGGUNA
Pemilik usaha kecil, usia 25 sampai 55 tahun, memakai HP Android, tidak paham
istilah akuntansi, dan sering membuka aplikasi sambil melayani pelanggan.

TEKNOLOGI
- React dan Tailwind CSS. Boleh satu file index.html yang memuat React, ReactDOM,
  Babel standalone, dan Tailwind dari CDN, supaya bisa dibuka tanpa proses build.
- Belum perlu backend atau database. Simpan semua data di state React, supaya
  transaksi baru langsung muncul di Beranda, Riwayat, dan Stok.
- Pembaca nota: Tesseract.js dari CDN (bahasa "ind"), berjalan di browser.
- Input suara: Web Speech API bawaan browser (SpeechRecognition, lang "id-ID").
- Font: Plus Jakarta Sans dari Google Fonts.

====================================================================
HALAMAN SEBELUM LOGIN
====================================================================
1. Landing: logo dan nama Jualans, judul "Catat jualan semudah kirim chat.",
   penjelasan singkat (ketik, ucapkan, atau foto nota), contoh percakapan chat
   (pesan pengguna lalu kartu hasil, satu uang masuk dan satu uang keluar),
   empat keunggulan singkat (tahu untung tiap hari, catat bon pelanggan, pantau
   stok bahan, cocok untuk usaha kecil), tombol "Daftar gratis" dan "Login"
   yang menempel di bawah layar.
2. Daftar: nama, nomor HP atau email, kata sandi (dengan tombol lihat/sembunyi).
3. Setup usaha: muncul sekali setelah mendaftar. Isinya nama usaha dan jenis
   usaha dalam bentuk pilihan kartu (Cilok goreng, Warung makan, Laundry kiloan,
   Fotokopi, Toko kelontong, Lainnya). Pilihan "Lainnya" memunculkan kolom isian.
4. Login: nomor HP atau email, kata sandi, tautan "Lupa kata sandi?" (cukup
   tampilkan notifikasi "belum tersedia").
Login dan Daftar cukup berpindah halaman tanpa pemeriksaan sungguhan.

====================================================================
HALAMAN SETELAH LOGIN
====================================================================
5. BERANDA (kerjakan paling teliti)
   - Header: sapaan sesuai jam ("Selamat pagi, Rina"), nama usaha, ikon profil
     di pojok kanan atas yang menuju Pengaturan.
   - Pilihan periode: Hari ini, Minggu ini (7 hari terakhir), Bulan ini.
   - Kartu utama berwarna utama: "Untung" (atau "Rugi" jika minus) dengan angka
     besar, rentang tanggal, lalu dua kotak "Uang masuk" (+, hijau) dan
     "Uang keluar" (−, merah).
   - Grafik batang sederhana tanpa pustaka grafik: dua batang (masuk dan keluar)
     per kelompok. Hari ini dibagi Pagi/Siang/Sore/Malam, Minggu ini per hari,
     Bulan ini per pekan (1–7, 8–14, dst). Batang bisa diketuk untuk
     menampilkan angkanya. Yang terpilih pertama kali adalah kelompok terakhir
     yang sudah ada isinya, bukan kelompok kosong.
   - Kartu ringkasan Bon: total bon belum dibayar dan jumlah pelanggan, menuju Bon.
   - Kartu Stok bahan: menyebut bahan yang perlu dibeli, atau "Semua stok aman",
     menuju halaman Stok.
   - Lima transaksi terakhir dengan tautan "Lihat semua". Ketuk satu transaksi
     untuk mengubahnya.
   - Tombol "Catat manual pakai form".

6. CATAT (fitur utama, kerjakan paling teliti)
   Tampilan chat. Pesan pengguna di kanan, balasan aplikasi di kiri, dengan
   animasi "sedang mengetik" sebelum balasan muncul.
   Pesan pembuka menjelaskan cara pakai: kata "jual" untuk uang masuk, "beli"
   atau "bayar" untuk uang keluar; tombol mikrofon untuk bicara; tombol kamera
   untuk foto nota; "pakai tepung 2kg" untuk stok.

   Bilah bawah (menempel di atas menu bawah):
   - Deretan contoh pesan yang bisa diketuk untuk mengisi kolom: "jual 10 cilok
     50rb", "beli tepung tapioka 5kg 65rb", "bayar gas 22 ribu", "pakai tepung
     2kg", "cek stok", "kemarin jual es teh 15 gelas 45rb".
   - [tombol kamera] [kolom ketik] [tombol mikrofon]. Begitu ada teks, tombol
     mikrofon berganti menjadi tombol kirim.
   - Tombol "Form" di header untuk input manual.

   Tiru AI dengan aturan sederhana (tanpa AI sungguhan):
   - Jenis: kata yang mengandung "jual", "laku", "laris" berarti uang masuk;
     "beli", "bayar", "belanja" berarti uang keluar. Jika keduanya ada, yang
     muncul lebih dulu yang dipakai.
   - Nominal: "45rb", "45 ribu", "45k" = 45.000; "1,5jt" atau "1,5 juta" =
     1.500.000; "Rp45.000", "45.000", atau angka ≥ 1000 juga dianggap nominal.
     Angka kecil seperti "3" atau "5kg" bukan nominal. Jika ada beberapa, pakai
     yang terakhir.
   - Angka dalam bentuk kata (dari input suara) diubah dulu menjadi angka:
     "lima puluh ribu" = 50000, "sepuluh" = 10, "dua puluh lima" = 25,
     "seratus", "seribu", "setengah" = 0,5, "satu setengah" = 1,5.
   - Tanggal: "kemarin" mundur 1 hari, "3 hari lalu" mundur 3 hari, selain itu
     hari ini.
   - Barang: sisa kalimat setelah kata jenis, nominal, dan kata keterangan waktu
     dibuang. "jual 3 nasi ayam 45rb" menjadi barang "Nasi ayam (3)".
   - Kategori: uang masuk menjadi Penjualan (atau Pesanan jika ada kata
     pesanan/arisan/katering). Uang keluar ditebak dari kata kunci: tepung,
     daging, minyak, bumbu, gula, teh menjadi Bahan baku; gas, listrik, plastik,
     tusuk, bensin menjadi Operasional; gaji/upah menjadi Gaji; sewa/lapak
     menjadi Sewa; lainnya menjadi Lain-lain.
   - Jumlah dan satuan (5kg, 2 liter, 2 tabung, 3 pak) dibaca untuk stok.

   Balasan aplikasi:
   - Terbaca lengkap: kartu konfirmasi berisi jenis (Uang masuk (+) atau Uang
     keluar (−)), nominal besar berwarna, barang, kategori, tanggal, dan baris
     "Masuk stok" jika belanjaan cocok dengan bahan di stok. Tombol Ubah,
     Simpan, dan "Batal, bukan ini". Setelah disimpan, kartu bertanda
     "Tersimpan" dengan tautan "Lihat di Riwayat", lalu aplikasi membalas
     "Sip, sudah dicatat. Untung hari ini sekarang +Rp…".
   - Ada nominal tapi jenisnya tidak jelas ("tadi 15.000"): tanya "Ini uang
     masuk atau uang keluar?" dengan dua tombol.
   - Ada jenis tapi tanpa nominal: minta pengguna mengulang dengan harga, plus
     tombol "Isi form manual" yang sudah terisi.
   - Tidak terbaca sama sekali: minta mengulang dengan contoh, plus tombol
     "Isi form manual".
   - Pesan berisi bon/utang/ngutang/kasbon: arahkan ke menu Bon.
   - "pakai tepung 2kg": kartu "Stok dipakai" (bahan, jumlah dipakai, sisa,
     status) dengan Ubah/Simpan/Batal. Hanya mengurangi stok, tidak dihitung
     sebagai uang keluar. Jika bahan tidak ada di stok, arahkan ke halaman Stok.
   - "cek stok": daftar bahan yang perlu dibeli.
   - Belanja yang cocok dengan bahan stok tapi tanpa jumlah: setelah disimpan,
     tawarkan "Mau tambah stok … juga?" dengan tombol.

   Catat pakai suara:
   - Tombol mikrofon membuka panel di atas menu bawah: ikon mikrofon berdenyut,
     tulisan "Mendengarkan…", teks yang terucap muncul langsung, serta tombol
     Batal dan Selesai. Setelah selesai bicara, teks otomatis terkirim dan
     diproses seperti pesan ketik.
   - Jika mikrofon ditolak, suara tidak terdengar, atau browser tidak mendukung,
     tampilkan pesan yang jelas dengan tombol Tutup, Simulasi, dan Coba lagi.
   - Mode simulasi "mengucapkan" contoh kalimat kata demi kata (misalnya "jual
     sepuluh cilok lima puluh ribu") lalu mengirimnya, untuk demo.

   Scan nota pakai kamera:
   - Tombol kamera membuka popup dengan tips memotret (tempat terang, nota
     rata, HP tegak lurus) dan pilihan "Ambil foto" (input file dengan
     capture="environment"), "Pilih dari galeri", serta "Belum ada nota? Coba
     pakai contoh nota".
   - Setelah memilih foto, tampilkan dulu pratinjau dengan tombol "Ganti foto"
     dan "Baca nota ini".
   - Foto muncul di chat sebagai pesan pengguna, lalu muncul bilah progres
     ("Menyiapkan pembaca nota…" kemudian "Membaca tulisan di nota…").
   - Sebelum dibaca, gambar diperbesar sampai lebar sekitar 1600 px, dijadikan
     abu-abu, dan kontrasnya dinaikkan. Gunakan Tesseract PSM 4.
   - Aturan membaca teks nota:
     * Harga diambil dari angka di ujung baris (65.000, 65.000,00, 65000), dan
       salah baca umum diperbaiki (O menjadi 0, l/I menjadi 1).
     * Baris TOTAL/JUMLAH dipakai sebagai total nota. Baris TUNAI, KEMBALI,
       PPN, kasir, telepon, dan "terima kasih" dilewati.
     * Label dan angka yang terbaca di kolom terpisah dipasangkan berurutan.
     * Diskon dikurangkan dari barang tepat di atasnya.
     * Format struk minimarket (nama di satu baris, "2 x 36.500   73.000" di
       baris bawahnya) digabungkan.
     * Baris teks pertama menjadi nama toko. Tanggal di nota (11/10/2026 atau
       12 Okt 2026) dipakai jika masuk akal.
     * Jika jumlah barang tidak sama dengan total dan satu angka bisa
       dibetulkan dari total dengan digit yang mirip (7.000 terbaca 71.000),
       betulkan dan tandai "Terbaca Rp71.000, disesuaikan dengan total nota".
   - Hasil berupa satu kartu: nama toko, tanggal, daftar barang (centang
     ikut/tidak, kategori, info stok, nominal), tombol "Tambah barang yang
     terlewat", total terpilih, tanda hijau "Cocok dengan total di nota" atau
     peringatan kuning jika berbeda, lalu tombol Batal dan "Simpan N catatan".
     Ketuk satu barang untuk mengubahnya lewat form.
   - Jika gagal: beri tips memotret ulang dengan tombol "Foto ulang" dan "Isi
     form manual". Jika pustaka OCR gagal dimuat, beri tahu bahwa pertama kali
     butuh internet.
   - Sediakan 3 nota contoh (toko bahan kue, kios pasar, warung sembako) yang
     digambar sebagai SVG mirip struk (termasuk baris TOTAL, TUNAI, KEMBALI),
     lalu dibaca dengan OCR yang sama.

7. FORM TRANSAKSI (popup dari bawah layar)
   Jenis (dua tombol besar: + Uang masuk / − Uang keluar), barang, nominal
   (berawalan "Rp", otomatis berformat titik ribuan), kategori (pilihan chip
   sesuai jenis), tanggal (chip Hari ini/Kemarin plus pemilih tanggal).
   Untuk uang keluar baru, ada pilihan "Tambah ke stok bahan" (pilih bahan
   dan jumlah). Form ini dipakai untuk input manual, untuk mengubah hasil
   bacaan chat/scan, dan untuk mengubah transaksi lama (dengan tombol Hapus
   dan konfirmasi). Tampilkan pesan error di bawah kolom yang kosong.

8. RIWAYAT
   Kolom pencarian, filter tanggal berupa chip (Semua, Hari ini, 7 hari, Bulan
   ini, Pilih tanggal), filter kategori, ringkasan jumlah transaksi dengan
   total + dan −, lalu daftar yang dikelompokkan per hari dengan judul tanggal
   yang menempel saat menggulir beserta untung hari itu. Ketuk transaksi untuk
   mengubah atau menghapus. Tombol + untuk catat manual. Tampilan kosong untuk
   "belum ada catatan" dan "tidak ada yang cocok dengan filter".

9. BON
   Kartu total belum dibayar, daftar pelanggan yang belum lunas (inisial,
   nama, jumlah catatan, kapan terakhir, total), lalu bagian "Sudah lunas".
   Tombol "Tambah bon" menempel di bawah. Form tambah bon berisi nama
   pelanggan (dengan chip nama yang sudah ada), untuk apa, jumlah, tanggal.
   Tampilan kosong jika belum ada bon. Warna bon kuning/netral, bukan
   hijau/merah, karena utang pelanggan bukan uang keluar.

10. DETAIL BON
    Total belum dibayar, rincian utang per tanggal, riwayat yang sudah dibayar
    (dicoret), tombol "Tambah utang" dan "Tandai lunas". Saat tandai lunas,
    muncul konfirmasi dengan centang "Catat juga sebagai uang masuk hari ini"
    (aktif secara bawaan) yang membuat transaksi "Pelunasan bon …".

11. STOK BAHAN (dibuka dari kartu di Beranda, bukan dari menu bawah)
    - Kartu peringatan "N bahan perlu dibeli" atau "Semua stok masih aman".
    - Daftar bahan diurutkan Habis, Hampir habis, lalu Aman. Setiap bahan
      menampilkan nama, sisa dan satuan, batas peringatan, label status, dan
      garis indikator. Status: Habis jika 0, Hampir habis jika sisa ≤ batas,
      selain itu Aman.
    - Ketuk bahan untuk membuka detail: sisa, tombol Pakai dan Tambah stok,
      riwayat perubahan stok, dan "Ubah info bahan".
    - Popup ubah stok: pilihan Tambah/Pakai, jumlah dengan chip cepat (0,5/1/2/5
      untuk kg dan liter, 1/2/5/10 untuk satuan lain), pratinjau "Stok 7 → jadi
      9 kg" beserta status barunya, dan catatan opsional.
    - Popup tambah atau ubah bahan: nama, satuan (chip kg, liter, tabung, pak,
      bungkus, buah, atau isi sendiri), stok awal, dan "Ingatkan kalau sisa".
      Ada tombol Hapus dengan konfirmasi.
    - Stok bertambah otomatis saat belanja yang cocok disimpan. Bahan per
      kg/liter memakai ukuran (gram/ons diubah ke kg), sedangkan bahan per
      tabung/pak memakai jumlah barang ("gas elpiji 3 kg" = +1 tabung, "2 x
      minyak 2L" = +4 liter). Jika ukurannya tidak jelas, biarkan pengguna yang
      mengisi.
    - Muncul notifikasi kuning saat stok baru saja menjadi hampir habis atau habis.
    - Mengubah atau menghapus transaksi lama tidak mengubah stok.

12. PENGATURAN
    Profil usaha (nama usaha, jenis, pemilik, kontak) dengan mode ubah, daftar
    kategori uang masuk dan uang keluar (tambah dan hapus, minimal satu),
    bagian "Data contoh" dengan tombol Kosongkan (untuk melihat tampilan
    kosong) dan Isi ulang, serta tombol "Keluar dari akun" dengan konfirmasi.

====================================================================
NAVIGASI
====================================================================
Menu bawah dengan empat tombol: Beranda, Catat, Riwayat, Bon. Tombol Catat
dibuat paling menonjol: lingkaran besar berwarna utama yang sedikit naik di
atas menu. Pengaturan dibuka dari ikon profil, Stok dari kartu di Beranda.
Setiap pindah halaman, gulir ke atas. Riwayat percakapan chat tetap tersimpan
saat berpindah menu.

====================================================================
ATURAN DESAIN
====================================================================
- Rancang untuk layar HP lebih dulu (lebar 360 sampai 414 px). Di layar lebar,
  tampilkan konten di tengah dengan lebar maksimal 420 px seperti HP.
- Semua teks dalam Bahasa Indonesia sehari-hari. Jangan pakai istilah debit,
  kredit, atau jurnal. Pakai "uang masuk", "uang keluar", dan "untung".
- Nominal selalu berformat Rupiah, contoh: Rp45.000.
- Uang masuk berwarna hijau dan uang keluar berwarna merah, selalu disertai
  tanda + atau − (dan ikon panah) supaya tidak bergantung pada warna saja.
- Satu warna utama biru (blue-600) yang berbeda dari hijau dan merah. Kuning
  untuk bon dan peringatan stok.
- Tombol besar dan mudah ditekan jempol, tinggi minimal 44 px. Ukuran teks
  input 16 px supaya HP tidak memperbesar layar.
- Tampilan bersih dan sederhana, tanpa dekorasi berlebihan. Animasi halus
  untuk popup dan pesan baru.
- Popup muncul dari bawah layar (bottom sheet). Konfirmasi hapus memakai
  dialog di tengah.
- Notifikasi singkat di atas layar setelah menyimpan, mengubah, atau menghapus.
- Sediakan tampilan kosong untuk Riwayat, Bon, dan Stok.
- Aksesibilitas: label aria pada tombol ikon, dan tombol pilihan memakai
  role radio/aria-pressed.

====================================================================
DATA CONTOH
====================================================================
Usaha bernama "Jualans", jenis "Cilok goreng", pemilik "Rina". Buat data
relatif terhadap tanggal hari ini:
- Sekitar 20 transaksi dalam 7 hari terakhir. Uang masuk: cilok goreng
  (Rp5.000/porsi, 18–45 porsi per hari), es teh manis (Rp3.000/gelas),
  pesanan arisan Bu RT 50 porsi Rp250.000. Uang keluar: tepung tapioka 5 kg
  Rp65.000, daging ayam giling 1 kg Rp48.000, minyak goreng 2 liter Rp36.000,
  gas elpiji 3 kg Rp22.000, plastik & tusuk sate Rp25.000, bumbu kacang &
  cabai Rp30.000. Belanja di pagi hari, penjualan sore hari.
- 3 pelanggan yang punya bon: Bu Sri (tetangga depan, 3 catatan, Rp41.000),
  Pak Darto (ojek pangkalan, 2 catatan, Rp25.000), Mas Rizki (anak kos,
  1 catatan, Rp20.000).
- 7 bahan stok beserta riwayat singkatnya: tepung tapioka 7 kg (batas 5),
  daging ayam giling 0,5 kg (batas 1), minyak goreng 3 liter (batas 2), gas
  elpiji 3 kg 1 tabung (batas 1), bumbu kacang 1 kg (batas 0,5), plastik
  kemasan 3 pak (batas 1), tusuk sate 0 pak (batas 1), sehingga ada contoh
  status Aman, Hampir habis, dan Habis.
- Kategori uang masuk: Penjualan, Pesanan, Pelunasan bon, Lain-lain.
  Kategori uang keluar: Bahan baku, Operasional, Sewa, Gaji, Lain-lain.

====================================================================
HASIL YANG SAYA HARAPKAN
====================================================================
Semua halaman di atas bisa dibuka dan saling terhubung. Kerjakan Catat dan
Beranda paling teliti karena keduanya paling sering dipakai. Sebelum selesai,
uji minimal hal berikut di lebar 375 px:
- "jual 3 nasi ayam 45rb" menjadi uang masuk +Rp45.000, barang Nasi ayam (3),
  kategori Penjualan.
- "beli tepung tapioka 5kg 65rb" menjadi uang keluar −Rp65.000 dengan baris
  "Masuk stok: Tepung tapioka +5 kg". Setelah disimpan, stok bertambah.
- "kemarin jual es teh 1,5jt" bertanggal kemarin dengan nominal +Rp1.500.000.
- "tadi 15.000" memunculkan pertanyaan uang masuk atau uang keluar.
- "halo apa kabar" meminta mengulang dan menawarkan form manual.
- "pakai tepung 2kg" mengurangi stok tanpa menambah uang keluar.
- Simulasi suara "beli tepung tapioka lima kilo enam puluh lima ribu" terbaca
  sebagai −Rp65.000 dan +5 kg stok.
- Ketiga nota contoh terbaca dengan total yang cocok.
- Transaksi baru langsung muncul di Beranda dan Riwayat.
- Tombol Kosongkan di Pengaturan menampilkan tampilan kosong Riwayat, Bon,
  dan Stok.
- Tidak ada error di console.
