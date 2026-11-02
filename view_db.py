from database import SessionLocal, Product

def afiseaza_date():
    db = SessionLocal()
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
    db.close()

if __name__ == "__main__":
    afiseaza_date()