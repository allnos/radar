import yfinance as yf
import pandas as pd
import json
import datetime

# --- 1. FONCTIONS DE RÉCUPÉRATION DYNAMIQUE DES TICKERS (Scraping Wikipedia) ---

def get_sp500_tickers():
    """Récupère le S&P 500 (USA)"""
    try:
        print("Récupération S&P 500 (USA)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        return [t.replace('.', '-') for t in df['Symbol'].tolist()]
    except:
        return []

def get_nasdaq100_tickers():
    """Récupère le NASDAQ 100 (USA)"""
    try:
        print("Récupération NASDAQ 100 (USA)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
        col_name = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
        return df[col_name].tolist()
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

    # Nettoyage final des formats et suppression des doublons
    clean_tickers = list(set([t.replace('.', '-') if len(t.split('.')) <= 1 or t.endswith(('.TO', '.AX', '.HK', '.SW', '.MI', '.MC', '.AS')) else t for t in all_tickers]))
    
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
                continue

            # Récupération des données fondamentales
            info = stock.info
            pe = info.get('trailingPE')
            # Le ROE est un float (ex: 0.18 pour 18%). On utilise 0 par défaut.
            roe = info.get('returnOnEquity', 0) 

            # --- STRATÉGIE DE SÉLECTION STRICTE : QUALITÉ + PRIX BAS ---
            
            # P/E doit être inférieur à 15 ET ROE doit être supérieur à 15% (0.15)
            cond_strict_buffett = (pe is not None and 0 < pe < 15 and roe > 0.15)
            
            if cond_strict_buffett: 
                name = info.get('longName', ticker)
                sector = info.get('sector', 'N/A')
                currency = info.get('currency', 'USD')
                # Tag unique pour ce filtre très strict
                tag = "Valeur d'Or"

                print(f"💰 VALEUR D'OR TROUVÉE: {ticker} - {name} (P/E: {pe:.2f}, ROE: {roe*100:.2f}%)")

                undervalued_stocks.append({
                    "symbol": ticker,
                    "name": name,
                    "sector": sector,
                    "pe": round(pe, 2),
                    # On stocke le ROE en pourcentage pour l'affichage HTML
