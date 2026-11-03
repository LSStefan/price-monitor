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

def is_valid_match(title: str, query: str) -> bool:
    """Verifica daca TOATE cuvintele din cautare se regasesc in titlul produsului."""
    query_words = query.lower().split()
    title_lower = title.lower()
    
    for word in query_words:
        if word not in title_lower:
            return False
    return True

def auto_find_product_url(context: BrowserContext, store_key: str, product_name: str) -> str | None:
    config = SEARCH_CONFIGS.get(store_key)
    if not config:
        return None
        
    encoded_query = quote_plus(product_name)
    search_url = config["search_url"].format(query=encoded_query)
    page = context.new_page()
    
    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        
        # Cazul 1: Redirectionare directa (am nimerit direct pe produs)
        if page.url != search_url and "/search/" not in page.url and "/cauta/" not in page.url:
            return page.url
            
        # Cazul 2: Lista de rezultate
        page.wait_for_selector(config["first_product_link"], timeout=10000)
        
        # Luam primele 5 rezultate de pe pagina
        links = page.locator(config["first_product_link"]).all()
        
        best_link = None
        for link in links[:5]:
            title_text = link.inner_text().strip()
            if not title_text:
                continue
                
            # Verificam daca titlul contine ce am cautat
            if is_valid_match(title_text, product_name):
                print(f"       [DEBUG] Potrivire validata pe {store_key}: {title_text}")
                best_link = link
                break
                
        if best_link:
            best_link.click()
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            return page.url
        else:
            print(f"       [INFO] Niciunul din primele 5 rezultate nu contine exact '{product_name}'.")
            return None
            
    except Exception as e:
        print(f"       [EROARE Cautare {store_key}]: {e}")
        return None
    finally:
        page.close()