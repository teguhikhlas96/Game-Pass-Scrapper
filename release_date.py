import json
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import re

# Metode 1: Menggunakan Wikipedia (Gratis, tidak perlu API key)
def get_release_date_wikipedia(game_title):
    """
    Scraping release date dari Wikipedia
    """
    try:
        # Search Wikipedia
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            'action': 'opensearch',
            'search': game_title,
            'limit': 1,
            'format': 'json'
        }
        
        response = requests.get(search_url, params=search_params, timeout=10)
        results = response.json()
        
        if len(results[3]) > 0:
            page_url = results[3][0]
            
            # Get page content
            page_params = {
                'action': 'parse',
                'page': results[1][0],
                'format': 'json',
                'prop': 'text'
            }
            
            page_response = requests.get(search_url, params=page_params, timeout=10)
            page_data = page_response.json()
            
            if 'parse' in page_data:
                html_content = page_data['parse']['text']['*']
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Cari infobox
                infobox = soup.find('table', class_='infobox')
                if infobox:
                    # Cari baris release date
                    rows = infobox.find_all('tr')
                    for row in rows:
                        th = row.find('th')
                        if th and 'release' in th.get_text().lower():
                            td = row.find('td')
                            if td:
                                release_text = td.get_text().strip()
                                # Extract tahun
                                years = re.findall(r'\b(19\d{2}|20\d{2})\b', release_text)
                                if years:
                                    return {
                                        'title': game_title,
                                        'source': 'Wikipedia',
                                        'release_date': years[0],
                                        'full_text': release_text[:100],
                                        'url': page_url
                                    }
        
        return None
    except Exception as e:
        print(f"Error Wikipedia for {game_title}: {str(e)}")
        return None


# Metode 2: Menggunakan SteamAPI (Gratis, tidak perlu key)
def get_release_date_steam(game_title):
    """
    Mendapatkan release date dari Steam Store API
    """
    try:
        # Search Steam
        search_url = "https://steamcommunity.com/actions/SearchApps/"
        params = {'q': game_title}
        
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                app_id = data[0]['appid']
                
                # Get game details
                details_url = f"https://store.steampowered.com/api/appdetails"
                details_params = {'appids': app_id}
                
                details_response = requests.get(details_url, params=details_params, timeout=10)
                details_data = details_response.json()
                
                if str(app_id) in details_data and details_data[str(app_id)]['success']:
                    game_data = details_data[str(app_id)]['data']
                    release_date = game_data.get('release_date', {})
                    
                    return {
                        'title': game_title,
                        'matched_name': game_data.get('name', ''),
                        'source': 'Steam',
                        'release_date': release_date.get('date', 'Unknown'),
                        'coming_soon': release_date.get('coming_soon', False),
                        'steam_url': f"https://store.steampowered.com/app/{app_id}"
                    }
        
        return None
    except Exception as e:
        print(f"Error Steam for {game_title}: {str(e)}")
        return None


# Metode 3: Menggunakan Giant Bomb API (Gratis dengan registrasi sederhana)
def get_release_date_giantbomb(game_title, api_key=None):
    """
    Mendapatkan release date dari Giant Bomb API
    API Key gratis di: https://www.giantbomb.com/api/
    """
    if not api_key:
        return None
        
    try:
        url = "https://www.giantbomb.com/api/search/"
        params = {
            'api_key': api_key,
            'format': 'json',
            'query': game_title,
            'resources': 'game',
            'limit': 1
        }
        
        headers = {'User-Agent': 'GamePassReleaseChecker/1.0'}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                game = data['results'][0]
                return {
                    'title': game_title,
                    'matched_name': game.get('name', ''),
                    'source': 'Giant Bomb',
                    'release_date': game.get('original_release_date', 'Unknown'),
                    'platforms': [p['name'] for p in game.get('platforms', [])[:5]]
                }
        
        return None
    except Exception as e:
        print(f"Error Giant Bomb for {game_title}: {str(e)}")
        return None


# Metode 4: Menggunakan Metacritic (Web Scraping)
def get_release_date_metacritic(game_title):
    """
    Scraping dari Metacritic (backup method)
    """
    try:
        # Format title untuk URL
        formatted_title = game_title.lower().replace(' ', '-')
        formatted_title = re.sub(r'[^\w\-]', '', formatted_title)
        
        # Coba PC platform dulu
        url = f"https://www.metacritic.com/game/pc/{formatted_title}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cari release date
            release_span = soup.find('span', class_='release-date')
            if release_span:
                return {
                    'title': game_title,
                    'source': 'Metacritic',
                    'release_date': release_span.get_text().strip(),
                    'url': url
                }
        
        return None
    except Exception as e:
        print(f"Error Metacritic for {game_title}: {str(e)}")
        return None


