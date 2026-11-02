from playwright.sync_api import BrowserContext
from urllib.parse import urlparse, quote_plus
import re

# Configuratia pentru extragerea pretului de pe pagina produsului
STORE_SELECTORS = {
    "pcgarage.ro": ".price_num",
    "vexio.ro": "#price-value",
    "altex.ro": ".Price-int",
    "mediagalaxy.ro": ".Price-int",
    "flanco.ro": ".special-price .price",
    "emag.ro": ".product-new-price"
}

# Configuratia pentru cautarea automata (bara de search a fiecarui magazin)
SEARCH_CONFIGS = {
    "PCGARAGE": {
        "search_url": "https://www.pcgarage.ro/cauta/{query}",
        "first_product_link": ".product_box_name a"
    },
    "VEXIO": {
        "search_url": "https://www.vexio.ro/?sn.q={query}",
        "first_product_link": "h2.name a"
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
    """Cauta automat produsul pe magazin si returneaza URL-ul primului rezultat."""
    config = SEARCH_CONFIGS.get(store_key)
    if not config:
        return None
        
    encoded_query = quote_plus(product_name)
    search_url = config["search_url"].format(query=encoded_query)
    page = context.new_page()
    
    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        
        # Daca magazinul ne redirectioneaza direct pe pagina produsului
        if page.url != search_url and "/cauta/" not in page.url and "sn.q=" not in page.url:
            return page.url
            
        # Altfel, asteptam lista de rezultate si luam primul produs
        page.wait_for_selector(config["first_product_link"], timeout=10000)
        first_link = page.locator(config["first_product_link"]).first.get_attribute("href")
        
        if first_link and first_link.startswith("/"):
            parsed = urlparse(search_url)
            first_link = f"{parsed.scheme}://{parsed.netloc}{first_link}"
            
        return first_link
    except Exception:
        return None
    finally:
        page.close()