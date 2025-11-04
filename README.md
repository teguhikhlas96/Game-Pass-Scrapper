# Aplikasi Scraping Website dengan Selenium

Aplikasi scraping website yang lengkap menggunakan Selenium WebDriver dengan Python. Aplikasi ini dapat mengambil berbagai informasi dari website tertentu seperti title, meta description, heading, paragraf, link, dan gambar.

## Fitur

- ✅ Scraping Title halaman
- ✅ Scraping Meta Description
- ✅ Scraping Semua Heading (h1-h6)
- ✅ Scraping Semua Paragraf
- ✅ Scraping Semua Link (dengan text dan URL)
- ✅ Scraping Semua Gambar (dengan src dan alt)
- ✅ Scraping Semua Text dari body
- ✅ Penyimpanan hasil ke file JSON
- ✅ Mode Headless (tanpa membuka browser)
- ✅ Auto-scroll untuk memuat konten lazy-loaded

## Instalasi

1. Pastikan Python 3.7+ sudah terinstall
2. Install dependencies:
```bash
pip install -r requirements.txt
```

Atau jika menggunakan virtual environment:
```bash
# Buat virtual environment
python3 -m venv .venv

# Aktifkan virtual environment
source .venv/bin/activate  # Untuk macOS/Linux
# atau
.venv\Scripts\activate  # Untuk Windows

# Install dependencies
pip install -r requirements.txt
```

## Cara Menggunakan

### 1. Edit Konfigurasi di `app.py`

Buka file `app.py` dan edit bagian konfigurasi di bawah:

```python
# Ganti URL di bawah ini dengan website yang ingin di-scrape
TARGET_URL = "https://example.com"

# Atau gunakan salah satu contoh di bawah (uncomment salah satu):
# TARGET_URL = "https://www.python.org"
# TARGET_URL = "https://github.com"
# TARGET_URL = "https://news.ycombinator.com"

# Opsi:
HEADLESS = False  # True untuk menjalankan tanpa membuka browser
SAVE_TO_FILE = True  # True untuk menyimpan hasil ke file JSON
```

### 2. Jalankan Aplikasi

```bash
# Aktifkan virtual environment (jika menggunakan)
source .venv/bin/activate

# Jalankan aplikasi
python app.py
```

### 3. Lihat Hasil

Aplikasi akan menampilkan informasi yang di-scrape di terminal dan menyimpan hasil ke file JSON dengan format:
- `hasil_scraping_[domain].json`

## Contoh Penggunaan

### Contoh 1: Scraping Website Sederhana
```python
hasil = scrape_website(
    url="https://example.com",
    headless=False,
    save_to_file=True
)
```

### Contoh 2: Scraping dalam Mode Headless
```python
hasil = scrape_website(
    url="https://www.python.org",
    headless=True,  # Browser tidak akan terbuka
    save_to_file=True
)
```

### Contoh 3: Scraping Tanpa Menyimpan ke File
```python
hasil = scrape_website(
    url="https://github.com",
    headless=False,
    save_to_file=False  # Hanya tampilkan di terminal
)
```

## Struktur Hasil Scraping

Hasil scraping disimpan dalam format JSON dengan struktur berikut:

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "meta_description": "Description website",
  "headings": {
    "h1": ["Heading 1"],
    "h2": ["Heading 2", "Heading 2 lainnya"],
    ...
  },
  "paragraphs": ["Paragraf 1", "Paragraf 2", ...],
  "links": [
    {"url": "https://example.com/link", "text": "Text Link"},
    ...
  ],
  "images": [
    {"src": "https://example.com/image.jpg", "alt": "Alt text"},
    ...
  ],
  "all_text": "Semua text dari body..."
}
```

## Catatan Penting

1. **Chrome Browser**: Pastikan Google Chrome sudah terinstall di sistem Anda
2. **ChromeDriver**: Akan di-download otomatis oleh webdriver-manager
3. **Respect Robots.txt**: Selalu perhatikan robots.txt dan Terms of Service website yang Anda scrape
4. **Rate Limiting**: Jangan melakukan scraping terlalu sering ke website yang sama
5. **Legal**: Pastikan Anda memiliki izin untuk scraping website target

## Troubleshooting

### Error: ChromeDriver tidak ditemukan
- Pastikan Google Chrome terinstall
- webdriver-manager akan mengunduh ChromeDriver otomatis

### Error: Timeout
- Periksa koneksi internet
- Beberapa website mungkin memerlukan waktu loading lebih lama
- Coba tambah timeout di `WebDriverWait(driver, 15)`

### Error: Element tidak ditemukan
- Website mungkin menggunakan JavaScript untuk render konten
- Aplikasi sudah menggunakan wait dan scroll untuk mengatasi ini
- Jika masih error, website mungkin menggunakan iframe atau konten yang terlindungi

## Lisensi

Project ini dibuat untuk keperluan edukasi dan contoh penggunaan.
