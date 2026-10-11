import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

def main():
    profile_dir = os.path.abspath("chrome_scraper_profile")
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--start-maximized")
    options.add_argument("--remote-allow-origins=*")

    driver = webdriver.Chrome(options=options)
    driver.get("https://contacts.google.com/u/2/directory")
    print("Waiting 5 seconds for page load...", flush=True)
    time.sleep(5)

    info = driver.execute_script("""
        const res = [];
        const elements = document.querySelectorAll('*');
        elements.forEach(el => {
            if (el.scrollHeight > el.clientHeight && el.clientHeight > 200) {
                res.push({
                    tag: el.tagName,
                    class: el.className,
                    role: el.getAttribute('role'),
                    scrollHeight: el.scrollHeight,
                    clientHeight: el.clientHeight,
                    scrollTop: el.scrollTop
                });
            }
        });
        return res;
    """)
    print("Scrollable containers found:", info, flush=True)

    try:
        rows = driver.find_elements(By.XPATH, "//*[@role='row' or @role='gridcell']")
        if rows:
            rows[0].click()
            print("Clicked first row to focus table!", flush=True)
            
        actions = ActionChains(driver)
        for i in range(15):
            actions.send_keys(Keys.PAGE_DOWN).perform()
            time.sleep(0.5)
            
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
        print(f"After 15 PAGE_DOWNs, found {len(emails)} emails in DOM: {emails[:10]}", flush=True)

    except Exception as e:
        print("Error:", e, flush=True)

    driver.quit()

if __name__ == "__main__":
    main()
