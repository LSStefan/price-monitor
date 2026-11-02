from playwright.sync_api import sync_playwright
from database import init_db, SessionLocal, Product, ProductListing, PriceHistory
from scraper import scrape_product_price, get_store_info, auto_find_product_url, SEARCH_CONFIGS

def get_browser_context(playwright_instance):
    browser = playwright_instance.chromium.launch(headless=False, slow_mo=50)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080}
    )
    return browser, context

def add_product_auto(db):
    print("\n--- ADAUGARE PRODUS (CAUTARE AUTOMATA) ---")
    name = input("Introdu numele exact al produsului (ex: Ryzen 7 7800X3D): ").strip()
    if not name:
        print("[EROARE] Numele nu poate fi gol.")
        return
        
    try:
        target_price = float(input("Introdu pretul tinta in RON (ex: 1800): ").strip())
    except ValueError:
        print("[EROARE] Pretul trebuie sa fie un numar valid.")
        return

    new_product = Product(name=name, target_price=target_price)
    db.add(new_product)
    db.commit()

    print(f"\n[SEARCH] Cautam automat '{name}' pe magazinele suportate...")
    with sync_playwright() as p:
        browser, context = get_browser_context(p)
        
        for store_name in SEARCH_CONFIGS.keys():
            print(f" -> Cautam pe [{store_name}]...")
            found_url = auto_find_product_url(context, store_name, name)
            
            if found_url:
                print(f"    [GASIT] {found_url}")
                listing = ProductListing(
                    product_id=new_product.id,
                    store_name=store_name,
                    url=found_url
                )
                db.add(listing)
                db.commit()
            else:
                print(f"    [ INFO ] Nu am gasit un rezultat clar pe {store_name}.")
                
        browser.close()
    print(f"[SUCCES] Produsul '{name}' a fost salvat in baza de date!")

def add_product_manual(db):
    print("\n--- ADAUGARE PRODUS (LINKURI MANUALE) ---")
    name = input("Introdu numele produsului: ").strip()
    try:
        target_price = float(input("Introdu pretul tinta (RON): ").strip())
    except ValueError:
        print("[EROARE] Pret invalid.")
        return

    new_product = Product(name=name, target_price=target_price)
    db.add(new_product)
    db.commit()

    print("Introdu linkurile produsului (lasa gol si apasa Enter cand ai terminat):")
    while True:
        url = input("URL magazin (sau Enter pentru iesire): ").strip()
        if not url:
            break
        try:
            store_name, _ = get_store_info(url)
            listing = ProductListing(product_id=new_product.id, store_name=store_name, url=url)
            db.add(listing)
            db.commit()
            print(f"   [OK] Link adaugat pentru magazinul [{store_name}].")
        except Exception as e:
            print(f"   [EROARE] {e}")

def run_comparator(db):
    products = db.query(Product).all()
    if not products:
        print("\n[INFO] Nu ai niciun produs in baza de date. Foloseste optiunea 1 sau 2 mai intai!")
        return

    print(f"\n[START] Analizam cea mai buna oferta pentru {len(products)} produse...\n")
    
    with sync_playwright() as p:
        browser, context = get_browser_context(p)
        
        for product in products:
            print("=" * 60)
            print(f"PRODUS: {product.name} (Tinta: {product.target_price} RON)")
            print("=" * 60)
            
            current_offers = []
            for listing in product.listings:
                print(f" -> Verificam [{listing.store_name}]...")
                try:
                    price = scrape_product_price(context, listing.url)
                    
                    history_entry = PriceHistory(listing_id=listing.id, price=price)
                    db.add(history_entry)
                    db.commit()
                    
                    current_offers.append({
                        "store": listing.store_name,
                        "price": price,
                        "url": listing.url
                    })
                    print(f"    Pret: {price:.2f} RON")
                except Exception as e:
                    print(f"    [EROARE] Eroare pe {listing.store_name}: {e}")
            
            if current_offers:
                current_offers.sort(key=lambda x: x["price"])
                best = current_offers[0]
                
                print("\n--- CLASAMENT OFERTE ---")
                print(f"[CASTIGATOR] Cel mai ieftin este la {best['store']}: {best['price']:.2f} RON")
                print(f"             Link: {best['url']}")
                
                if len(current_offers) > 1:
                    second = current_offers[1]
                    diff = second["price"] - best["price"]
                    print(f"[ECONOMIE] Economisesti {diff:.2f} RON fata de {second['store']} ({second['price']:.2f} RON)")
                
                if best["price"] <= product.target_price:
                    print(f"[ALERTA] Pretul ({best['price']:.2f} RON) este SUB tinta ta de {product.target_price} RON!")
                else:
                    diff_target = best["price"] - product.target_price
                    print(f"[INFO] Mai trebuie sa scada cu {diff_target:.2f} RON pana la tinta.")
            else:
                print("\n[EROARE] Nicio oferta nu a putut fi extrasa.")
            print("\n")
            
        browser.close()

def delete_product(db):
    products = db.query(Product).all()
    if not products:
        print("\n[INFO] Baza de date este goala.")
        return
        
    print("\n--- PRODUSE SALVATE ---")
    for p in products:
        print(f"ID: {p.id} | {p.name} (Tinta: {p.target_price} RON) - {len(p.listings)} magazine")
        
    try:
        prod_id = int(input("\nIntrodu ID-ul produsului pe care vrei sa il stergi (sau 0 pt anulare): "))
        if prod_id == 0:
            return
        prod = db.query(Product).filter(Product.id == prod_id).first()
        if prod:
            db.delete(prod)
            db.commit()
            print(f"[SUCCES] Produsul '{prod.name}' a fost sters.")
        else:
            print("[EROARE] ID inexistent.")
    except ValueError:
        print("[EROARE] Introdu un numar valid.")

def afiseaza_date(db):
    produse = db.query(Product).all()
    
    for p in produse:
        print(f"\n==========================================")
        print(f"PRODUS: {p.name} | Pret Tinta: {p.target_price} RON")
        print(f"==========================================")
        for l in p.listings:
            print(f"  Magazin: [{l.store_name}] -> {l.url}")
            for h in l.history:
                data_f = h.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                print(f"     * {h.price:.2f} RON ({data_f} UTC)")

def main_menu():
    init_db()
    db = SessionLocal()
    
    while True:
        print("\n================ PRICE COMPARATOR CLI ================")
        print("1. Adauga produs nou (Cautare Automata pe magazine)")
        print("2. Adauga produs nou (Introducere manuala de linkuri)")
        print("3. Ruleaza comparatorul pentru produsele salvate")
        print("4. Sterge un produs din baza de date")
        print("5. Afiseaza produsele si istoricul preturilor")
        print("0. Iesire")
        print("======================================================")
        
        choice = input("Alege o optiune (0-4): ").strip()
        
        if choice == "1":
            add_product_auto(db)
        elif choice == "2":
            add_product_manual(db)
        elif choice == "3":
            run_comparator(db)
        elif choice == "4":
            delete_product(db)
        elif choice == "5":
            from view_db import afiseaza_date
            afiseaza_date()
        elif choice == "0":
            print("La revedere!")
            break
        else:
            print("[EROARE] Optiune invalida.")
            
    db.close()

if __name__ == "__main__":
    main_menu()