import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    metadata_path = Path("data/metadata.json")
    
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    existing_urls = {item["source_url"] for item in metadata}
    
    url = "https://groww.in/mutual-funds/filter"
    new_entries = []
    
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            for _ in range(10):
                page.mouse.wheel(0, 1500)
                time.sleep(1)
                
            elements = page.query_selector_all("a[href^='/mutual-funds/']")
            
            for el in elements:
                href = el.get_attribute("href")
                title = el.inner_text().split("\n")[0].strip()
                
                if href and title:
                    full_url = "https://groww.in" + href
                    if full_url not in existing_urls and full_url not in [e["source_url"] for e in new_entries]:
                        new_entries.append({
                            "id": "groww_" + href.split("/")[-1].replace("-", "_"),
                            "source_url": full_url,
                            "source_name": "Groww - " + title,
                            "scheme": title,
                            "amc": title.split(" ")[0] + " Mutual Fund",
                            "doc_type": "scheme_page",
                            "content_type": "html_dynamic"
                        })
                        
                if len(metadata) + len(new_entries) >= 25:
                    break
                    
            browser.close()
    except Exception as e:
        print(f"Failed to scrape new funds, continuing with existing funds. Error: {e}")
        
    metadata.extend(new_entries)
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"Added {len(new_entries)} new entries. Total entries: {len(metadata)}")

if __name__ == "__main__":
    main()
