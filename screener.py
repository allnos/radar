import yfinance as yf
import pandas as pd
import json
import datetime

# --- 1. FONCTIONS DE RÉCUPÉRATION DYNAMIQUE DES TICKERS (Scraping Wikipedia) ---

def get_sp500_tickers():
    """Récupère le S&P 500 (USA) et corrige le format des tickers pour yfinance."""
    try:
        print("Récupération S&P 500 (USA)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        # Correction du format (ex: BRK.B -> BRK-B)
        return [t.replace('.', '-') for t in df['Symbol'].tolist()]
    except:
        return []

def get_nasdaq100_tickers():
    """Récupère le NASDAQ 100 (USA) et corrige le format des tickers pour yfinance."""
    try:
        print("Récupération NASDAQ 100 (USA)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
        col_name = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
        # Correction du format (ex: Ticker.A -> Ticker-A)
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

    # Nettoyage final : simple suppression des doublons
    clean_tickers = list(set(all_tickers))
    return clean_tickers

# --- 2. ANALYSE PRINCIPALE (Critère Strict: P/E < 15 ET ROE > 15%) ---

def run_analysis():
    print("--- Démarrage du Screener Mondial (P/E < 15 ET ROE > 15%) ---")
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
                continue # Skip si le prix n'est pas disponible

            # Récupération des données fondamentales
            info = stock.info
            pe = info.get('trailingPE')
            # Ne pas utiliser de valeur par défaut ici, car 'None' est plus clair que 0 pour le filtre
            roe = info.get('returnOnEquity') 

            # --- FILTRE STRICT : P/E < 15 ---
            
            # Étape 1 : Vérification stricte du P/E (Prix)
            # Doit être disponible, strictement positif, et STRICTEMENT inférieur à 15.
            if pe is None or pe <= 0 or pe >= 15:
                continue # P/E non conforme, on passe au suivant.
                
            # --- FILTRE STRICT : ROE > 15% ---

            # Étape 2 : Vérification stricte du ROE (Qualité)
            # Doit être disponible (non None) et STRICTEMENT supérieur à 0.15 (15%).
            if roe is None or roe <= 0.15:
                continue # ROE non conforme, on passe au suivant.

            # --- Si le code atteint ce point, les deux conditions sont remplies ---
            
            name = info.get('longName', ticker)
            sector = info.get('sector', 'N/A')
            currency = info.get('currency', 'USD')
            tag = "Valeur d'Or"

            print(f"💰 VALEUR D'OR TROUVÉE: {ticker} - {name} (P/E: {pe:.2f}, ROE: {roe*100:.2f}%)")

            undervalued_stocks.append({
                "symbol": ticker,
                "name": name,
                "sector": sector,
                "pe": round(pe, 2),
                # Conversion du ROE en
