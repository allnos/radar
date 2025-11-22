import yfinance as yf
import pandas as pd
import json
import datetime
import sys

# --- BUFFETT FILTERS & CRITERIA ---

# Secteurs typiquement évités par Buffett (trop complexe, trop volatile, trop cyclique)
EXCLUDED_SECTORS = [
    'Technology', 'Biotechnology', 'Basic Materials', 'Energy', 
    'Oil & Gas', 'Mining', 'Semiconductors', 'Aerospace & Defense', 
    'Capital Goods', 'Industrials' 
]


# --- FONCTION UTILITAIRE DE SÉCURITÉ ---
def get_safe_float(info, key, reject_value):
    """Récupère une valeur et garantit qu'elle est un float. Sinon, renvoie une valeur de rejet."""
    val = info.get(key)
    try:
        # Tente de convertir en float. Si réussi, renvoie la valeur.
        return float(val) if val is not None else reject_value
    except (ValueError, TypeError):
        # Si la conversion échoue (ex: valeur non-numérique), renvoie la valeur de rejet.
        return reject_value

# --- 1. FONCTIONS DE RÉCUPÉRATION DYNAMIQUE DES TICKERS (Inchangées) ---
# (Ces fonctions restent inchangées et ne sont pas répétées ici pour la clarté, 
# mais elles doivent être présentes dans votre fichier final)

