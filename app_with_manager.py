"""
Versi aplikasi dengan webdriver-manager (lebih mudah, tidak perlu download ChromeDriver manual)
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

def contoh_scraping_sederhana():
    """
    Contoh aplikasi Selenium sederhana untuk scraping website
    Menggunakan webdriver-manager untuk otomatis mengelola ChromeDriver
    """
    # Konfigurasi Chrome Options
    chrome_options = Options()
    # Uncomment baris di bawah jika ingin headless (tanpa membuka browser)
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Inisialisasi driver dengan webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Buka website contoh (menggunakan example.com)
        print("Membuka website...")
        driver.get("https://example.com")
        
        # Tunggu sampai halaman dimuat
        wait = WebDriverWait(driver, 10)
        
        # Contoh 1: Ambil title halaman
        title = driver.title
        print(f"Title halaman: {title}")
        
        # Contoh 2: Ambil teks dari elemen
        try:
            heading = wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            print(f"Judul halaman: {heading.text}")
        except Exception as e:
            print(f"Error mengambil judul: {e}")
        
        # Contoh 3: Ambil semua paragraf
        try:
            paragraphs = driver.find_elements(By.TAG_NAME, "p")
            print(f"\nJumlah paragraf: {len(paragraphs)}")
            for i, p in enumerate(paragraphs, 1):
                print(f"Paragraf {i}: {p.text[:100]}...")  # Batasi 100 karakter
        except Exception as e:
            print(f"Error mengambil paragraf: {e}")
        
        # Tunggu sebentar untuk melihat hasil
        time.sleep(2)
        
        # Contoh 4: Ambil URL saat ini
        current_url = driver.current_url
        print(f"\nURL saat ini: {current_url}")
        
    except Exception as e:
        print(f"Error terjadi: {e}")
    
    finally:
        # Tutup browser
        print("\nMenutup browser...")
        driver.quit()

if __name__ == "__main__":
    print("=== Contoh Aplikasi Selenium dengan WebDriver Manager ===\n")
    
    print("Contoh: Scraping sederhana dari example.com")
    print("-" * 50)
    contoh_scraping_sederhana()

