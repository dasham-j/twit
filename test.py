import time
import json
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()
DB_FILE = os.getenv("DB_FILE", "followers.json")


# Load cookies file path from .env
cookies_file = os.getenv("COOKIES_FILE")
if not cookies_file or not os.path.exists(cookies_file):
    print(f"❌ Cookies file '{cookies_file}' not found. Exiting.")
    exit()

# Load cookies from file
with open(cookies_file, "r") as f:
    raw_cookies = json.load(f)

def load_editthiscookie(raw_cookies):
    cookie_list = []
    for c in raw_cookies:
        cookie_list.append({
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"].lstrip("."),
            "path": c.get("path", "/"),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False),
            "expiry": c.get("expirationDate", None)
        })
    return cookie_list

def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = f.read().strip()
            if not data:
                return []
            db = json.loads(data)
            return db.get("usernames", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_db(usernames):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"usernames": list(usernames)}, f, indent=2)

# Setup Chrome
options = uc.ChromeOptions()
options.headless = True
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36')

driver = uc.Chrome(driver_executable_path=ChromeDriverManager().install(), options=options, headless=True)

# Open site and inject cookies
driver.get("https://x.com")
for cookie in load_editthiscookie(raw_cookies):
    try:
        driver.add_cookie(cookie)
    except Exception as e:
        print(f"❌ Cookie error: {e}")

driver.get("https://x.com/_vivienneluv/followers")

# Wait for container
wait = WebDriverWait(driver, 20)
container = wait.until(
    EC.presence_of_element_located((By.XPATH, '//div[@class="css-175oi2r" and contains(@aria-label, "Timeline: Followers")]'))
)

def fol(existing_usernames):
    usernames = []
    seen = set()
    scroll_attempts = 0
    max_scrolls = 1

    time.sleep(0.5)
    last_height = driver.execute_script("return arguments[0].scrollHeight", container)

    while scroll_attempts < max_scrolls:
        try:
            spans = container.find_elements(By.CSS_SELECTOR, 'span.css-1jxf684.r-bcqeeo.r-1ttztb7.r-qvutc0.r-poiln3')
            for span in spans:
                text = span.text.strip()
                if text.startswith("@") and text not in seen:
                    usernames.append(text)
                    seen.add(text)

            driver.execute_script("window.scrollBy(0, 3000);")
            time.sleep(0.2)

            new_height = driver.execute_script("return arguments[0].scrollHeight", container)
            if new_height == last_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_height = new_height

        except Exception as e:
            print("⚠️ Error during scroll:", e)
            break

    new_usernames = [u for u in usernames if u not in existing_usernames]
    if new_usernames:
        print(f"\n🆕 New usernames found: {len(new_usernames)}")
        for u in new_usernames:
            print(u)
    else:
        print("\n🔁 No new usernames found.")

    updated_usernames = new_usernames + existing_usernames
    seen = set()
    final_list = []
    for u in updated_usernames:
        if u not in seen:
            final_list.append(u)
            seen.add(u)

    return final_list

def get_top_username(container):
    try:
        spans = container.find_elements(By.CSS_SELECTOR, 'span.css-1jxf684.r-bcqeeo.r-1ttztb7.r-qvutc0.r-poiln3')
        for span in spans:
            text = span.text.strip()
            if text.startswith("@"):
                return text
        return ""
    except Exception as e:
        print(f"⚠️ Error getting top username: {e}")
        return ""

# 🔁 Main loop start
print("🚀 Script started. Monitoring top username every 10 seconds...\n")
all_usernames = load_db()
top_username_live = get_top_username(container)
print(f"🔼 Live (Current) Top Username: {top_username_live}")
top_username_saved = all_usernames[0] if all_usernames else ""
print(f"📦 Saved (Previous) Top Username: {top_username_saved}")

if not all_usernames or (top_username_live and top_username_live != top_username_saved):
    print("🔁 Top username changed or DB empty. Running scrape...")
    scraped_usernames = fol(all_usernames)
    new_usernames = [u for u in scraped_usernames if u not in all_usernames]
    updated_usernames = new_usernames + [u for u in all_usernames if u not in new_usernames]
    save_db(updated_usernames)
    all_usernames = updated_usernames
    previous_top = top_username_live
    print(f"✅ Updated DB. New top username: {all_usernames[0]}")
else:
    print("⏸️ No change in top username. Skipping scrape.")
    previous_top = top_username_live

while True:
    try:
        time.sleep(5)
        driver.get("https://x.com/_vivienneluv/followers")
        time.sleep(1)

        container = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//div[@class="css-175oi2r" and contains(@aria-label, "Timeline: Followers")]'))
        )

        current_top = get_top_username(container)
        print(f"🔼 Live (Current) Top Username: {repr(current_top)}")

        if all_usernames:
            print(f"📂 DB Top Username: {all_usernames[0]}")

        if current_top and current_top != previous_top:
            print("🔄 Change detected! Fetching updated usernames...")
            all_usernames = fol(all_usernames)
            save_db(all_usernames)
            previous_top = current_top
        else:
            print("⏸️ No change. Waiting...")

    except KeyboardInterrupt:
        print("\n🛑 Script stopped manually.")
        break
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
