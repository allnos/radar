import yfinance as yf
import pandas as pd
import json
import datetime
import time

# --- 1. FONCTIONS DE RÉCUPÉRATION DYNAMIQUE DES TICKERS ---

def get_sp500_tickers():
    try:
        print("Récupération S&P 500 (USA)...")
        # Lit le premier tableau de la page Wikipedia S&P 500
        df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        return df['Symbol'].tolist()
    except:
        return []

def get_nasdaq100_tickers():
    try:
        print("Récupération NASDAQ 100 (USA)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4] # Le tableau est souvent le 5ème (index 4)
        return df['Symbol'].tolist()
    except:
        return []

def get_cac40_tickers():
    try:
        print("Récupération CAC 40 (France)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/CAC_40')[4]
        # Sur Wiki, les tickers n'ont pas le .PA, on l'ajoute
        tickers = df['Ticker'].tolist()
        return [t + ".PA" for t in tickers]
    except:
        # Fallback manuel si Wiki change de format
        return ["OR.PA", "MC.PA", "TTE.PA", "SAN.PA", "AIR.PA", "BNP.PA"]

def get_dax_tickers():
    try:
        print("Récupération DAX (Allemagne)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/DAX')[4]
        tickers = df['Ticker'].tolist()
        return [t if ".DE" in t else t + ".DE" for t in tickers]
    except:
        return ["SAP.DE", "SIE.DE", "VOW3.DE"]

def get_ftse100_tickers():
    try:
        print("Récupération FTSE 100 (Royaume-Uni)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/FTSE_100_Index')[4]
        tickers = df['Ticker'].tolist()
        # Yahoo demande .L pour Londres
        return [t + ".L" for t in tickers]
    except:
        return ["SHEL.L", "HSBA.L", "BP.L"]

# --- LISTE ASIE & RESTE DU MONDE (MANUELLE CAR DIFFICILE À SCRAPER) ---
asia_pacific_manual = [
    # JAPON (Nikkei Leaders)
    "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "9432.T", "7974.T", 
    # CHINE / HK
    "0700.HK", "9988.HK", "0939.HK", "1299.HK", "0941.HK", "3690.HK", 
    # CANADA
    "RY.TO", "TD.TO", "ENB.TO", "CNR.TO", "CP.TO",
    # AUSTRALIE
    "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX"
]

def get_all_global_tickers():
    """Agrège toutes les listes"""
    all_tickers = []
    all_tickers.extend(get_sp500_tickers())
    all_tickers.extend(get_nasdaq100_tickers())
    all_tickers.extend(get_cac40_tickers())
    all_tickers.extend(get_dax_tickers())
    all_tickers.extend(get_ftse100_tickers())
    all_tickers.extend(asia_pacific_manual)
    
    # Nettoyage : on enlève les doublons et on corrige les formats (BRK.B -> BRK-B)
    clean_tickers = list(set([t.replace('.', '-') if "PA" not in t and "DE" not in t else t for t in all_tickers]))
    return clean_tickers

# --- 2. ANALYSE PRINCIPALE ---

def run_analysis():
    # 1. Récupération de la Master List
    print("--- CONSTRUCTION DE LA LISTE MONDIALE ---")
    tickers = get_all_global_tickers()
    print(f"Total actions trouvées à analyser : {len(tickers)}")
    
    undervalued_stocks = []
    
    # Pour éviter de faire planter Yahoo, on analyse par paquets de 100
    # et on limite à 1500 actions max pour respecter le temps GitHub gratuit (6h max)
    # Si vous voulez tout scanner, augmentez limit_scan
    limit_scan = 1500 
    tickers = tickers[:limit_scan]

    print(f"Démarrage du scan sur {len(tickers)} titres...")
    
    for i, ticker in enumerate(tickers):
        # Petit log pour voir l'avancement dans GitHub Actions
        if i % 50 == 0:
            print(f"Progression : {i}/{len(tickers)}")

        try:
            stock = yf.Ticker(ticker)
            
            # Filtre rapide sur le prix (si pas de prix, l'action est morte/suspendue)
            try:
                price = stock.fast_info.last_price
            except:
                continue

            # Récupération données lourdes
            info = stock.info
            pe = info.get('trailingPE')
            roe = info.get('returnOnEquity', 0)
            
            # --- STRATÉGIE WARREN BUFFETT ---
            # Critère 1 : P/E < 15 (Pas cher)
            cond_cheap = (pe is not None and 0 < pe < 15)
            
            # Critère 2 : P/E 15-25 MAIS ROE > 15% (Qualité)
            cond_quality = (pe is not None and 15 <= pe < 25 and roe is not None and roe > 0.15)
            
            if cond_cheap or cond_quality:
                name = info.get('longName', ticker)
                sector = info.get('sector', 'N/A')
                currency = info.get('currency', 'USD')
                tag = "Sous-évalué" if cond_cheap else "Qualité"
                
                print(f"✅ {ticker}: {tag} (P/E: {pe})")
                
                undervalued_stocks.append({
                    "symbol": ticker,
                    "name": name,
                    "sector": sector,
                    "pe": round(pe, 2),
                    "price": round(price, 2),
                    "currency": currency,
                    "tag": tag
                })

        except Exception:
            continue
            
    # Tri final
    undervalued_stocks.sort(key=lambda x: x['pe'])
    
    final_data = {
        "last_updated": datetime.datetime.utcnow().strftime("%d/%m/%Y à %H:%M GMT"),
        "count": len(undervalued_stocks),
        "data": undervalued_stocks
    }

    with open("data.json", "w") as f:
        json.dump(final_data, f)
    
    print("--- Terminé ---")

if __name__ == "__main__":
    run_analysis()
