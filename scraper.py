from playwright.sync_api import BrowserContext
from urllib.parse import urlparse, quote_plus
import re

STORE_SELECTORS = {
    "pcgarage.ro": ".price_num",
    "emag.ro": ".product-new-price",
    "altex.ro": ".Price-int",
    "mediagalaxy.ro": ".Price-int",
    "flanco.ro": ".special-price .price"
}

SEARCH_CONFIGS = {
    "PCGARAGE": {
        "search_url": "https://www.pcgarage.ro/cauta/{query}",
        "first_product_link": ".product_box_name a"
    },
    "EMAG": {
        "search_url": "https://www.emag.ro/search/{query}",
        "first_product_link": "a.card-v2-title"
    }
}

def get_store_info(url: str) -> tuple[str, str]:
    domain = urlparse(url).netloc.lower()
    for store_domain, selector in STORE_SELECTORS.items():
        if store_domain in domain:
            store_name = store_domain.split('.')[0].upper()
            return store_name, selector
    raise ValueError(f"Magazinul din URL-ul '{domain}' nu este suportat!")

def clean_price(price_text: str) -> float:
    first_line = price_text.strip().split('\n')[0]
    clean_text = re.sub(r'[^\d.,]', '', first_line)
    
    if ',' in clean_text and '.' in clean_text:
        clean_text = clean_text.replace('.', '').replace(',', '.')
    elif ',' in clean_text:
        clean_text = clean_text.replace(',', '.')
    return float(clean_text)

def scrape_product_price(context: BrowserContext, url: str) -> float:
    _, selector = get_store_info(url)
    page = context.new_page()
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector(selector, timeout=15000)
        
        raw_price = page.locator(selector).first.inner_text()
        return clean_price(raw_price)
    finally:
        page.close()

def auto_find_product_url(context: BrowserContext, store_key: str, product_name: str) -> str | None:
    config = SEARCH_CONFIGS.get(store_key)
    if not config:
        return None
        
    encoded_query = quote_plus(product_name)
    search_url = config["search_url"].format(query=encoded_query)
    page = context.new_page()
    
    try:
        # Intram pe pagina de cautare
        page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        
        # Daca magazinul ne-a redirectionat direct pe produs
        if page.url != search_url and "/search/" not in page.url and "/cauta/" not in page.url:
            return page.url
            
        # Asteptam sa apara lista de rezultate
        page.wait_for_selector(config["first_product_link"], timeout=10000)
        
        # DAM CLICK pe primul rezultat
        print(f"       [DEBUG] Accesam pagina primului produs de pe {store_key}...")
        page.locator(config["first_product_link"]).first.click()
        
        # Asteptam sa se incarce pagina noului produs
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        
        return page.url
    except Exception as e:
        print(f"       [EROARE Cautare {store_key}]: {e}")
        return None
    finally:
        page.close()