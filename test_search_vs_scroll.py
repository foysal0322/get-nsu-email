import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def main():
    profile_dir = os.path.abspath("chrome_scraper_profile")
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--start-maximized")
    options.add_argument("--remote-allow-origins=*")

    driver = webdriver.Chrome(options=options)
    driver.get("https://contacts.google.com/u/2/directory")
    print("Waiting 4 seconds for page load...", flush=True)
    time.sleep(4)

    search_inputs = driver.find_elements(By.XPATH, "//input[@aria-label='Search' or @type='text' or contains(@placeholder, 'Search')]")
    print(f"Search inputs found: {len(search_inputs)}", flush=True)

    if search_inputs:
        inp = search_inputs[0]
        inp.click()
        time.sleep(1)
        inp.clear()
        inp.send_keys("b")
        inp.send_keys(Keys.ENTER)
        print("Searched for 'b'...", flush=True)
        time.sleep(4)
        
        emails = driver.execute_script("""
            const set = new Set();
            document.querySelectorAll('*').forEach(n => {
                const txt = n.innerText || "";
                if (txt.includes('@') && txt.length < 300) {
                    const m = txt.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/);
                    if (m) set.add(m[0].toLowerCase());
                }
            });
            return Array.from(set);
        """)
        print(f"After searching 'b', found {len(emails)} emails in DOM: {emails[:10]}", flush=True)

    driver.quit()

if __name__ == "__main__":
    main()
