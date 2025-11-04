from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from urllib.parse import urljoin, urlparse

def init_driver(headless=False):
    """
    Inisialisasi Chrome driver
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_website(url, headless=False, save_to_file=False):
    """
    Fungsi utama untuk scraping informasi dari website tertentu
    
    Args:
        url: URL website yang akan di-scrape
        headless: True untuk menjalankan browser tanpa UI
        save_to_file: True untuk menyimpan hasil ke file JSON
    """
    driver = None
    hasil_scraping = {
        "url": url,
        "title": "",
        "meta_description": "",
        "headings": {},
        "paragraphs": [],
        "links": [],
        "images": [],
        "all_text": ""
    }
    
    try:
        print(f"Membuka website: {url}")
        driver = init_driver(headless=headless)
        driver.get(url)
        
        # Tunggu sampai halaman dimuat
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Scroll untuk memuat konten lazy-loaded
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        print("\n" + "="*60)
        print("MEMULAI SCRAPING...")
        print("="*60)
        
        # 1. Ambil Title
        try:
            hasil_scraping["title"] = driver.title
            print(f"\n✓ Title: {hasil_scraping['title']}")
        except Exception as e:
            print(f"✗ Error mengambil title: {e}")
        
        # 2. Ambil Meta Description
        try:
            meta_desc = driver.find_element(By.XPATH, "//meta[@name='description']")
            hasil_scraping["meta_description"] = meta_desc.get_attribute("content")
            print(f"\n✓ Meta Description: {hasil_scraping['meta_description'][:100]}...")
        except:
            try:
                meta_desc = driver.find_element(By.XPATH, "//meta[@property='og:description']")
                hasil_scraping["meta_description"] = meta_desc.get_attribute("content")
                print(f"\n✓ Meta Description (OG): {hasil_scraping['meta_description'][:100]}...")
            except:
                print("\n✗ Meta Description tidak ditemukan")
        
        # 3. Ambil Semua Heading (h1-h6)
        print("\n" + "-"*60)
        print("HEADING:")
        print("-"*60)
        for level in range(1, 7):
            try:
                headings = driver.find_elements(By.TAG_NAME, f"h{level}")
                if headings:
                    hasil_scraping["headings"][f"h{level}"] = [h.text.strip() for h in headings if h.text.strip()]
                    print(f"\nh{level} ({len(headings)}):")
                    for i, h in enumerate(headings[:5], 1):  # Tampilkan max 5
                        text = h.text.strip()
                        if text:
                            print(f"  {i}. {text[:80]}...")
                    if len(headings) > 5:
                        print(f"  ... dan {len(headings) - 5} heading lainnya")
            except Exception as e:
                print(f"✗ Error mengambil h{level}: {e}")
        
        # 4. Ambil Semua Paragraf
        print("\n" + "-"*60)
        print("PARAGRAF:")
        print("-"*60)
        try:
            paragraphs = driver.find_elements(By.TAG_NAME, "p")
            hasil_scraping["paragraphs"] = [p.text.strip() for p in paragraphs if p.text.strip()]
            print(f"Jumlah paragraf: {len(hasil_scraping['paragraphs'])}")
            for i, p in enumerate(hasil_scraping["paragraphs"][:3], 1):  # Tampilkan 3 pertama
                print(f"\n{i}. {p[:150]}...")
            if len(hasil_scraping["paragraphs"]) > 3:
                print(f"\n... dan {len(hasil_scraping['paragraphs']) - 3} paragraf lainnya")
        except Exception as e:
            print(f"✗ Error mengambil paragraf: {e}")
        
        # 5. Ambil Semua Links
        print("\n" + "-"*60)
        print("LINK:")
        print("-"*60)
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            unique_links = set()
            for link in links:
                href = link.get_attribute("href")
                text = link.text.strip()
                if href:
                    # Konversi relative URL ke absolute
                    full_url = urljoin(url, href)
                    unique_links.add((full_url, text))
            
            hasil_scraping["links"] = [{"url": link[0], "text": link[1]} for link in unique_links]
            print(f"Jumlah link unik: {len(hasil_scraping['links'])}")
            for i, link in enumerate(list(unique_links)[:5], 1):  # Tampilkan 5 pertama
                print(f"\n{i}. {link[1][:50] if link[1] else '(no text)'}")
                print(f"   {link[0][:80]}...")
            if len(unique_links) > 5:
                print(f"\n... dan {len(unique_links) - 5} link lainnya")
        except Exception as e:
            print(f"✗ Error mengambil link: {e}")
        
        # 6. Ambil Semua Gambar
        print("\n" + "-"*60)
        print("GAMBAR:")
        print("-"*60)
        try:
            images = driver.find_elements(By.TAG_NAME, "img")
            for img in images:
                src = img.get_attribute("src")
                alt = img.get_attribute("alt") or ""
                if src:
                    full_src = urljoin(url, src)
                    hasil_scraping["images"].append({"src": full_src, "alt": alt})
            print(f"Jumlah gambar: {len(hasil_scraping['images'])}")
            for i, img in enumerate(hasil_scraping["images"][:5], 1):  # Tampilkan 5 pertama
                print(f"\n{i}. {img['alt'][:50] if img['alt'] else '(no alt)'}")
                print(f"   {img['src'][:80]}...")
            if len(hasil_scraping["images"]) > 5:
                print(f"\n... dan {len(hasil_scraping['images']) - 5} gambar lainnya")
        except Exception as e:
            print(f"✗ Error mengambil gambar: {e}")
        
        # 7. Ambil Semua Text dari Body
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            hasil_scraping["all_text"] = body.text.strip()
        except:
            pass
        
        # Simpan ke file jika diminta
        if save_to_file:
            domain = urlparse(url).netloc.replace(".", "_")
            filename = f"hasil_scraping_{domain}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(hasil_scraping, f, ensure_ascii=False, indent=2)
            print(f"\n" + "="*60)
            print(f"✓ Hasil disimpan ke: {filename}")
            print("="*60)
        
        print("\n" + "="*60)
        print("SCRAPING SELESAI!")
        print("="*60)
        
        return hasil_scraping
        
    except Exception as e:
        print(f"\n✗ Error terjadi: {e}")
        return None
    
    finally:
        if driver:
            print("\nMenutup browser...")
            driver.quit()

def scrape_single_page_xbox(driver, page_num=1):
    """
    Fungsi helper untuk scraping satu halaman Xbox Game Pass
    
    Args:
        driver: WebDriver instance yang sudah diinisialisasi
        page_num: Nomor halaman (untuk logging)
    
    Returns:
        List game yang ditemukan di halaman ini
    """
    games_list = []
    
    try:
        print(f"\n{'='*60}")
        print(f"MENGSCRAPE HALAMAN {page_num}")
        print(f"{'='*60}")
        
        # Tunggu sampai konten game muncul
        time.sleep(3)
        
        # Scroll ke bagian game (skip header/nav)
        try:
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)
        except:
            pass
        
        # Cari container game dengan berbagai selector yang mungkin
        game_selectors = [
            "a[href*='/games/']",
            "article",
            "[data-module='GameTile']",
            ".game-tile",
            "a[data-testid]",
            "[role='listitem']",
            ".product-tile"
        ]
        
        last_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 30
        
        print("\nMencari elemen game dan melakukan scroll...")
        
        # Scroll perlahan untuk memuat semua game (infinite scroll)
        max_games_found = 0
        consecutive_no_change = 0
        
        while scroll_attempts < max_scroll_attempts:
            # Coba berbagai selector untuk menghitung game
            current_max = 0
            for selector in game_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    current_max = max(current_max, len(elements))
                    if len(elements) > last_count:
                        last_count = len(elements)
                        consecutive_no_change = 0
                except:
                    continue
            
            # Update max games found
            if current_max > max_games_found:
                max_games_found = current_max
                consecutive_no_change = 0
            else:
                consecutive_no_change += 1
            
            # Scroll ke bawah untuk load lebih banyak konten
            scroll_height_before = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Scroll sedikit ke atas lalu ke bawah lagi untuk trigger lazy load
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 500);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            scroll_height_after = driver.execute_script("return document.body.scrollHeight")
            
            # Jika scroll height tidak berubah DAN tidak ada game baru, increment attempts
            if scroll_height_before == scroll_height_after and consecutive_no_change >= 2:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
            
            if scroll_attempts >= 5:
                break
            
            print(f"  Scroll halaman {page_num}... ({scroll_attempts}/{max_scroll_attempts}) - Game: {max_games_found}", end='\r')
        
        print(f"\n✓ Halaman {page_num}: Ditemukan {max_games_found} elemen")
        
        # Cari elemen dengan berbagai selector untuk mendapatkan info game
        game_elements = []
        for selector in game_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > len(game_elements):
                    game_elements = elements
            except:
                continue
        
        if not game_elements:
            print(f"✗ Halaman {page_num}: Tidak ada elemen game ditemukan")
            return games_list
        
        print(f"✓ Halaman {page_num}: Menggunakan {len(game_elements)} elemen untuk scraping")
        
        # Extract informasi dari setiap game
        processed_titles = set()
        max_elements = min(len(game_elements), 1000)
        
        for idx, element in enumerate(game_elements[:max_elements], 1):
            try:
                game_info = {}
                
                # Cari nama game (coba berbagai cara)
                title = None
                title_selectors = [
                    ".text-title",
                    "h2", "h3", "h4",
                    "[data-testid*='title']",
                    ".game-title",
                    "span[class*='title']",
                    "div[class*='title']"
                ]
                
                for title_sel in title_selectors:
                    try:
                        title_elem = element.find_element(By.CSS_SELECTOR, title_sel)
                        title = title_elem.text.strip()
                        if title and len(title) > 0:
                            break
                    except:
                        continue
                
                # Jika tidak ada title di child, coba ambil dari element sendiri
                if not title:
                    title = element.text.strip().split('\n')[0] if element.text.strip() else None
                
                # Skip jika title sudah pernah diproses atau tidak valid
                if not title or title in processed_titles or len(title) < 2:
                    continue
                
                processed_titles.add(title)
                game_info["title"] = title
                
                # Cari link game
                try:
                    link_elem = element.find_element(By.TAG_NAME, "a")
                    game_info["url"] = link_elem.get_attribute("href")
                except:
                    try:
                        parent = element.find_element(By.XPATH, "./ancestor::a[1]")
                        game_info["url"] = parent.get_attribute("href")
                    except:
                        game_info["url"] = None
                
                # Cari gambar
                try:
                    img_elem = element.find_element(By.TAG_NAME, "img")
                    game_info["image_url"] = img_elem.get_attribute("src") or img_elem.get_attribute("data-src")
                    game_info["image_alt"] = img_elem.get_attribute("alt") or ""
                except:
                    game_info["image_url"] = None
                    game_info["image_alt"] = ""
                
                # Ambil text tambahan jika ada
                try:
                    game_info["description"] = element.text.strip()[:200]
                except:
                    game_info["description"] = ""
                
                if game_info["title"]:
                    game_info["page_found"] = page_num
                    games_list.append(game_info)
                    
            except Exception as e:
                continue
        
        # Hapus duplikat berdasarkan title di halaman ini
        unique_games = []
        seen_titles = set()
        for game in games_list:
            if game.get("title") and game["title"] not in seen_titles:
                seen_titles.add(game["title"])
                unique_games.append(game)
        
        games_list = unique_games
        print(f"✓ Halaman {page_num}: Berhasil di-scrape {len(games_list)} game")
        
        return games_list
        
    except Exception as e:
        print(f"\n✗ Error pada halaman {page_num}: {e}")
        return games_list

def set_items_per_page(driver, items_count=200):
    """
    Mencari dan mengubah dropdown/select untuk memilih jumlah item per halaman
    
    Args:
        driver: WebDriver instance
        items_count: Jumlah item per halaman yang diinginkan (default: 200)
    
    Returns:
        True jika berhasil, False jika tidak
    """
    try:
        print(f"\n{'='*60}")
        print(f"MENCARI OPSI '{items_count} PER HALAMAN'")
        print(f"{'='*60}")
        
        # Tunggu sebentar untuk memastikan halaman sudah dimuat
        time.sleep(3)
        
        # Cari berbagai selector untuk dropdown items per page
        selectors_to_try = [
            # Select element
            "select[name*='per']",
            "select[name*='page']",
            "select[name*='limit']",
            "select[name*='size']",
            "select[id*='per']",
            "select[id*='page']",
            "select[id*='limit']",
            "select[id*='size']",
            "select[class*='per']",
            "select[class*='page']",
            "select[class*='limit']",
            "select",
            
            # Button untuk dropdown
            "button[aria-label*='per']",
            "button[aria-label*='page']",
            "button[aria-label*='Show']",
            "button[aria-label*='Display']",
            "button[aria-label*='Items']",
            
            # Div atau span yang bisa diklik
            "[role='combobox']",
            "[role='button'][aria-label*='per']",
            "[role='button'][aria-label*='page']",
        ]
        
        # XPath selectors
        xpath_selectors = [
            "//select[contains(@name, 'per') or contains(@name, 'page') or contains(@name, 'limit')]",
            "//select[contains(@id, 'per') or contains(@id, 'page') or contains(@id, 'limit')]",
            "//select",
            "//button[contains(text(), 'per') or contains(text(), 'Show')]",
            "//div[contains(text(), 'per')]",
        ]
        
        # Coba cari select element
        for selector in selectors_to_try:
            try:
                select_element = driver.find_element(By.CSS_SELECTOR, selector)
                if select_element.is_displayed():
                    print(f"  ✓ Ditemukan select element: {selector}")
                    
                    # Cek apakah ada option untuk items_count
                    try:
                        options = select_element.find_elements(By.TAG_NAME, "option")
                        for option in options:
                            option_text = option.text.strip()
                            option_value = option.get_attribute("value")
                            
                            # Cek apakah ada option dengan nilai 200 atau text yang sesuai
                            if str(items_count) in option_text or str(items_count) in (option_value or ""):
                                print(f"  ✓ Ditemukan option untuk {items_count} item")
                                select_element.click()
                                time.sleep(1)
                                option.click()
                                time.sleep(2)
                                print(f"  ✓ Berhasil mengubah ke {items_count} item per halaman")
                                return True
                    except:
                        pass
                    
                    # Jika tidak ada option spesifik, coba set value langsung
                    try:
                        select_element.send_keys(str(items_count))
                        time.sleep(2)
                        print(f"  ✓ Berhasil mengatur ke {items_count} item per halaman")
                        return True
                    except:
                        pass
            except:
                continue
        
        # Coba dengan XPath
        for xpath in xpath_selectors:
            try:
                select_element = driver.find_element(By.XPATH, xpath)
                if select_element.is_displayed():
                    print(f"  ✓ Ditemukan element dengan XPath: {xpath}")
                    try:
                        # Coba sebagai select element
                        options = select_element.find_elements(By.TAG_NAME, "option")
                        for option in options:
                            if str(items_count) in option.text or str(items_count) in (option.get_attribute("value") or ""):
                                select_element.click()
                                time.sleep(1)
                                option.click()
                                time.sleep(2)
                                print(f"  ✓ Berhasil mengubah ke {items_count} item per halaman")
                                return True
                    except:
                        pass
            except:
                continue
        
        # Cari text yang mengandung angka untuk items per page
        try:
            # Cari text yang mengandung angka seperti "12", "24", "48", "96", "200"
            xpath_text = f"//*[contains(text(), '{items_count}') or contains(text(), 'Show {items_count}') or contains(text(), '{items_count} per')]"
            try:
                element = driver.find_element(By.XPATH, xpath_text)
                if element.is_displayed():
                    print(f"  ✓ Ditemukan element dengan text '{items_count}': {element.text}")
                    try:
                        # Coba klik element tersebut
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(2)
                        print(f"  ✓ Berhasil klik opsi {items_count}")
                        return True
                    except:
                        # Coba klik parent
                        try:
                            parent = element.find_element(By.XPATH, "./parent::*")
                            driver.execute_script("arguments[0].click();", parent)
                            time.sleep(2)
                            print(f"  ✓ Berhasil klik parent opsi {items_count}")
                            return True
                        except:
                            pass
            except:
                pass
        except:
            pass
        
        # Coba cari button atau dropdown custom
        try:
            # Cari semua button yang mungkin dropdown
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                button_text = button.text.strip()
                if any(keyword in button_text.lower() for keyword in ['per', 'show', 'display', 'items', 'results']):
                    print(f"  ✓ Ditemukan button dropdown: {button_text}")
                    try:
                        # Scroll ke button
                        driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(2)
                        
                        # Setelah klik, cari option yang sesuai
                        option_selectors = [
                            f"//button[contains(text(), '{items_count}')]",
                            f"//a[contains(text(), '{items_count}')]",
                            f"//li[contains(text(), '{items_count}')]",
                            f"//div[contains(text(), '{items_count}')]",
                            f"//span[contains(text(), '{items_count}')]",
                            f"[data-value='{items_count}']",
                            f"[data-value='{str(items_count)}']",
                            f"[aria-label*='{items_count}']",
                            f"//*[@data-testid and contains(text(), '{items_count}')]"
                        ]
                        
                        for opt_sel in option_selectors:
                            try:
                                if "//" in opt_sel:
                                    option = driver.find_element(By.XPATH, opt_sel)
                                else:
                                    option = driver.find_element(By.CSS_SELECTOR, opt_sel)
                                
                                if option.is_displayed():
                                    driver.execute_script("arguments[0].scrollIntoView(true);", option)
                                    time.sleep(1)
                                    driver.execute_script("arguments[0].click();", option)
                                    time.sleep(3)  # Tunggu lebih lama untuk halaman reload
                                    print(f"  ✓ Berhasil memilih {items_count} item per halaman")
                                    return True
                            except:
                                continue
                                
                        # Coba cari dengan text yang lebih fleksibel
                        all_clickable = driver.find_elements(By.XPATH, "//*[@role='option' or @role='menuitem' or contains(@class, 'option')]")
                        for clickable in all_clickable:
                            text = clickable.text.strip()
                            if str(items_count) in text:
                                print(f"  ✓ Ditemukan option: {text}")
                                driver.execute_script("arguments[0].click();", clickable)
                                time.sleep(3)
                                print(f"  ✓ Berhasil memilih {items_count} item per halaman")
                                return True
                    except Exception as e:
                        print(f"    Error saat klik button: {e}")
                        pass
        except:
            pass
        
        # Coba cari semua div atau span yang mengandung angka
        try:
            xpath_all = f"//div[contains(text(), '{items_count}')] | //span[contains(text(), '{items_count}')] | //a[contains(text(), '{items_count}')]"
            elements = driver.find_elements(By.XPATH, xpath_all)
            for elem in elements:
                elem_text = elem.text.strip()
                # Cek apakah text mengandung keyword terkait pagination
                if any(keyword in elem_text.lower() for keyword in ['per', 'show', 'display', 'items', 'results', 'page']) or str(items_count) in elem_text:
                    print(f"  ✓ Ditemukan element dengan text: {elem_text}")
                    try:
                        parent = elem.find_element(By.XPATH, "./ancestor::button[1] | ./ancestor::a[1] | ./ancestor::div[@role='button'][1]")
                        if parent:
                            driver.execute_script("arguments[0].scrollIntoView(true);", parent)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", parent)
                            time.sleep(3)
                            print(f"  ✓ Berhasil klik element terkait {items_count}")
                            return True
                    except:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", elem)
                            time.sleep(3)
                            print(f"  ✓ Berhasil klik element {items_count}")
                            return True
                        except:
                            pass
        except:
            pass
        
        print(f"  ⚠ Tidak ditemukan opsi untuk mengatur {items_count} item per halaman")
        print(f"  → Akan menggunakan jumlah default dari website")
        return False
        
    except Exception as e:
        print(f"  ✗ Error saat mencari opsi items per page: {e}")
        return False

def find_next_page_button(driver):
    """
    Mencari tombol next page atau pagination
    
    Returns:
        Element tombol next jika ditemukan, None jika tidak
    """
    next_button_selectors = [
        "button[aria-label*='Next']",
        "button[aria-label*='next']",
        "a[aria-label*='Next']",
        "a[aria-label*='next']",
        "button:contains('Next')",
        "a:contains('Next')",
        "[data-testid*='next']",
        "[data-testid*='Next']",
        ".pagination-next",
        ".next-page",
        "button[title*='Next']",
        "a[title*='Next']"
    ]
    
    # Coba cari dengan XPath juga
    xpath_selectors = [
        "//button[contains(text(), 'Next')]",
        "//a[contains(text(), 'Next')]",
        "//button[contains(., 'Next')]",
        "//a[contains(., 'Next')]"
    ]
    
    for selector in next_button_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                # Cek jika tombol tidak disabled
                if elem.is_displayed() and elem.is_enabled():
                    disabled = elem.get_attribute("disabled") or elem.get_attribute("aria-disabled")
                    if not disabled or disabled.lower() != "true":
                        return elem
        except:
            continue
    
    # Coba dengan XPath
    for xpath in xpath_selectors:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for elem in elements:
                if elem.is_displayed() and elem.is_enabled():
                    return elem
        except:
            continue
    
    return None

def scrape_xbox_gamepass(url="https://www.xbox.com/id-ID/xbox-game-pass/games#allgames", headless=False, save_to_file=True, max_pages=100):
    """
    Fungsi utama untuk scraping semua list game dari Xbox Game Pass dengan looping semua halaman
    
    Args:
        url: URL halaman Xbox Game Pass
        headless: True untuk menjalankan browser tanpa UI
        save_to_file: True untuk menyimpan hasil ke file JSON
        max_pages: Maksimal jumlah halaman yang akan di-scrape (default: 100)
    """
    driver = None
    all_games = []
    seen_titles = set()  # Untuk menghapus duplikat dari semua halaman
    
    try:
        print(f"Membuka halaman Xbox Game Pass: {url}")
        driver = init_driver(headless=headless)
        driver.get(url)
        
        # Tunggu sampai halaman dimuat
        wait = WebDriverWait(driver, 20)
        print("Menunggu halaman dimuat...")
        time.sleep(5)
        
        # Coba set items per page ke 200
        items_per_page_set = set_items_per_page(driver, items_count=200)
        
        # Tunggu sebentar setelah mengubah setting
        if items_per_page_set:
            print("\nMenunggu halaman refresh setelah perubahan setting...")
            time.sleep(5)
        
        print("\n" + "="*60)
        print("MEMULAI SCRAPING SEMUA HALAMAN XBOX GAME PASS")
        print("="*60)
        
        current_page = 1
        max_pages_reached = False
        
        while current_page <= max_pages:
            print(f"\n{'='*60}")
            print(f"PROSES HALAMAN {current_page} dari maksimal {max_pages}")
            print(f"{'='*60}")
            
            # Scrape halaman saat ini
            page_games = scrape_single_page_xbox(driver, current_page)
            
            # Tambahkan game dari halaman ini (skip duplikat)
            new_games_count = 0
            for game in page_games:
                title = game.get("title")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_games.append(game)
                    new_games_count += 1
            
            print(f"\n✓ Halaman {current_page}: Menambah {new_games_count} game baru")
            print(f"✓ Total game terkumpul: {len(all_games)}")
            
            # Cari tombol next page
            print(f"\nMencari tombol halaman berikutnya...")
            next_button = find_next_page_button(driver)
            
            if next_button:
                try:
                    # Scroll ke tombol next
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(2)
                    
                    # Klik tombol next
                    print(f"✓ Tombol Next ditemukan, menuju ke halaman {current_page + 1}...")
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(5)  # Tunggu halaman baru dimuat
                    
                    # Cek apakah benar-benar pindah halaman
                    new_url = driver.current_url
                    if new_url != url:
                        url = new_url
                        print(f"✓ Berhasil pindah ke halaman baru")
                    else:
                        # Coba tunggu lebih lama atau cek apakah sudah di halaman terakhir
                        time.sleep(3)
                        next_button_after = find_next_page_button(driver)
                        if not next_button_after or not next_button_after.is_enabled():
                            print(f"✓ Sudah mencapai halaman terakhir")
                            max_pages_reached = True
                            break
                    
                    current_page += 1
                    
                except Exception as e:
                    print(f"✗ Error saat klik tombol Next: {e}")
                    print(f"  Mencoba cara alternatif...")
                    
                    # Coba cara alternatif: cari link pagination
                    try:
                        # Coba cari nomor halaman berikutnya
                        next_page_link = driver.find_element(By.XPATH, f"//a[contains(text(), '{current_page + 1}')]")
                        next_page_link.click()
                        time.sleep(5)
                        current_page += 1
                    except:
                        # Jika tidak ada, mungkin sudah di halaman terakhir
                        print(f"✓ Tidak ada halaman berikutnya yang ditemukan")
                        max_pages_reached = True
                        break
            else:
                # Tidak ada tombol next, coba cek apakah menggunakan infinite scroll
                print(f"  Tidak ada tombol Next ditemukan")
                print(f"  Mencoba cek apakah masih ada konten yang bisa di-load...")
                
                # Scroll sekali lagi untuk memastikan semua konten sudah ter-load
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                
                # Jika ini halaman pertama dan belum ada game banyak, mungkin perlu scroll lebih
                if current_page == 1 and len(all_games) < 50:
                    print(f"  Melanjutkan scroll untuk memuat lebih banyak konten...")
                    time.sleep(3)
                    # Scrape sekali lagi untuk memastikan semua game terambil
                    additional_games = scrape_single_page_xbox(driver, current_page)
                    for game in additional_games:
                        title = game.get("title")
                        if title and title not in seen_titles:
                            seen_titles.add(title)
                            all_games.append(game)
                    
                    print(f"  ✓ Total setelah scroll tambahan: {len(all_games)} game")
                
                # Tidak ada pagination, hanya ada 1 halaman dengan infinite scroll
                print(f"✓ Selesai - Hanya ada 1 halaman dengan infinite scroll")
                max_pages_reached = True
                break
        
        if current_page > max_pages:
            print(f"\n⚠ Mencapai batas maksimal {max_pages} halaman")
        
        # Hapus duplikat final berdasarkan title
        final_games = []
        final_seen_titles = set()
        for game in all_games:
            title = game.get("title")
            if title and title not in final_seen_titles:
                final_seen_titles.add(title)
                final_games.append(game)
        
        all_games = final_games
        
        print(f"\n{'='*60}")
        print(f"SCRAPING SELESAI!")
        print(f"{'='*60}")
        print(f"Total halaman di-scrape: {current_page}")
        print(f"Total game berhasil di-scrape: {len(all_games)}")
        
        # Tampilkan beberapa contoh
        print("\n" + "-"*60)
        print("CONTOH GAME YANG DI-SCRAPE (10 pertama):")
        print("-"*60)
        for i, game in enumerate(all_games[:10], 1):
            print(f"\n{i}. {game.get('title', 'N/A')} (Halaman: {game.get('page_found', 'N/A')})")
            if game.get('url'):
                print(f"   URL: {game['url'][:80]}...")
        
        if len(all_games) > 10:
            print(f"\n... dan {len(all_games) - 10} game lainnya")
        
        # Simpan ke file jika diminta
        hasil = {
            "url_scraped": url,
            "total_pages": current_page,
            "total_games": len(all_games),
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "games": all_games
        }
        
        if save_to_file:
            filename = "hasil_scraping_xbox_gamepass.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(hasil, f, ensure_ascii=False, indent=2)
            print(f"\n" + "="*60)
            print(f"✓ Hasil disimpan ke: {filename}")
            print("="*60)
        
        return hasil
        
    except Exception as e:
        print(f"\n✗ Error terjadi: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        if driver:
            print("\nMenutup browser...")
            driver.quit()

def contoh_scraping_google():
    """
    Contoh lain: Mencari di Google
    """
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Inisialisasi driver dengan webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        print("Membuka Google...")
        driver.get("https://www.google.com")
        
        # Tunggu dan cari search box
        wait = WebDriverWait(driver, 10)
        search_box = wait.until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        
        # Ketik query
        search_query = "Selenium Python"
        search_box.send_keys(search_query)
        print(f"Mencari: {search_query}")
        
        # Submit form (atau tekan Enter)
        search_box.submit()
        
        # Tunggu hasil pencarian
        time.sleep(3)
        
        # Ambil title hasil pencarian
        print(f"Title hasil: {driver.title}")
        
        time.sleep(2)
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    print("=== Aplikasi Scraping Website dengan Selenium ===\n")
    
    # ========== KONFIGURASI ==========
    # PILIH MODE SCRAPING:
    
    # MODE 1: Scraping Xbox Game Pass (Uncomment untuk menggunakan)
    MODE_XBOX_GAMEPASS = True
    
    # MODE 2: Scraping Website Umum (Uncomment untuk menggunakan)
    # MODE_XBOX_GAMEPASS = False
    # TARGET_URL = "https://example.com"
    
    # Opsi:
    HEADLESS = False  # True untuk menjalankan tanpa membuka browser
    SAVE_TO_FILE = True  # True untuk menyimpan hasil ke file JSON
    
    # ==================================
    
    if MODE_XBOX_GAMEPASS:
        # Jalankan scraping Xbox Game Pass
        print("Mode: Scraping Xbox Game Pass\n")
        hasil = scrape_xbox_gamepass(
            url="https://www.xbox.com/id-ID/xbox-game-pass/games#allgames",
            headless=HEADLESS,
            save_to_file=SAVE_TO_FILE
        )
        
        if hasil:
            print(f"\n✓ Scraping berhasil! Total game: {hasil.get('total_games', 0)}")
        else:
            print("\n✗ Scraping gagal!")
    else:
        # Jalankan scraping website umum
        TARGET_URL = "https://example.com"  # Default URL
        hasil = scrape_website(
            url=TARGET_URL,
            headless=HEADLESS,
            save_to_file=SAVE_TO_FILE
        )
        
        if hasil:
            print("\n✓ Scraping berhasil!")
        else:
            print("\n✗ Scraping gagal!")