def get_sp500_tickers():
    """Récupère le S&P 500 (USA) et corrige le format des tickers pour yfinance."""
    try:
        print("Récupération S&P 500 (USA)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        return [t.replace('.', '-') for t in df['Symbol'].tolist()]
    except:
        return []

def get_nasdaq100_tickers():
    """Récupère le NASDAQ 100 (USA) et corrige le format des tickers pour yfinance."""
    try:
        print("Récupération NASDAQ 100 (USA)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
        col_name = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
        return [t.replace('.', '-') for t in df[col_name].tolist()]
    except:
        return []

def get_cac40_tickers():
    """Récupère le CAC 40 (France)"""
    try:
        print("Récupération CAC 40 (France)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/CAC_40')[4]
        return [t + ".PA" for t in df['Ticker'].tolist()]
    except:
        return []

def get_dax_tickers():
    """Récupère le DAX (Allemagne)"""
    try:
        print("Récupération DAX (Allemagne)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/DAX')[4]
        return [t if ".DE" in t else t + ".DE" for t in df['Ticker'].tolist()]
    except:
        return []

def get_ftse100_tickers():
    """Récupère le FTSE 100 (Royaume-Uni)"""
    try:
        print("Récupération FTSE 100 (UK)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/FTSE_100_Index')[4]
        return [t + ".L" for t in df['Ticker'].tolist()]
    except:
        return []

def get_major_europe_japan_manual():
    """Liste manuelle des leaders pour la couverture des bourses difficiles à scraper"""
    print("Ajout des leaders Japonais, Suisses, Canadiens, etc. (Liste manuelle)...")
    return [
        "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "9432.T", "7974.T", 
        "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ZURN.SW",
        "FER.MI", "ENI.MI", "ISP.MI", "ENEL.MI", 
        "ITX.MC", "IBE.MC",
        "RY.TO", "TD.TO", "ENB.TO",
        "0700.HK", "9988.HK", "1299.HK",
        "BHP.AX", "CBA.AX", "CSL.AX"
    ]


def get_all_global_tickers():
    """Agrège toutes les listes pour le scan mondial"""
    all_tickers = []
    all_tickers.extend(get_sp500_tickers())
    all_tickers.extend(get_nasdaq100_tickers())
    all_tickers.extend(get_cac40_tickers())
    all_tickers.extend(get_dax_tickers())
    all_tickers.extend(get_ftse100_tickers())
    all_tickers.extend(get_major_europe_japan_manual())

    clean_tickers = list(set(all_tickers))
    return clean_tickers


# --- 2. ANALYSE PRINCIPALE (4 Critères Fondamentaux) ---

def run_analysis():
    print("--- Démarrage du Screener Buffet (4 Critères Fondamentaux + Exclusion de Secteur) ---")
    tickers = get_all_global_tickers()
    
    limit_scan = 1500
    tickers_to_scan = tickers[:limit_scan]
    
    undervalued_stocks = []
    print(f"Total actions à scanner : {len(tickers_to_scan)}")

    for i, ticker in enumerate(tickers_to_scan):
        if i % 100 == 0:
            print(f"Progression : {i}/{len(tickers_to_scan)} - {ticker}")

        try:
            stock = yf.Ticker(ticker)

            try:
                price = stock.fast_info.last_price
            except:
                continue 

            info = stock.info
            
            # 1. Vérification du Secteur (Critère Qualitatif de Simplicité)
            sector = info.get('sector', 'N/A')
            if sector in EXCLUDED_SECTORS:
                # print(f"DEBUG: {ticker} - Secteur {sector} exclu.")
                continue

            # 2. Récupération des Ratios (Sécurisée)
            pe_val = get_safe_float(info, 'trailingPE', reject_value=9999.0)
            roe_val = get_safe_float(info, 'returnOnEquity', reject_value=-1.0)
            gpm_val = get_safe_float(info, 'grossMargins', reject_value=-1.0)
            
            # Ratio Dette/Capitaux Propres (D/E)
            total_debt = get_safe_float(info, 'totalDebt', reject_value=0.0)
            total_equity = get_safe_float(info, 'totalStockholderEquity', reject_value=-1.0)
            
            if total_equity > 0:
                de_val = total_debt / total_equity
            else:
                # Si capitaux propres négatifs ou nuls, le ratio échoue
                de_val = 9999.0 

            # --- APPLICATION DES FILTRES BUFFETT ---
            
            # F1: P/E < 15.0 (Prix)
            is_pe_ok = (0.0 < pe_val < 15.0)
            
            # F2: ROE > 15% (Qualité)
            is_roe_ok = (roe_val > 0.15)
            
            # F3: Marge Brute (GPM) > 20% (Pouvoir de Fixation des Prix / Moat)
            is_gpm_ok = (gpm_val > 0.20)
            
            # F4: Dette/Capitaux Propres (D/E) < 1.0 (Sécurité / Dette gérable)
            is_de_ok = (de_val < 1.0)
            
            # Ligne de DÉBOGAGE CRITIQUE : Vérifiez vos logs GitHub Action !
            # print(f"DEBUG: {ticker} - P/E:{is_pe_ok}, ROE:{is_roe_ok}, GPM:{is_gpm_ok}, D/E:{is_de_ok}")

            # --- ENREGISTREMENT FINAL ---
            if is_pe_ok and is_roe_ok and is_gpm_ok and is_de_ok:
                
                name = info.get('longName', ticker)
                currency = info.get('currency', 'USD')
                tag = "Valeur d'Or"

                print(f"💰 VALEUR D'OR TROUVÉE: {ticker} - {name} (P/E: {pe_val:.2f}, ROE: {roe_val*100:.2f}%)")

                undervalued_stocks.append({
                    "symbol": ticker,
                    "name": name,
                    "sector": sector,
                    "pe": round(pe_val, 2),
                    "roe": round(roe_val * 100, 2),
                    "gpm": round(gpm_val * 100, 2),
                    "de_ratio": round(de_val, 2),
                    "price": round(price, 2),
                    "currency": currency,
                    "tag": tag
                })
        
        except Exception as e:
            # print(f"Erreur pour {ticker}: {e}")
            continue
            
    # Tri par P/E croissant
    undervalued_stocks.sort(key=lambda x: x['pe'])
    
    final_data = {
        "last_updated": datetime.datetime.utcnow().strftime("%d/%m/%Y à %H:%M GMT"),
        "count": len(undervalued_stocks),
        "data": undervalued_stocks
    }

    with open("data.json", "w") as f:
        json.dump(final_data, f)
    
    print("--- ANALSE COMPLÈTE. Résultat :", len(undervalued_stocks), "actions trouvées. ---")

if __name__ == "__main__":
    run_analysis()
