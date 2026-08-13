import json
from playwright.sync_api import sync_playwright
import time

def get_links():
    url = "https://groww.in/mutual-funds/filter?fund_house=%5B%22HDFC+Mutual+Fund%22%5D"
    results = []
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Scroll down to load more funds
        for _ in range(15):
            page.mouse.wheel(0, 1500)
            time.sleep(1.5)
            
        elements = page.query_selector_all("a[href^='/mutual-funds/hdfc']")
        
        for el in elements:
            href = el.get_attribute("href")
            title_el = el.query_selector(".fs14") or el.query_selector("div.truncate")
            if not title_el:
                title_el = el # fallback
            
            title = el.inner_text().split("\n")[0].strip()
            
            if href and title and "hdfc" in href.lower():
                full_url = "https://groww.in" + href
                if full_url not in [r["source_url"] for r in results]:
                    results.append({
                        "id": "groww_" + href.split("/")[-1].replace("-", "_"),
                        "source_url": full_url,
                        "source_name": "Groww - " + title,
                        "scheme": title,
                        "amc": "HDFC Mutual Fund",
                        "doc_type": "scheme_page",
                        "content_type": "html_dynamic"
                    })
                    
            if len(results) >= 30:
                break
                
        browser.close()
        
    print(json.dumps(results[:30], indent=2))

if __name__ == "__main__":
    get_links()
