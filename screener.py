import yfinance as yf
import pandas as pd
import json
import datetime

# --- 1. FONCTIONS DE RÉCUPÉRATION DYNAMIQUE DES TICKERS ---
# Ces fonctions extraient les tickers de Wikipédia (Méthode la plus efficace et gratuite)

def get_sp500_tickers():
    try:
        df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        return df['Symbol'].tolist()
    except:
        return []

def get_nasdaq100_tickers():
    try:
        df = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4] 
        return df['Symbol'].tolist()
    except:
        return []

def get_cac40_tickers():
    try:
        df = pd.read_html('https://en.wikipedia.org/wiki/CAC_40')[4]
        tickers = df['Ticker'].tolist()
        return [t + ".PA" for t in tickers]
    except:
        return []

def get_dax_tickers():
    try:
        df = pd.read_html('https://en.wikipedia.org/wiki/DAX')[4]
        tickers = df['Ticker'].tolist()
        return [t if ".DE" in t else t + ".DE" for t in tickers]
    except:
        return []

def get_ftse100_tickers():
    try:
        df = pd.read_html('https://en.wikipedia.org/wiki/FTSE_100_Index')[4]
        tickers = df['Ticker'].tolist()
        return [t + ".L" for t in tickers]
    except:
        return []

asia_pacific_manual = [
    # JAPON, CHINE/HK, CANADA, AUSTRALIE (Ajoutez ici si besoin)
    "7203.T", "6758.T", "9984.T", "0700.HK", "9988.HK", "RY.TO", "BHP.AX"
]

def get_all_global_tickers():
    all_tickers = []
    all_tickers.extend(get_sp500_tickers())
    all_tickers.extend(get_nasdaq100_tickers())
    all_tickers.extend(get_cac40_tickers())
    all_tickers.extend(get_dax_tickers())
    all_tickers.extend(get_ftse100_tickers())
    all_tickers.extend(asia_pacific_manual)
    
    clean_tickers = list(set([t.replace('.', '-') if "PA" not in t and "DE" not in t else t for t in all_tickers]))
    return clean_tickers

# --- 2. ANALYSE PRINCIPALE AVEC ROE ---

def run_analysis():
    print("--- Démarrage du Screener Mondial (P/E & ROE) ---")
    tickers = get_all_global_tickers()
    undervalued_stocks = []
    
    # Limite de scan pour rester dans la durée d'exécution gratuite de GitHub (1000 actions, environ 10-15 min)
    limit_scan = 1000 
    tickers_to_scan = tickers[:limit_scan]
    print(f"Total actions à scanner : {len(tickers_to_scan)}")

    for i, ticker in enumerate(tickers_to_scan):
        if i % 100 == 0:
            print(f"Progression : {i}/{len(tickers_to_scan)}")

        try:
            stock = yf.Ticker(ticker)
            
            # Récupération rapide du prix
            try:
                price = stock.fast_info.last_price
            except:
                continue

            # Récupération des données fondamentales
            info = stock.info
            pe = info.get('trailingPE')
            roe = info.get('returnOnEquity') # Le ROE est souvent un float (ex: 0.18 pour 18%)
            
            # --- STRATÉGIE DE SÉLECTION BUFFETT MODERNE ---
            
            # 1. Critère Bas Prix (Valeur pure à la Ben Graham)
            cond_cheap = (pe is not None and 0 < pe < 15)
            
            # 2. Critère Qualité/Prix (Buffett/Munger)
            # P/E entre 15 et 25 ET ROE > 15%
            cond_quality = (pe is not None and 15 <= pe < 25 and roe is not None and roe > 0.15)
            
            if cond_cheap or cond_quality:
                name = info.get('longName', ticker)
                sector = info.get('sector', 'N/A')
                currency = info.get('currency', 'USD')
                tag = "Sous-évalué" if cond_cheap else "Qualité/Prix"
                
                print(f"✅ TROUVÉ {ticker}: {tag} (P/E: {pe:.2f} | ROE: {roe*100:.2f}%)")
                
                undervalued_stocks.append({
                    "symbol": ticker,
                    "name": name,
                    "sector": sector,
                    "pe": round(pe, 2),
                    "roe": round(roe * 100, 2) if roe else 0,
                    "price": round(price, 2),
                    "currency": currency,
                    "tag": tag
                })

        except Exception as e:
            # print(f"Erreur sur {ticker}: {e}")
            continue
            
    undervalued_stocks.sort(key=lambda x: x['pe'])
    
    final_data = {
        "last_updated": datetime.datetime.utcnow().strftime("%d/%m/%Y à %H:%M GMT"),
        "count": len(undervalued_stocks),
        "data": undervalued_stocks
    }

    with open("data.json", "w") as f:
        json.dump(final_data, f)
    
    print("--- Analyse terminée. Fichier data.json généré. ---")

if __name__ == "__main__":
    run_analysis()
