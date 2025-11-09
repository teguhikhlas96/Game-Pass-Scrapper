# Xbox Game Pass Games Scraper

Script Python menggunakan Selenium untuk scraping semua daftar game dari Xbox Game Pass dengan fitur filtering berdasarkan tahun rilis.

## Fitur Utama

- ✅ **Scraping Lengkap**: Mengambil semua game dari Xbox Game Pass dengan pagination otomatis
- ✅ **Filter Tahun Rilis**: Opsi untuk hanya mengambil game yang dirilis di tahun tertentu (default: 2025)
- ✅ **GiantBomb API Integration**: Menggunakan GiantBomb API untuk mendapatkan informasi release date
- ✅ **Rate Limiting**: Sistem rate limiting otomatis (200 requests/hour) dengan countdown timer
- ✅ **HTTP 420 Handling**: Auto-retry dengan countdown 1 jam jika mendapat HTTP 420 response
- ✅ **Caching**: Cache release dates untuk menghindari API calls duplikat
- ✅ **Auto-Scroll**: Auto-scroll untuk memuat konten dinamis
- ✅ **Multiple Output Formats**: Menyimpan hasil ke JSON dan CSV

## Instalasi

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Pastikan Chrome browser sudah terinstall (ChromeDriver akan diinstall otomatis via webdriver-manager)

## Penggunaan

### Penggunaan Dasar

Jalankan script dengan konfigurasi default:
```bash
python gamepass_scraper.py
```

### Konfigurasi

Edit bagian `main()` di `gamepass_scraper.py` untuk mengubah konfigurasi:

```python
# Configuration
FILTER_2025_ONLY = True  # True = hanya game 2025, False = semua game

scraper = GamePassScraper(
    headless=False,      # True = run tanpa browser window
    debug=True,          # True = tampilkan log detail
    filter_2025_only=FILTER_2025_ONLY
)
```

### Opsi Konfigurasi

- **`headless`**: 
  - `True`: Jalankan browser di background (tanpa window)
  - `False`: Tampilkan browser window (default)

- **`debug`**: 
  - `True`: Tampilkan log detail untuk troubleshooting
  - `False`: Log minimal

- **`filter_2025_only`**: 
  - `True`: Hanya ambil game yang dirilis di tahun 2025 (menggunakan GiantBomb API)
  - `False`: Ambil semua game tanpa filter tahun

## Fitur Detail

### 1. Pagination Otomatis
Script secara otomatis menelusuri semua halaman dengan:
- Mencari tombol "Next" di pagination
- Auto-scroll untuk memuat konten lazy-loading
- Maksimal 100 percobaan untuk memastikan semua halaman ditelusuri

### 2. Filter Release Date (2025)
Jika `filter_2025_only=True`:
- Script akan memanggil GiantBomb API untuk setiap game
- Hanya game dengan release date tahun 2025 yang akan disimpan
- Release dates di-cache untuk menghindari API calls duplikat

### 3. Rate Limiting
- **Limit**: 200 requests per jam (sesuai limit GiantBomb API)
- **Countdown Timer**: Menampilkan countdown saat menunggu rate limit
- **Auto-resume**: Script otomatis melanjutkan setelah rate limit reset

### 4. HTTP 420 Handling
Jika mendapat HTTP 420 (Enhance Your Calm):
- Script akan menunggu 1 jam dengan countdown timer
- Auto-retry hingga 3 kali jika masih mendapat 420
- Reset rate limiter setelah menunggu
- Skip game jika masih gagal setelah 3 retry

### 5. Caching
- Release dates di-cache di file `release_date_cache.json`
- Menghindari API calls duplikat untuk game yang sama
- Cache persist antar session

## Output

Script akan menghasilkan 3 file:

1. **`gamepass_games.json`** - Data dalam format JSON
   ```json
   [
     {
       "name": "Game Name",
       "url": "https://www.xbox.com/games/store/...",
       "release_date": "2025-01-15",
       "scraped_at": "2025-11-09 10:30:00"
     }
   ]
   ```

2. **`gamepass_games.csv`** - Data dalam format CSV dengan kolom:
   - `name`: Nama game
   - `url`: URL game di Xbox Store
   - `release_date`: Tanggal rilis (jika filter aktif)
   - `scraped_at`: Waktu scraping

3. **`release_date_cache.json`** - Cache release dates (jika filter aktif)

## Struktur File

```
.
├── gamepass_scraper.py      # Main script
├── requirements.txt          # Python dependencies
├── README.md                 # Dokumentasi ini
├── gamepass_games.json       # Output JSON (generated)
├── gamepass_games.csv        # Output CSV (generated)
└── release_date_cache.json   # Cache release dates (generated)
```

## Catatan Penting

### Rate Limiting
- GiantBomb API memiliki limit 200 requests per jam
- Script otomatis mengatur rate limiting dengan delay 2 detik antar request
- Jika limit tercapai, script akan menunggu dengan countdown timer

### HTTP 420 Response
- Jika mendapat HTTP 420, script akan:
  1. Menampilkan countdown 1 jam
  2. Reset rate limiter
  3. Retry request (maksimal 3 kali)
  4. Skip game jika masih gagal

### Waktu Eksekusi
- Scraping semua game: ~5-15 menit (tergantung jumlah game)
- Dengan filter 2025: ~30-60 menit (karena API calls untuk setiap game)
- Jika rate limit tercapai: +1 jam per 200 requests

### Troubleshooting

**Script tidak mengambil semua game:**
- Pastikan koneksi internet stabil
- Cek apakah ada error di console
- Coba jalankan dengan `debug=True` untuk melihat log detail

**HTTP 420 terus muncul:**
- Tunggu beberapa jam sebelum menjalankan lagi
- Pastikan tidak ada instance script lain yang berjalan
- Cek apakah API key valid

**Browser tidak terbuka:**
- Pastikan Chrome browser terinstall
- Cek apakah ChromeDriver terinstall dengan benar
- Coba set `headless=False` untuk melihat browser

## Dependencies

- `selenium` - Web scraping
- `webdriver-manager` - Auto-manage ChromeDriver
- `requests` - HTTP requests untuk GiantBomb API
- `json` - JSON handling
- `csv` - CSV handling

## Lisensi

Script ini dibuat untuk keperluan personal/educational. Pastikan untuk menghormati Terms of Service dari Xbox.com dan GiantBomb API.

## Kontribusi

Jika menemukan bug atau ingin menambahkan fitur, silakan buat issue atau pull request.
