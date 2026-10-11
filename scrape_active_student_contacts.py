import os
import re
import json
import time
from selenium import webdriver

def clean_name(name, email):
    if not name:
        prefix = email.split("@")[0]
        clean_prefix = re.sub(r'\d+', '', prefix).strip("._- ")
        parts = [p.capitalize() for p in re.split(r'[._-]', clean_prefix) if p]
        return " ".join(parts) if parts else "Unknown"
    
    name = re.sub(r'^\s*\d{7,10}\s*', '', name)
    name = re.sub(r'^\s*[^a-zA-Z]+\s*', '', name).strip()
    return name or "Unknown"

def parse_contacts_from_html(html, sid):
    matches = re.findall(r'["\']([a-zA-Z0-9._%+-]+@northsouth\.edu)["\']', html)
    unique_emails = set(m.lower() for m in matches)
    unique_emails.discard("s.ahmed01@northsouth.edu")
    
    for email in unique_emails:
        idx = html.find(email)
        name = ""
        if idx != -1:
            snippet = html[max(0, idx - 300): idx]
            str_matches = re.findall(r'["\']([A-Z][a-zA-B\s.]{2,40})["\']', snippet)
            if str_matches:
                for candidate in reversed(str_matches):
                    if not any(kw in candidate.lower() for kw in ['google', 'account', 'directory', 'search', 'contact', 'http', 'https']):
                        name = candidate.strip()
                        break
        
        name = clean_name(name, email)
        return {"id": sid, "name": name, "email": email}
    
    return None

def create_driver(profile_dir):
    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        lock_path = os.path.join(profile_dir, lock_name)
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except Exception:
                pass
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--headless=new")
    options.add_argument("--remote-allow-origins=*")
    options.set_capability("pageLoadStrategy", "none")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(15)
    driver.set_script_timeout(10)
    return driver

def main():
    profile_dir = os.path.abspath("chrome_scraper_profile")
    
    with open("active_student_ids.json", "r", encoding="utf-8") as f:
        active_ids = json.load(f)

    # Load existing student_contacts.json
    contacts_map = {}
    json_path = "student_contacts.json"
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                contacts_map[item['id']] = item

    checked_ids = set(contacts_map.keys())
    checked_file = "checked_student_ids.json"
    if os.path.exists(checked_file):
        try:
            with open(checked_file, "r", encoding="utf-8") as f:
                checked_ids.update(json.load(f))
        except Exception:
            pass

    missing_ids = [sid for sid in active_ids if sid not in checked_ids]
    print(f"Total active IDs: {len(active_ids)}")
    print(f"Captured contacts: {len(contacts_map)}")
    print(f"Remaining IDs to check: {len(missing_ids)}")

    if not missing_ids:
        print("All student IDs are fully processed!")
        return

    driver = None
    try:
        driver = create_driver(profile_dir)
        driver.get("https://contacts.google.com/u/0/directory")
        time.sleep(3)

        for idx, sid in enumerate(missing_ids):
            if driver is None:
                try:
                    driver = create_driver(profile_dir)
                    driver.get("https://contacts.google.com/u/0/directory")
                    time.sleep(3)
                except Exception as e:
                    print(f"Driver init error: {e}")
                    time.sleep(5)
                    continue

            try:
                res_json = driver.execute_async_script("""
                    const sid = arguments[0];
                    const callback = arguments[1];
                    fetch('/u/0/search/' + sid)
                        .then(r => r.text())
                        .then(html => callback({success: true, html: html}))
                        .catch(e => callback({success: false, error: e.message}));
                """, sid)

                checked_ids.add(sid)
                if res_json and res_json.get("success"):
                    parsed = parse_contacts_from_html(res_json["html"], sid)
                    if parsed:
                        contacts_map[sid] = parsed

                if (idx + 1) % 50 == 0 or (idx + 1) == len(missing_ids):
                    records = list(contacts_map.values())
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(records, f, indent=2, ensure_ascii=False)
                    with open("active_student_contacts.json", "w", encoding="utf-8") as f:
                        json.dump(records, f, indent=2, ensure_ascii=False)
                    with open(checked_file, "w", encoding="utf-8") as f:
                        json.dump(list(checked_ids), f, indent=2)
                    print(f"[{idx + 1}/{len(missing_ids)}] Checked. Total captured contacts: {len(contacts_map)}")

            except Exception as err:
                print(f"Error at ID {sid}: {err}. Resetting driver...")
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    driver = None
                time.sleep(2)

    finally:
        records = list(contacts_map.values())
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        with open("active_student_contacts.json", "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        with open(checked_file, "w", encoding="utf-8") as f:
            json.dump(list(checked_ids), f, indent=2)
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

if __name__ == "__main__":
    main()