def clean_game_title(title):
    """
    Membersihkan title dari karakter khusus
    """
    replacements = {
        '®': '',
        '™': '',
        '©': '',
        'â„¢': '',
        'Â®': '',
        '  ': ' ',
    }
    
    cleaned = title
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    
    # Hapus info dalam kurung
    if '(' in cleaned:
        cleaned = cleaned.split('(')[0]
    if '[' in cleaned:
        cleaned = cleaned.split('[')[0]
    
    # Hapus "Edition", "for Windows", dll
    remove_words = [' Edition', ' for Windows', ' - Windows', ' PC', ' (PC)', ' Standard']
    for word in remove_words:
        cleaned = cleaned.replace(word, '')
    
    return cleaned.strip()


def process_all_games(json_file, methods=['steam', 'wikipedia'], giantbomb_key=None):
    """
    Memproses semua game dengan multiple methods
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    games = data['games']
    results = []
    
    print(f"Processing {len(games)} games using methods: {', '.join(methods)}")
    print("=" * 60)
    
    for idx, game in enumerate(games, 1):
        title = game['title']
        cleaned_title = clean_game_title(title)
        
        print(f"\n[{idx}/{len(games)}] {cleaned_title}")
        
        result = None
        
        # Coba setiap method sampai dapat hasil
        for method in methods:
            if method == 'steam':
                result = get_release_date_steam(cleaned_title)
            elif method == 'wikipedia':
                result = get_release_date_wikipedia(cleaned_title)
            elif method == 'metacritic':
                result = get_release_date_metacritic(cleaned_title)
            elif method == 'giantbomb' and giantbomb_key:
                result = get_release_date_giantbomb(cleaned_title, giantbomb_key)
            
            if result:
                print(f"  ✓ Found via {result['source']}: {result['release_date']}")
                break
            else:
                print(f"  ✗ Not found via {method}")
            
            time.sleep(0.5)  # Small delay between methods
        
        if not result:
            result = {
                'title': title,
                'matched_name': 'Not Found',
                'source': 'None',
                'release_date': 'Unknown'
            }
        
        results.append(result)
        
        # Rate limiting
        time.sleep(1.5)
        
        # Save progress setiap 25 game
        if idx % 25 == 0:
            save_progress(results, f'progress_{idx}_games.json')
            print(f"\n>>> Progress saved: {idx} games processed")
    
    return results


def save_progress(results, filename='game_release_dates.json'):
    """
    Menyimpan hasil ke file JSON
    """
    output = {
        'total_processed': len(results),
        'timestamp': datetime.now().isoformat(),
        'found': sum(1 for r in results if r['release_date'] != 'Unknown'),
        'not_found': sum(1 for r in results if r['release_date'] == 'Unknown'),
        'games': results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to {filename}")


def print_statistics(results):
    """
    Menampilkan statistik hasil
    """
    total = len(results)
    found = sum(1 for r in results if r['release_date'] != 'Unknown')
    
    sources = {}
    for r in results:
        source = r.get('source', 'Unknown')
        sources[source] = sources.get(source, 0) + 1
    
    print("\n" + "=" * 60)
    print("STATISTICS")
    print("=" * 60)
    print(f"Total games processed: {total}")
    print(f"Release dates found: {found} ({found/total*100:.1f}%)")
    print(f"Not found: {total - found} ({(total-found)/total*100:.1f}%)")
    print("\nSources breakdown:")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {source}: {count}")


# MAIN EXECUTION
if __name__ == "__main__":
    # Path ke file JSON
    json_file = 'xbox_gamepass_games_20251103_130324 after frostpunk 2.json'
    
    # Pilih methods yang ingin digunakan (urutan prioritas)
    methods = ['giantbomb']
    
    # Optional: Giant Bomb API key (gratis di https://www.giantbomb.com/api/)
    giantbomb_key = '3587fb5f91911d92ae351c60f37885e669c5d838'  # Isi dengan key jika punya
   
    print("Xbox Game Pass Release Date Fetcher")
    print("=" * 60)
    print("Methods: Giant Bomb")
    print("No registration required!")
    print("=" * 60)
    
    # Process all games
    results = process_all_games(json_file, methods=methods, giantbomb_key=giantbomb_key)
    
    # Save final results
    save_progress(results, 'game_release_dates_final.json')
    
    # Print statistics
    print_statistics(results)
    
    print("\n✓ Process completed!")