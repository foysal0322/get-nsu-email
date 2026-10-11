import os
import re
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

def clean_name(name, email):
    if not name:
        prefix = email.split("@")[0]
        clean_prefix = re.sub(r'\d+', '', prefix).strip("._- ")
        parts = [p.capitalize() for p in re.split(r'[._-]', clean_prefix) if p]
        return " ".join(parts) if parts else "Unknown"
    
    # Remove leading icons/numbers
    name = re.sub(r'^\s*\d{7,10}\s*', '', name)
    name = re.sub(r'^\s*[^a-zA-Z]+\s*', '', name).strip()
    return name or "Unknown"

def parse_contacts_from_html(html, sid):
    # Search for northsouth.edu emails in html
    matches = re.findall(r'["\']([a-zA-Z0-9._%+-]+@northsouth\.edu)["\']', html)
    unique_emails = set(m.lower() for m in matches)
    
    # Remove standard login user email if present
    unique_emails.discard("s.ahmed01@northsouth.edu")
    
    for email in unique_emails:
        # Check if email contains the student ID (or prefix)
        prefix = email.split('@')[0]
        # Attempt to find name in HTML near email
        idx = html.find(email)
        name = ""
        if idx != -1:
            snippet = html[max(0, idx - 300): idx]
            # Find quoted strings before email
            str_matches = re.findall(r'["\']([A-Z][a-zA-B\s.]{2,40})["\']', snippet)
            if str_matches:
                for candidate in reversed(str_matches):
                    if not any(kw in candidate.lower() for kw in ['google', 'account', 'directory', 'search', 'contact', 'http']):
                        name = candidate.strip()
                        break
        
        name = clean_name(name, email)
        return {"id": sid, "name": name, "email": email}
    
    return None

def main():
    profile_dir = os.path.abspath("chrome_scraper_profile")
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--headless=new")
    options.add_argument("--remote-allow-origins=*")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get("https://contacts.google.com/u/0/directory")
        time.sleep(3)
        
        # Test on 5 missing IDs
        with open("active_student_ids.json") as f:
            active_ids = json.load(f)
            
        with open("student_contacts.json") as f:
            existing = {item['id']: item for item in json.load(f)}
            
        missing_ids = [sid for sid in active_ids if sid not in existing]
        print(f"Total missing IDs to test: {len(missing_ids)}")
        
        test_ids = missing_ids[:5]
        for sid in test_ids:
            driver.get(f"https://contacts.google.com/u/0/search/{sid}")
            time.sleep(1.5)
            html = driver.page_source
            res = parse_contacts_from_html(html, sid)
            print(f"Result for ID {sid}: {res}")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
