import time
import json
import csv
import os
import re
import string
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

EMAIL = "s.ahmed01@northsouth.edu"
PASS = "Faisal@hmed03#"

ICON_KEYWORDS = {
    "drag_indicator", "more_vert", "check_box_outline_blank", 
    "person", "star_border", "star", "expand_more", "expand_less", 
    "edit", "delete", "checkbox", "unknown", "search results"
}

def clean_name(name, email):
    if not name or name.lower().strip() in ICON_KEYWORDS:
        prefix = email.split("@")[0]
        clean_prefix = re.sub(r'\d+', '', prefix).strip("._- ")
        parts = [p.capitalize() for p in re.split(r'[._-]', clean_prefix) if p]
        if parts:
            return " ".join(parts)
        return "Unknown"
    
    for icon in ICON_KEYWORDS:
        if name.lower().startswith(icon):
            name = name[len(icon):].strip()
            
    name = re.sub(r'^[^a-zA-Z]+', '', name).strip()
    return name or "Unknown"

def login_google(driver):
    print("Checking sign-in status...", flush=True)
    driver.get("https://contacts.google.com/u/2/directory")
    time.sleep(4)
    
    if "signin" in driver.current_url.lower() or "accounts.google.com" in driver.current_url.lower():
        print("Sign-in required. Submitting email credential...", flush=True)
        try:
            email_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='email' or @id='identifierId']"))
            )
            email_field.clear()
            email_field.send_keys(EMAIL)
            time.sleep(1)
            
            try:
                next_btn = driver.find_element(By.XPATH, "//button[contains(.,'Next') or @id='identifierNext']")
                next_btn.click()
            except Exception:
                email_field.send_keys("\n")
                
            print("Email submitted. Waiting for password field...", flush=True)
            time.sleep(4)
            
            password_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='password' or @name='Passwd']"))
            )
            password_field.clear()
            password_field.send_keys(PASS)
            time.sleep(1)
            
            try:
                pwd_next = driver.find_element(By.XPATH, "//button[contains(.,'Next') or @id='passwordNext']")
                pwd_next.click()
            except Exception:
                password_field.send_keys("\n")
                
            print("Password submitted. Waiting for login verification...", flush=True)
            time.sleep(6)
        except Exception as e:
            print(f"Login automation notice: {e}", flush=True)

def extract_dom_contacts(driver):
    return driver.execute_script("""
        const items = [];
        const icons = new Set([
            'drag_indicator', 'more_vert', 'check_box_outline_blank', 
            'person', 'star_border', 'star', 'expand_more', 'expand_less', 
            'edit', 'delete', 'checkbox', 'search results'
        ]);
        
        const nodes = document.querySelectorAll('div, tr, li, [role="row"], [role="gridcell"], td');
        nodes.forEach(n => {
            const txt = n.innerText || "";
            if (txt.includes('@') && txt.length < 350) {
                const m = txt.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/);
                if (m) {
                    const email = m[0].toLowerCase().trim();
                    const parts = txt.split('\\n').map(p => p.trim()).filter(p => {
                        const low = p.toLowerCase();
                        return p && !low.includes(email) && !icons.has(low);
                    });
                    
                    let name = parts.length > 0 ? parts[0] : '';
                    name = name.replace(/^[^a-zA-Z0-9.\\s]+/, '').trim();
                    if (email && email.includes('.')) {
                        items.push({ name: name, email: email });
                    }
                }
            }
        });
        return items;
    """)

def scroll_page(driver):
    try:
        driver.execute_script("""
            const containers = document.querySelectorAll('.My2mLb, .QkOsze, .nvy7uf, [role="main"]');
            containers.forEach(el => { el.scrollTop += 1500; });
            window.scrollBy(0, 1500);
        """)
        time.sleep(0.6)
    except Exception:
        pass

def save(contacts):
    records = list(contacts.values())
    if not records:
        return
        
    json_file = "nsu_directory_contacts.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        
    csv_file = "nsu_directory_contacts.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "email"])
        writer.writeheader()
        writer.writerows(records)

def main():
    letters = string.ascii_lowercase
    id_prefixes = [str(y).zfill(2) + str(s) + str(d) for y in range(5, 27) for s in range(1, 4) for d in range(0, 10)]
    three_char_prefixes = [c1 + c2 + c3 for c1 in letters for c2 in letters for c3 in letters]
    prefixes = id_prefixes + three_char_prefixes
    
    checkpoint_file = "scrape_checkpoint.json"
    contacts = {}
    if os.path.exists("nsu_directory_contacts.json"):
        try:
            with open("nsu_directory_contacts.json", "r", encoding="utf-8") as f:
                existing = json.load(f)
                for item in existing:
                    em = item.get("email", "").lower().strip()
                    nm = clean_name(item.get("name", ""), em)
                    if em:
                        contacts[em] = {"name": nm, "email": em}
            print(f"Loaded {len(contacts)} pre-existing records.", flush=True)
        except Exception as e:
            print(f"Pre-existing load warning: {e}", flush=True)
            
    while True:
        start_idx = 0
        if os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, "r") as f:
                    ckpt = json.load(f)
                    start_idx = ckpt.get("idx", 0)
            except Exception:
                pass
                
        if start_idx >= len(prefixes):
            print(f"Extraction fully complete across all {len(prefixes)} queries! Final unique count: {len(contacts)}", flush=True)
            break
            
        print(f"Resuming search queue ({start_idx}/{len(prefixes)})...", flush=True)
        
        # Clean locks
        profile_dir = os.path.abspath("chrome_scraper_profile")
        for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
            lock_path = os.path.join(profile_dir, lock_name)
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                except Exception:
                    pass
                    
        driver = None
        current_idx = start_idx
        try:
            options = webdriver.ChromeOptions()
            options.add_argument(f"--user-data-dir={profile_dir}")
            options.add_argument("--start-maximized")
            options.add_argument("--remote-allow-origins=*")
            options.add_experimental_option("detach", True)
            
            driver = webdriver.Chrome(options=options)
            login_google(driver)
            
            while current_idx < len(prefixes):
                prefix = prefixes[current_idx]
                url = f"https://contacts.google.com/u/2/search/{prefix}"
                
                try:
                    driver.get(url)
                    time.sleep(1.5)
                except Exception as net_err:
                    print(f"Navigation error at '{prefix}': {net_err}. Resetting session...", flush=True)
                    break
                    
                added_this_prefix = 0
                for step in range(4):
                    data = extract_dom_contacts(driver)
                    for entry in data:
                        e = entry['email']
                        n = clean_name(entry['name'], e)
                        if e not in contacts:
                            contacts[e] = {"name": n, "email": e}
                            added_this_prefix += 1
                    scroll_page(driver)
                    
                current_idx += 1
                
                with open(checkpoint_file, "w") as f:
                    json.dump({"idx": current_idx}, f)
                    
                if added_this_prefix > 0:
                    print(f"[{current_idx}/{len(prefixes)}] Prefix '{prefix}': +{added_this_prefix} new (Total unique: {len(contacts)})", flush=True)
                    save(contacts)
                elif current_idx % 50 == 0:
                    print(f"[{current_idx}/{len(prefixes)}] Prefix '{prefix}': 0 new (Total unique: {len(contacts)})", flush=True)
                    
        except Exception as err:
            print(f"Session error at index {current_idx}: {err}. Resetting browser in 3s...", flush=True)
            time.sleep(3)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            save(contacts)

if __name__ == "__main__":
    main()
