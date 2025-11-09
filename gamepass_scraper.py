"""
Xbox Game Pass Games Scraper
Scrapes all games from https://www.xbox.com/en-US/xbox-game-pass/games#all-games
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import json
import csv
import time
import requests
from datetime import datetime, timedelta
from threading import Lock


def wait_with_countdown(wait_time_seconds, message="Waiting"):
    """
    Wait for specified time with countdown display
    
    Args:
        wait_time_seconds (float): Time to wait in seconds
        message (str): Message to display before countdown
    """
    print(f"\n{message}")
    wait_time_seconds = int(wait_time_seconds)  # Convert to int for display
    print(f"⏳ Countdown: {wait_time_seconds // 3600}h {(wait_time_seconds % 3600) // 60}m {wait_time_seconds % 60}s remaining...")
    
    remaining = wait_time_seconds
    update_interval = 10  # Update every 10 seconds
    
    while remaining > 0:
        sleep_time = min(update_interval, remaining)
        time.sleep(sleep_time)
        remaining -= sleep_time
        
        if remaining > 0:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60
            print(f"⏳ Countdown: {hours}h {minutes}m {seconds}s remaining...")
    
    print("✅ Wait completed! Resuming...\n")


class RateLimiter:
    """
    Rate limiter for GiantBomb API
    Official limit: 200 requests per resource per hour
    Also implements velocity detection prevention (min delay between requests)
    """
    def __init__(self, max_requests=200, time_window=3600, min_delay=2.0):
        self.max_requests = max_requests  # 200 requests per hour (official limit)
        self.time_window = time_window  # 1 hour in seconds
        self.min_delay = min_delay  # Minimum delay between requests (seconds) to avoid velocity detection
        self.requests = []
        self.last_request_time = 0
        self.lock = Lock()
    
    def wait_if_needed(self):
        """
        Wait if rate limit is reached or to prevent velocity detection
        """
        with self.lock:
            now = time.time()
            
            # Remove requests older than time_window
            self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
            
            # Check hourly rate limit (200 requests/hour)
            if len(self.requests) >= self.max_requests:
                # Calculate wait time until oldest request expires
                oldest_request = min(self.requests)
                wait_time = self.time_window - (now - oldest_request) + 1  # Add 1 second buffer
                
                if wait_time > 0:
                    print(f"\n⚠️  Rate limit reached (200 requests/hour). Waiting {wait_time/60:.1f} minutes...")
                    wait_with_countdown(wait_time, "⏸️  Rate limit reached. Waiting...")
                    # Clear old requests after waiting
                    self.requests = []
                    self.last_request_time = time.time()
            
            # Velocity detection prevention: ensure minimum delay between requests
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_delay:
                delay_needed = self.min_delay - time_since_last
                if delay_needed > 0:
                    time.sleep(delay_needed)
            
            # Record this request
            self.requests.append(time.time())
            self.last_request_time = time.time()
    
    def get_remaining_requests(self):
        """Get remaining requests in current window"""
        with self.lock:
            now = time.time()
            self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
            return self.max_requests - len(self.requests)


class GamePassScraper:
    def __init__(self, headless=False, debug=False, filter_2025_only=False):
        """
        Initialize the scraper with Chrome WebDriver
        
        Args:
            headless (bool): Run browser in headless mode
            debug (bool): Enable debug logging
            filter_2025_only (bool): If True, only include games released in 2025 (requires GiantBomb API)
        """
        self.headless = headless
        self.debug = debug
        self.filter_2025_only = filter_2025_only
        self.driver = None
        self.games = []
        self.giantbomb_api_key = "8b6e036a70bd8b3d7dae00c30939a4b5a5a41b65"
        # GiantBomb official limit: 200 requests per resource per hour
        # min_delay=2.0 seconds between requests to avoid velocity detection
        self.rate_limiter = RateLimiter(max_requests=200, time_window=3600, min_delay=2.0) if filter_2025_only else None
        # Cache for release dates to avoid duplicate API calls
        self.release_date_cache = {}
        self.cache_file = 'release_date_cache.json'
        self.load_cache()
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Use webdriver-manager to automatically handle ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            print("Chrome WebDriver initialized successfully")
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            print("Make sure Chrome browser is installed")
            raise
    
    def is_valid_game(self, href, game_name):
        """
        Check if the URL and name represent a valid game (not navigation/category)
        
        Args:
            href: URL of the potential game
            game_name: Name of the potential game
            
        Returns:
            bool: True if it's a valid game, False otherwise
        """
        if not href or not game_name:
            return False
        
        # Filter out navigation/category URLs
        invalid_url_patterns = [
            '?xr=shellnav',
            '?xr=footnav',
            '/games/all-games',
            '/games/xbox-play-anywhere',
            '/games/free-to-play',
            '/games/optimized',
            '/games/backward-compatibility',
            '/games/ea-play',
            'developer.microsoft.com',
        ]
        
        # Check if URL contains invalid patterns
        for pattern in invalid_url_patterns:
            if pattern in href:
                return False
        
        # Check for generic store link without game ID (exact match or ends with /games/store/)
        if href.rstrip('/').endswith('/games/store') or href.rstrip('/') == '/games/store':
            return False
        
        # Must be a game store URL with game ID (format: /games/store/game-name/ID)
        if '/games/store/' not in href:
            return False
        
        # Extract the part after /games/store/
        parts = href.split('/games/store/')
        if len(parts) < 2:
            return False
        
        game_part = parts[1].split('?')[0].split('#')[0]
        # Should have game name and ID separated by /
        if '/' not in game_part:
            return False
        
        try:
            game_slug, game_id = game_part.split('/', 1)
            # Game ID should be reasonable length (relaxed: 3-60 chars)
            if len(game_id) < 3 or len(game_id) > 60:
                return False
        except:
            return False
        
        # Filter out navigation/category names (exact matches only)
        invalid_names = [
            'all games',
            'xbox anywhere',
            'free to play',
            'optimized',
            'backward compatibility',
            'store',  # Only reject if it's exactly "Store"
            'games for developers',
            'explore',
            'browse',
            'learn more',
            'get the app',
            'download',
            'upgrade',
            'show more',
            'load more',
            'see more',
            'play fortnite',  # Action button, not game name
        ]
        
        game_name_lower = game_name.lower().strip()
        
        # Check exact matches only (not partial)
        if game_name_lower in invalid_names:
            return False
        
        # Don't reject names that just contain these words (e.g., "Store" in "Game Store" is OK)
        # Only reject if name starts with invalid patterns and is short
        short_invalid_patterns = ['store', 'explore', 'browse', 'learn more', 'get the app']
        for invalid in short_invalid_patterns:
            if game_name_lower.startswith(invalid) and len(game_name) < 15:
                return False
        
        # Filter out names that are too short or too long
        if len(game_name) < 2 or len(game_name) > 150:
            return False
        
        # Filter out names that contain navigation text (but be more lenient)
        # Only reject if it's clearly a navigation button, not a game name with "play" in it
        navigation_keywords = ['learn more,', 'explore,', 'browse,', 'get the app', 'download the app', 
                              'upgrade to', 'buy ', 'shop ']
        for keyword in navigation_keywords:
            if keyword in game_name_lower:
                # If it starts with navigation keyword, it's likely not a game
                if game_name_lower.startswith(keyword.split(',')[0]):
                    return False
        
        # Special case: "PLAY FORTNITE" is a button, but "Play" in game name is OK
        if game_name_lower == 'play fortnite':
            return False
        
        # Filter out names that still contain subscription tier info (should be cleaned before this)
        if 'ULTIMATE' in game_name.upper() or 'PREMIUM' in game_name.upper() or 'ESSENTIAL' in game_name.upper():
            # If it's just subscription info, not a game
            if len(game_name) < 20 and ('·' in game_name or 'PC' in game_name.upper()):
                return False
        
        return True
    
    def clean_game_name(self, game_name):
        """
        Clean game name from subscription info and other non-game text
        
        Args:
            game_name: Raw game name
            
        Returns:
            str: Cleaned game name
        """
        if not game_name:
            return ""
        
        # Remove common navigation prefixes (case-insensitive)
        navigation_prefixes = ['LEARN MORE,', 'LEARN MORE', 'Explore,', 'Explore', 'EXPLORE,', 'EXPLORE', 'explore']
        game_name_original = game_name
        for prefix in navigation_prefixes:
            if game_name.lower().startswith(prefix.lower()):
                game_name = game_name[len(prefix):].strip()
                # Remove leading comma if any
                if game_name.startswith(','):
                    game_name = game_name[1:].strip()
                break
        
        # Also handle "explore Game Name" pattern (lowercase explore at start)
        if game_name.lower().startswith('explore '):
            game_name = game_name[8:].strip()  # Remove "explore " (8 chars)
        
        # Split by newlines and filter out subscription info
        lines = game_name.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Skip subscription tier info
            if any(keyword in line.upper() for keyword in ['ULTIMATE', 'PREMIUM', 'ESSENTIAL', 'PC', 'CONSOLE']):
                if '·' in line or len(line) < 15:
                    continue
            # Skip description lines (too long)
            if len(line) > 100:
                continue
            # Skip lines that are just navigation text
            if line.upper() in ['LEARN MORE', 'EXPLORE', 'BROWSE', 'STORE']:
                continue
            # This might be the game name
            cleaned_lines.append(line)
        
        # If we have cleaned lines, use the first reasonable one
        if cleaned_lines:
            for line in cleaned_lines:
                # Prefer lines that look like game names (not too short, not too long, not all caps subscription info)
                if 3 < len(line) < 100:
                    # Check if it's not just subscription info
                    line_upper = line.upper()
                    if not (len(line) < 20 and ('ULTIMATE' in line_upper or 'PREMIUM' in line_upper or 'ESSENTIAL' in line_upper)):
                        return line
        
        # Fallback: remove common prefixes
        original_name = game_name
        game_name = game_name.replace('Play ', '').replace('Buy ', '').strip()
        
        # Remove subscription info from beginning (lines with · separator)
        if '·' in game_name:
            parts = game_name.split('·')
            for part in parts:
                part = part.strip()
                if part and 'ULTIMATE' not in part.upper() and 'PREMIUM' not in part.upper() and 'ESSENTIAL' not in part.upper():
                    if 3 < len(part) < 100:
                        return part
        
        # If still no good name, try to extract from multiline text
        # Look for the longest line that's not subscription info
        lines = original_name.split('\n')
        best_line = ""
        for line in lines:
            line = line.strip()
            if 5 < len(line) < 100:
                line_upper = line.upper()
                # Skip if it's subscription info
                if 'ULTIMATE' in line_upper or 'PREMIUM' in line_upper or 'ESSENTIAL' in line_upper:
                    if len(line) < 25:  # Short subscription lines
                        continue
                # Prefer longer lines that look like game names
                if len(line) > len(best_line):
                    best_line = line
        
        if best_line:
            return best_line
        
        return game_name.strip() if game_name.strip() else ""
    
    def load_more_games(self, max_attempts=100):
        """
        Try to load more games by clicking pagination/load more buttons
        
        Args:
            max_attempts (int): Maximum number of attempts to load more games
        """
        print("\nTrying to load more games...")
        attempt = 0
        no_new_games_count = 0
        last_total_games = len(self.games)
        
        while attempt < max_attempts:
            attempt += 1
            games_before = len(self.games)
            
            # Try to find and click load more/pagination buttons
            button_found = False
            
            # List of possible button selectors (ONLY Next button, no More buttons)
            # Prioritize Xbox Game Pass specific selectors first
            button_selectors = [
                # Xbox Game Pass specific selectors (highest priority)
                ("//li[contains(@class, 'paginatenext')]//a", "paginatenext li > a"),
                ("//a[@data-loc-aria='keyArianextpage']", "data-loc-aria keyArianextpage"),
                ("//a[contains(@class, 'c-glyph')]//span[text()='Next']/parent::a", "c-glyph with Next span"),
                ("//a[contains(@class, 'c-glyph') and .//span[text()='Next']]", "c-glyph containing Next span"),
                # Next button selectors - exact matches
                ("//button[normalize-space(text())='Next']", "Next (exact)"),
                ("//button[normalize-space(text())='NEXT']", "NEXT (exact)"),
                ("//a[normalize-space(text())='Next']", "Next link (exact)"),
                # Aria-label selectors
                ("//button[@aria-label='Next' or @aria-label='next' or @aria-label='Next page' or @aria-label='Go to next page']", "Next (aria-label)"),
                ("//button[contains(@aria-label, 'next') and not(contains(@aria-label, 'more'))]", "Next (aria-label contains)"),
                # Class-based selectors (common in pagination)
                ("//button[contains(@class, 'next') and not(contains(@class, 'more')) and not(contains(@class, 'previous'))]", "next class"),
                ("//button[contains(@class, 'pagination') and contains(@class, 'next')]", "pagination next"),
                # Data attribute selectors
                ("//button[@data-testid='next' or @data-testid='next-button' or @data-testid='pagination-next']", "next testid"),
                # Text contains (but exclude More)
                ("//button[contains(text(), 'Next') and not(contains(text(), 'More'))]", "Next (contains)"),
                ("//a[contains(text(), 'Next') and not(contains(text(), 'More'))]", "Next link (contains)"),
                # Arrow buttons - look for buttons with arrow icons that might be next
                ("//button[contains(@class, 'arrow') and contains(@class, 'right')]", "arrow right"),
                ("//button[contains(@class, 'chevron') and contains(@class, 'right')]", "chevron right"),
            ]
            
            for selector, description in button_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    for button in buttons:
                        try:
                                # Check if button is visible and clickable
                            if button.is_displayed() and button.is_enabled():
                                # Get button text and attributes for verification
                                button_text = button.text.strip().upper()
                                aria_label = (button.get_attribute("aria-label") or "").lower()
                                button_class = (button.get_attribute("class") or "").lower()
                                data_testid = (button.get_attribute("data-testid") or "").lower()
                                
                                # STRICTLY reject any button with "More" in text or aria-label
                                if ("more" in button_text or "more" in aria_label) and "next" not in button_text and "next" not in aria_label:
                                    if self.debug:
                                        print(f"  Skipping button with 'More' - text: '{button.text.strip()}', aria-label: '{aria_label}'")
                                    continue
                                
                                # For Xbox Game Pass specific selectors, trust them
                                if "paginatenext" in description.lower() or "keyArianextpage" in description.lower() or "c-glyph" in description.lower():
                                    # These are Xbox-specific selectors, trust them
                                    # Just verify it's not "More" or "Previous"
                                    if "more" in button_text or "more" in aria_label:
                                        if self.debug:
                                            print(f"  Skipping Xbox Next button - has 'more' - text: '{button.text.strip()}'")
                                        continue
                                    if "previous" in button_text or "previous" in aria_label:
                                        if self.debug:
                                            print(f"  Skipping Xbox Next button - has 'previous' - text: '{button.text.strip()}'")
                                        continue
                                    
                                    # Check if span inside has "Next" text
                                    try:
                                        span_text = button.find_element(By.XPATH, ".//span").text.strip().upper()
                                        if "NEXT" in span_text:
                                            if self.debug:
                                                print(f"  Found valid Xbox Next button - span text: '{span_text}'")
                                        elif "MORE" in span_text or "PREVIOUS" in span_text:
                                            if self.debug:
                                                print(f"  Skipping - span has '{span_text}'")
                                            continue
                                    except:
                                        # No span found, but selector matched so it's probably Next
                                        pass
                                
                                # For other Next buttons, check multiple sources
                                elif "next" in description.lower():
                                    # Check if it has "next" in text, aria-label, class, or data-testid
                                    has_next = (
                                        "next" in button_text or 
                                        "next" in aria_label or 
                                        "next" in button_class or 
                                        "next" in data_testid
                                    )
                                    
                                    # Check if it has "more" (should not)
                                    has_more = (
                                        ("more" in button_text and "next" not in button_text) or
                                        ("more" in aria_label and "next" not in aria_label)
                                    )
                                    
                                    # If button has no text but matches Next selector, it might be an icon button
                                    # Allow it if it matches the selector pattern
                                    if not has_next:
                                        if self.debug:
                                            print(f"  Skipping button - no 'next' found - text: '{button.text.strip()}', aria-label: '{aria_label}', class: '{button_class[:50]}'")
                                        continue
                                    
                                    if has_more:
                                        if self.debug:
                                            print(f"  Skipping button - has 'more' - text: '{button.text.strip()}', aria-label: '{aria_label}'")
                                        continue
                                    
                                    # If we get here, it's a valid Next button
                                    if self.debug:
                                        print(f"  Found valid Next button - text: '{button.text.strip()}', aria-label: '{aria_label}'")
                                
                                # Scroll to button
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                                time.sleep(1)
                                
                                # Try to click
                                try:
                                    button.click()
                                except:
                                    # If normal click fails, try JavaScript click
                                    self.driver.execute_script("arguments[0].click();", button)
                                
                                print(f"  Clicked '{description}' button (text: '{button.text.strip()}') (attempt {attempt})")
                                button_found = True
                                time.sleep(3)  # Wait for content to load
                                
                                # Scroll to load new content
                                self.scroll_and_load_games(max_scrolls=10)
                                
                                # Extract new games
                                self.extract_games()
                                
                                games_after = len(self.games)
                                new_games = games_after - games_before
                                
                                if new_games > 0:
                                    print(f"  Found {new_games} new games (total: {games_after})")
                                    no_new_games_count = 0
                                    last_total_games = games_after
                                else:
                                    no_new_games_count += 1
                                    print(f"  No new games found (attempt {attempt})")
                                
                                break
                        except Exception as e:
                            if self.debug:
                                print(f"  Error clicking button: {e}")
                            continue
                    
                    if button_found:
                        break
                except:
                    continue
            
            # If no button found, try to find Next button by position in pagination
            if not button_found:
                try:
                    # Look for pagination container and find the last button (often Next)
                    pagination_containers = self.driver.find_elements(By.XPATH, 
                        "//nav[contains(@class, 'pagination')] | //div[contains(@class, 'pagination')] | //ul[contains(@class, 'pagination')]")
                    
                    for container in pagination_containers:
                        try:
                            # Find all buttons/links in pagination
                            pagination_items = container.find_elements(By.XPATH, ".//button | .//a")
                            
                            if len(pagination_items) > 1:
                                # Try the last button (often Next)
                                last_button = pagination_items[-1]
                                if last_button.is_displayed() and last_button.is_enabled():
                                    button_text = last_button.text.strip().upper()
                                    aria_label = (last_button.get_attribute("aria-label") or "").lower()
                                    
                                    # Skip if it says "Previous" or "More"
                                    if "previous" in button_text or "previous" in aria_label:
                                        continue
                                    if "more" in button_text or "more" in aria_label:
                                        continue
                                    
                                    # If it's not "Previous", it might be Next
                                    if button_text != "PREVIOUS" and "previous" not in aria_label:
                                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", last_button)
                                        time.sleep(1)
                                        
                                        try:
                                            last_button.click()
                                        except:
                                            self.driver.execute_script("arguments[0].click();", last_button)
                                        
                                        print(f"  Clicked pagination last button (text: '{last_button.text.strip()}', aria-label: '{aria_label}') (attempt {attempt})")
                                        button_found = True
                                        time.sleep(3)
                                        
                                        self.scroll_and_load_games(max_scrolls=10)
                                        self.extract_games()
                                        
                                        games_after = len(self.games)
                                        new_games = games_after - games_before
                                        
                                        if new_games > 0:
                                            print(f"  Found {new_games} new games (total: {games_after})")
                                            no_new_games_count = 0
                                            last_total_games = games_after
                                        else:
                                            no_new_games_count += 1
                                            print(f"  No new games found (attempt {attempt})")
                                        
                                        break
                        except:
                            continue
                    
                    if button_found:
                        continue
                except:
                    pass
            
            # If no button found, try scrolling to trigger lazy loading
            if not button_found:
                print(f"  No load more button found (attempt {attempt}), trying scroll...")
                self.scroll_and_load_games(max_scrolls=20)
                self.extract_games()
                
                games_after = len(self.games)
                new_games = games_after - games_before
                
                if new_games > 0:
                    print(f"  Found {new_games} new games via scroll (total: {games_after})")
                    no_new_games_count = 0
                    last_total_games = games_after
                else:
                    no_new_games_count += 1
                    print(f"  No new games via scroll (attempt {attempt})")
            
            # Stop if no new games found for several attempts (increased threshold)
            if no_new_games_count >= 5:
                print(f"\nNo new games found for {no_new_games_count} attempts. Stopping.")
                break
            
            # Small delay between attempts
            time.sleep(2)
        
        print(f"\nFinished loading more games. Total games: {len(self.games)}")
    
    def scroll_and_load_games(self, max_scrolls=50):
        """
        Scroll the page to load all games dynamically
        
        Args:
            max_scrolls (int): Maximum number of scroll attempts
        """
        print("Scrolling to load all games...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        
        while scroll_attempts < max_scrolls:
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for content to load
            
            # Calculate new scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                # Try scrolling to specific sections
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    print("No more content to load")
                    break
            
            last_height = new_height
            scroll_attempts += 1
            print(f"Scroll attempt {scroll_attempts}, loaded {len(self.games)} games so far...")
        
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
    
    def extract_games(self):
        """Extract game information from the page"""
        print("Extracting games from page...")
        
        try:
            # Wait for page to be fully loaded
            time.sleep(3)
            
            # Try multiple selectors for game cards (Xbox Game Pass specific)
            game_selectors = [
                # Common Xbox Game Pass selectors
                "//a[contains(@href, '/games/') and not(contains(@href, 'game-pass'))]",
                "//div[contains(@class, 'm-product-placement-item')]//a",
                "//article//a[contains(@href, '/games/')]",
                "//div[@role='article']//a",
                "//a[contains(@class, 'game')]",
                "//div[contains(@class, 'GameCard')]//a",
            ]
            
            games_found = []
            game_names = set()  # Use set to avoid duplicates
            
            # Try each selector
            for selector in game_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and len(elements) > len(games_found):
                        print(f"Found {len(elements)} elements with selector: {selector[:50]}...")
                        games_found = elements
                except Exception as e:
                    continue
            
            # If no games found with XPath, try CSS selectors
            if not games_found:
                css_selectors = [
                    "a[href*='/games/']:not([href*='game-pass']):not([href*='xbox-game-pass'])",
                    "div[class*='game'] a",
                    "article a[href*='/games/']",
                ]
                
                for css_sel in css_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, css_sel)
                        if elements:
                            print(f"Found {len(elements)} elements with CSS selector")
                            games_found = elements
                            break
                    except:
                        continue
            
            print(f"Processing {len(games_found)} potential game elements...")
            
            skipped_count = 0
            processed_count = 0
            
            # Extract game information
            for element in games_found:
                try:
                    # Get href first
                    href = element.get_attribute('href')
                    
                    # Skip if not a game store URL
                    if not href:
                        skipped_count += 1
                        continue
                    
                    # Check if it's a game store URL
                    # Accept both /games/store/ and /en-us/games/store/ formats
                    is_game_store = '/games/store/' in href or '/en-us/games/store/' in href
                    has_game_pass = 'game-pass' in href.lower() or 'xbox-game-pass' in href.lower()
                    
                    if not is_game_store or has_game_pass:
                        skipped_count += 1
                        continue
                    
                    # Normalize URL format - handle /en-us/games/store/ or /games/store/
                    normalized_href = href
                    if '/en-us/games/store/' in href:
                        normalized_href = href.replace('/en-us/games/store/', '/games/store/')
                    elif '/games/store/' not in href:
                        skipped_count += 1
                        continue
                    
                    # Check URL format - must have game ID (format: /games/store/game-name/ID)
                    parts = normalized_href.split('/games/store/')
                    if len(parts) < 2:
                        skipped_count += 1
                        continue
                    
                    game_part = parts[1].split('?')[0].split('#')[0]
                    if '/' not in game_part:
                        skipped_count += 1
                        continue  # No game ID, skip
                    
                    try:
                        game_slug, game_id = game_part.split('/', 1)
                        # Game ID should be reasonable (relaxed: 3-60 chars)
                        if len(game_id) < 3 or len(game_id) > 60:
                            skipped_count += 1
                            continue
                    except:
                        skipped_count += 1
                        continue
                    
                    # Use normalized href for further processing
                    href = normalized_href
                    
                    processed_count += 1
                    
                    # Try to get game name from various sources
                    game_name = None
                    
                    # Method 1: aria-label
                    game_name = element.get_attribute('aria-label')
                    
                    # Method 2: title attribute
                    if not game_name or len(game_name) < 2:
                        game_name = element.get_attribute('title')
                    
                    # Method 3: text content (but filter out navigation text)
                    if not game_name or len(game_name) < 2:
                        text = element.text.strip()
                        # Filter out common navigation text
                        skip_texts = ['EXPLORE', 'LEARN MORE', 'GET THE APP', 'DOWNLOAD', 
                                     'UPGRADE', 'SHOW MORE', 'LOAD MORE', 'SEE MORE']
                        if text and not any(skip in text.upper() for skip in skip_texts):
                            if 2 < len(text) < 100:  # Reasonable game name length
                                game_name = text
                    
                    # Method 4: Look for heading or span inside
                    if not game_name or len(game_name) < 2:
                        try:
                            # Try to find h2, h3, or span with game name
                            for tag in ['h2', 'h3', 'h4', 'span', 'div']:
                                try:
                                    child = element.find_element(By.TAG_NAME, tag)
                                    text = child.text.strip()
                                    if text and 2 < len(text) < 100:
                                        skip_texts = ['EXPLORE', 'LEARN MORE', 'GET THE APP', 'STORE']
                                        if not any(skip in text.upper() for skip in skip_texts):
                                            game_name = text
                                            break
                                except:
                                    continue
                        except:
                            pass
                    
                    # Method 5: If name is just "Store", try to find game name from parent or nearby elements
                    if game_name and game_name.lower().strip() == 'store':
                        try:
                            # Try parent element
                            parent = element.find_element(By.XPATH, "./..")
                            parent_text = parent.text.strip()
                            if parent_text and len(parent_text) > 3 and len(parent_text) < 100:
                                # Check if parent has a better name
                                if 'store' not in parent_text.lower() or len(parent_text) > 10:
                                    game_name = parent_text
                        except:
                            pass
                        
                        # If still "Store", try to find sibling elements
                        if game_name and game_name.lower().strip() == 'store':
                            try:
                                # Look for h2, h3, or strong tags nearby
                                for tag in ['h2', 'h3', 'h4', 'strong', 'b']:
                                    try:
                                        sibling = element.find_element(By.XPATH, f".//{tag}")
                                        text = sibling.text.strip()
                                        if text and 3 < len(text) < 100 and text.upper() != 'STORE':
                                            game_name = text
                                            break
                                    except:
                                        continue
                            except:
                                pass
                    
                    # Method 6: Extract from URL if it contains game name
                    if not game_name or len(game_name) < 2 or game_name.lower().strip() == 'store':
                        if href:
                            # Try to extract game name from URL
                            try:
                                # Extract from /games/store/game-slug/ID format
                                if '/games/store/' in href:
                                    parts = href.split('/games/store/')
                                    if len(parts) > 1:
                                        game_slug = parts[1].split('/')[0].split('?')[0]
                                        # Convert slug to readable name
                                        game_name = game_slug.replace('-', ' ').title()
                                        # Clean up common suffixes
                                        game_name = game_name.replace(' Xbox Series X S Version', '')
                                        game_name = game_name.replace(' Xbox One', '')
                                        game_name = game_name.replace(' Windows Edition', '')
                                        game_name = game_name.replace(' Game Preview', '')
                                        game_name = game_name.replace(' Standard Edition', '')
                                        game_name = game_name.replace(' Console', '')
                            except:
                                pass
                    
                    # Clean up game name
                    if not game_name or len(game_name) < 2:
                        # Final fallback: extract from URL
                        try:
                            if '/games/store/' in href:
                                game_slug = href.split('/games/store/')[1].split('/')[0].split('?')[0]
                                game_name = game_slug.replace('-', ' ').title()
                                # Clean up common suffixes
                                game_name = game_name.replace(' Xbox Series X S Version', '')
                                game_name = game_name.replace(' Xbox One', '')
                                game_name = game_name.replace(' Windows Edition', '')
                                game_name = game_name.replace(' Game Preview', '')
                        except:
                            continue
                    
                    if not game_name or len(game_name) < 2:
                        continue
                    
                    game_name = self.clean_game_name(game_name)
                    
                    # If cleaned name is empty or too short, try extracting from URL again
                    if not game_name or len(game_name) < 2 or game_name.lower().strip() == 'store':
                        # Extract from URL slug
                        try:
                            if '/games/store/' in href:
                                game_slug = href.split('/games/store/')[1].split('/')[0].split('?')[0]
                                game_name = game_slug.replace('-', ' ').title()
                                # Clean up common suffixes
                                game_name = game_name.replace(' Xbox Series X S Version', '')
                                game_name = game_name.replace(' Xbox One', '')
                                game_name = game_name.replace(' Windows Edition', '')
                                game_name = game_name.replace(' Game Preview', '')
                                game_name = game_name.replace(' Standard Edition', '')
                                game_name = game_name.replace(' Console', '')
                        except:
                            continue
                    
                    if not game_name or len(game_name) < 2 or game_name.lower().strip() == 'store':
                        continue
                    
                    # Validate if it's a valid game
                    if game_name and len(game_name) >= 2:
                        # More lenient validation - just check basic filters
                        is_valid = self.is_valid_game(href, game_name)
                        if self.debug and not is_valid:
                            print(f"  Rejected: {game_name[:50]} - URL: {href[:80]}")
                        
                        if is_valid:
                            if game_name not in game_names:
                                game_info = {
                                    'name': game_name,
                                    'url': href,
                                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }
                                
                                # If filter_2025_only is enabled, get release date immediately
                                if self.filter_2025_only and self.rate_limiter:
                                    release_date = self.get_release_date_from_giantbomb(game_name)
                                    if release_date:
                                        game_info['release_date'] = release_date
                                        year = release_date.split('-')[0]
                                        if year == '2025':
                                            if self.debug:
                                                print(f"  Added: {game_name} - Release: {release_date} (2025)")
                                        else:
                                            if self.debug:
                                                print(f"  Skipped: {game_name} - Release: {release_date} (not 2025)")
                                            # Don't add if not 2025
                                            continue
                                    else:
                                        # No release date found, skip if filtering
                                        if self.debug:
                                            print(f"  Skipped: {game_name} - Release date not found")
                                        continue
                                else:
                                    if self.debug:
                                        print(f"  Added: {game_name}")
                                
                                self.games.append(game_info)
                                game_names.add(game_name)
                            
                except Exception as e:
                    continue
            
            print(f"Processed {processed_count} game URLs, skipped {skipped_count} non-game links")
            print(f"Games found so far: {len(self.games)}")
            
            # Debug: Show sample URLs if no games found
            if len(self.games) == 0 and processed_count > 0:
                print("\nDebug: Checking why no games were extracted...")
                sample_count = 0
                for element in games_found[:5]:  # Check first 5
                    try:
                        href = element.get_attribute('href')
                        if href and '/games/' in href:
                            print(f"  Sample URL: {href[:100]}")
                            sample_count += 1
                            if sample_count >= 3:
                                break
                    except:
                        pass
            
            # If still not enough games, try extracting from all links
            if len(self.games) < 20:
                print("Trying broader extraction method...")
                try:
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        try:
                            href = link.get_attribute('href')
                            # Only process game store URLs
                            if href and '/games/store/' in href and 'game-pass' not in href.lower():
                                # Check if URL has game ID
                                parts = href.split('/games/store/')
                                if len(parts) > 1:
                                    game_part = parts[1].split('?')[0].split('#')[0]
                                    if '/' in game_part:
                                        game_slug, game_id = game_part.split('/', 1)
                                        if 3 <= len(game_id) <= 60:
                                            text = link.text.strip()
                                            if not text or len(text) < 2:
                                                # Try extracting from URL
                                                text = game_slug.replace('-', ' ').title()
                                            else:
                                                text = self.clean_game_name(text)
                                            
                                            if text and len(text) >= 2 and self.is_valid_game(href, text):
                                                if text not in game_names:
                                                    game_info = {
                                                        'name': text,
                                                        'url': href,
                                                        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                                    }
                                                    
                                                    # If filter_2025_only is enabled, check release date
                                                    if self.filter_2025_only and self.rate_limiter:
                                                        release_date = self.get_release_date_from_giantbomb(text)
                                                        if release_date:
                                                            game_info['release_date'] = release_date
                                                            year = release_date.split('-')[0]
                                                            if year == '2025':
                                                                if self.debug:
                                                                    print(f"  Added: {text} - Release: {release_date} (2025)")
                                                            else:
                                                                if self.debug:
                                                                    print(f"  Skipped: {text} - Release: {release_date} (not 2025)")
                                                                # Don't add if not 2025
                                                                continue
                                                        else:
                                                            # No release date found, skip if filtering
                                                            if self.debug:
                                                                print(f"  Skipped: {text} - Release date not found")
                                                            continue
                                                    
                                                    self.games.append(game_info)
                                                    game_names.add(text)
                        except:
                            continue
                except Exception as e:
                    print(f"Broader extraction failed: {e}")
            
            # Remove duplicates based on URL and clean up names
            seen_urls = set()
            unique_games = []
            seen_names = set()
            
            for game in self.games:
                url_key = game['url'].split('?')[0] if game['url'] else game['name']
                
                # Skip if URL already seen
                if url_key in seen_urls:
                    continue
                
                # Clean up game name - remove "explore" prefix if present
                game_name = game['name']
                if game_name.lower().startswith('explore '):
                    game_name = game_name[8:].strip()
                    game['name'] = game_name
                
                # Skip if name is just "explore" or too short after cleaning
                if len(game_name) < 3:
                    continue
                
                # Skip if name is duplicate (case-insensitive)
                name_lower = game_name.lower().strip()
                if name_lower in seen_names:
                    continue
                
                # If filter_2025_only is enabled, ensure only 2025 games are included
                if self.filter_2025_only:
                    if 'release_date' not in game:
                        # No release date, skip it
                        continue
                    release_date = game.get('release_date')
                    if release_date:
                        year = release_date.split('-')[0]
                        if year != '2025':
                            # Not 2025, skip it
                            continue
                    else:
                        # Release date is None, skip it
                        continue
                
                seen_urls.add(url_key)
                seen_names.add(name_lower)
                unique_games.append(game)
            
            self.games = unique_games
            print(f"Total unique games extracted: {len(self.games)}")
            
        except Exception as e:
            print(f"Error extracting games: {e}")
            import traceback
            traceback.print_exc()
    
    def scrape(self):
        """Main scraping method"""
        try:
            self.setup_driver()
            
            url = "https://www.xbox.com/en-US/xbox-game-pass/games#all-games"
            print(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Try to close any popups or accept cookies
            try:
                # Look for cookie consent buttons
                cookie_selectors = [
                    "//button[contains(text(), 'Accept')]",
                    "//button[contains(text(), 'I Accept')]",
                    "//button[@id='acceptButton']",
                    "//button[contains(@class, 'cookie')]",
                ]
                
                for selector in cookie_selectors:
                    try:
                        button = self.driver.find_element(By.XPATH, selector)
                        if button.is_displayed():
                            button.click()
                            time.sleep(2)
                            break
                    except:
                        continue
            except:
                pass
            
            # Wait for games section to load
            time.sleep(3)
            
            # Scroll to load all games
            self.scroll_and_load_games()
            
            # Extract games from initial load
            self.extract_games()
            initial_game_count = len(self.games)
            print(f"Initial games extracted: {initial_game_count}")
            
            # Try to load more games by clicking pagination/load more buttons
            self.load_more_games(max_attempts=50)
            
            # Filter and sort games (if filter_2025_only is enabled)
            self.filter_and_sort_games()
            
            return self.games
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        finally:
            # Save cache before closing
            if self.filter_2025_only:
                self.save_cache()
            
            if self.driver:
                self.driver.quit()
                print("Browser closed")
    
    def load_cache(self):
        """Load release date cache from file"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.release_date_cache = json.load(f)
            if self.debug:
                print(f"Loaded {len(self.release_date_cache)} cached release dates")
        except FileNotFoundError:
            self.release_date_cache = {}
        except Exception as e:
            if self.debug:
                print(f"Error loading cache: {e}")
            self.release_date_cache = {}
    
    def save_cache(self):
        """Save release date cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.release_date_cache, f, indent=2, ensure_ascii=False)
            if self.debug:
                print(f"Saved {len(self.release_date_cache)} release dates to cache")
        except Exception as e:
            if self.debug:
                print(f"Error saving cache: {e}")
    
    def get_release_date_from_giantbomb(self, game_name):
        """
        Get release date from GiantBomb API (with caching)
        
        Args:
            game_name: Name of the game
            
        Returns:
            str: Release date in YYYY-MM-DD format, or None if not found
        """
        if not self.filter_2025_only or not self.rate_limiter:
            return None
        
        # Normalize game name for cache key (case-insensitive)
        cache_key = game_name.lower().strip()
        
        # Check cache first
        if cache_key in self.release_date_cache:
            cached_result = self.release_date_cache[cache_key]
            if self.debug:
                print(f"  Using cached release date for '{game_name}': {cached_result}")
            return cached_result
        
        try:
            # Wait for rate limit
            self.rate_limiter.wait_if_needed()
            
            # Search for game in GiantBomb API
            search_url = "https://www.giantbomb.com/api/search/"
            headers = {'User-Agent': 'GamePassReleaseChecker/1.0'}
            params = {
                "api_key": self.giantbomb_api_key,
                "format": "json",
                "query": game_name,
                "resources": "game",
                "limit": 1
            }
            
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            # Handle HTTP 420 (Enhance Your Calm) - wait 1 hour with retry loop
            max_420_retries = 3
            retry_count = 0
            while response.status_code == 420 and retry_count < max_420_retries:
                retry_count += 1
                print(f"\n⚠️  HTTP 420 received (Rate limit exceeded). Waiting 1 hour before retrying... (Attempt {retry_count}/{max_420_retries})")
                wait_time = 3600  # 1 hour in seconds
                wait_with_countdown(wait_time, "⏸️  Rate limit exceeded. Waiting 1 hour...")
                
                # Clear rate limiter requests to reset the counter
                with self.rate_limiter.lock:
                    self.rate_limiter.requests = []
                    self.rate_limiter.last_request_time = time.time()
                
                # Retry the request after waiting
                print("🔄 Retrying request after wait...")
                self.rate_limiter.wait_if_needed()
                response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            # If still 420 after max retries, raise error
            if response.status_code == 420:
                print(f"\n❌ HTTP 420 persists after {max_420_retries} retries. Giving up on this request.")
                raise requests.exceptions.HTTPError(f"HTTP 420 after {max_420_retries} retries")
            
            response.raise_for_status()
            
            data = response.json()
            
            release_date = None
            if data.get("number_of_total_results", 0) > 0:
                game = data["results"][0]
                release_date_raw = game.get("original_release_date")
                
                if release_date_raw:
                    # Parse date (format: YYYY-MM-DD HH:MM:SS)
                    try:
                        date_obj = datetime.strptime(release_date_raw.split()[0], "%Y-%m-%d")
                        release_date = date_obj.strftime("%Y-%m-%d")
                    except:
                        release_date = release_date_raw.split()[0] if release_date_raw else None
            
            # Save to cache (even if None, to avoid checking again)
            self.release_date_cache[cache_key] = release_date
            self.save_cache()
            
            return release_date
            
        except requests.exceptions.HTTPError as e:
            # Check if it's a 420 error (this should rarely happen now since we handle it before raise_for_status)
            if hasattr(e, 'response') and e.response and e.response.status_code == 420:
                print(f"\n⚠️  HTTP 420 received in exception handler (Rate limit exceeded). Waiting 1 hour before retrying...")
                wait_time = 3600  # 1 hour in seconds
                wait_with_countdown(wait_time, "⏸️  Rate limit exceeded. Waiting 1 hour...")
                
                # Clear rate limiter requests to reset the counter
                with self.rate_limiter.lock:
                    self.rate_limiter.requests = []
                    self.rate_limiter.last_request_time = time.time()
                
                # Retry the request after waiting
                try:
                    print("🔄 Retrying request after wait...")
                    self.rate_limiter.wait_if_needed()
                    response = requests.get(search_url, params=params, headers=headers, timeout=10)
                    
                    # Check if still 420
                    if response.status_code == 420:
                        print(f"\n❌ HTTP 420 persists after retry. Skipping this game.")
                        self.release_date_cache[cache_key] = None
                        self.save_cache()
                        return None
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    release_date = None
                    if data.get("number_of_total_results", 0) > 0:
                        game = data["results"][0]
                        release_date_raw = game.get("original_release_date")
                        
                        if release_date_raw:
                            try:
                                date_obj = datetime.strptime(release_date_raw.split()[0], "%Y-%m-%d")
                                release_date = date_obj.strftime("%Y-%m-%d")
                            except:
                                release_date = release_date_raw.split()[0] if release_date_raw else None
                    
                    print(f"✅ Successfully retrieved release date after retry: {release_date}")
                    self.release_date_cache[cache_key] = release_date
                    self.save_cache()
                    return release_date
                except Exception as retry_e:
                    print(f"❌ Retry after 420 failed for '{game_name}': {retry_e}")
                    self.release_date_cache[cache_key] = None
                    self.save_cache()
                    return None
            else:
                if self.debug:
                    print(f"  API error for '{game_name}': {e}")
                self.release_date_cache[cache_key] = None
                self.save_cache()
                return None
        except requests.exceptions.RequestException as e:
            if self.debug:
                print(f"  API error for '{game_name}': {e}")
            # Save None to cache to avoid retrying failed requests
            self.release_date_cache[cache_key] = None
            self.save_cache()
            return None
        except Exception as e:
            if self.debug:
                print(f"  Error getting release date for '{game_name}': {e}")
            # Save None to cache to avoid retrying failed requests
            self.release_date_cache[cache_key] = None
            self.save_cache()
            return None
    
    def filter_and_sort_games(self):
        """
        Sort games by release date descending (filtering already done during scraping)
        """
        if self.filter_2025_only:
            print("\n" + "="*50)
            print("Sorting games by release date...")
            print("="*50)
            
            # Games are already filtered during scraping, just sort by release date
            games_with_dates = [g for g in self.games if 'release_date' in g]
            games_without_dates = [g for g in self.games if 'release_date' not in g]
            
            print(f"Total games: {len(self.games)}")
            print(f"  - Games with release date: {len(games_with_dates)}")
            print(f"  - Games without release date: {len(games_without_dates)}")
            
            # Sort by release date descending
            self.games.sort(key=lambda x: x.get('release_date', ''), reverse=True)
            
            print(f"\n✓ Games sorted by release date (newest first)")
            
        else:
            # Just sort by name if no filtering
            self.games.sort(key=lambda x: x.get('name', ''))
    
    def save_to_json(self, filename='gamepass_games.json'):
        """Save games to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.games, f, indent=2, ensure_ascii=False)
            print(f"Games saved to {filename}")
        except Exception as e:
            print(f"Error saving to JSON: {e}")
    
    def save_to_csv(self, filename='gamepass_games.csv'):
        """Save games to CSV file"""
        try:
            if not self.games:
                print("No games to save")
                return
            
            # Determine fieldnames (include release_date if it exists)
            fieldnames = ['name', 'url', 'scraped_at']
            if self.games and 'release_date' in self.games[0]:
                fieldnames.insert(2, 'release_date')
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.games)
            print(f"Games saved to {filename}")
        except Exception as e:
            print(f"Error saving to CSV: {e}")


def main():
    """Main function"""
    print("=" * 50)
    print("Xbox Game Pass Games Scraper")
    print("=" * 50)
    
    # Configuration
    FILTER_2025_ONLY = True  # Set to True to only get games from 2025, False to get all games
    
    # Create scraper instance
    # Set headless=True to run without opening browser window
    # Set debug=True to see detailed logging (useful for troubleshooting)
    # Set filter_2025_only=True to only get games released in 2025 (requires GiantBomb API)
    scraper = GamePassScraper(
        headless=False, 
        debug=True,
        filter_2025_only=FILTER_2025_ONLY
    )
    
    # Scrape games
    games = scraper.scrape()
    
    if games:
        print(f"\nSuccessfully scraped {len(games)} games!")
        
        # Save to both JSON and CSV
        scraper.save_to_json()
        scraper.save_to_csv()
        
        # Print first few games as sample
        print("\nSample games (first 10):")
        for i, game in enumerate(games[:10], 1):
            print(f"{i}. {game['name']}")
    else:
        print("\nNo games were scraped. Please check the script and website structure.")
    
    print("\nScraping completed!")


if __name__ == "__main__":
    main()

