import yfinance as yf
import pandas as pd
import json
import datetime
import time

# --- 1. FONCTIONS DE RÉCUPÉRATION DYNAMIQUE DES TICKERS (Scraping Wikipedia) ---

def get_sp500_tickers():
    """Récupère le S&P 500 (USA)"""
    try:
        print("Récupération S&P 500 (USA)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        # Correction du format (ex: BRK.B -> BRK-B)
        return [t.replace('.', '-') for t in df['Symbol'].tolist()]
    except:
        return []

def get_nasdaq100_tickers():
    """Récupère le NASDAQ 100 (USA)"""
    try:
        print("Récupération NASDAQ 100 (USA)...")
        # Le tableau est souvent à l'index 4
        df = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4] 
        return df['Ticker'].tolist()
    except:
        return []

def get_cac40_tickers():
    """Récupère le CAC 40 (France)"""
    try:
        print("Récupération CAC 40 (France)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/CAC_40')[4]
        # Ajout du suffixe .PA pour Yahoo Finance
        return [t + ".PA" for t in df['Ticker'].tolist()]
    except:
        return []

def get_dax_tickers():
    """Récupère le DAX (Allemagne)"""
    try:
        print("Récupération DAX (Allemagne)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/DAX')[4]
        # Ajout du suffixe .DE si manquant
        return [t if ".DE" in t else t + ".DE" for t in df['Ticker'].tolist()]
    except:
        return []

def get_ftse100_tickers():
    """Récupère le FTSE 100 (Royaume-Uni)"""
    try:
        print("Récupération FTSE 100 (UK)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/FTSE_100_Index')[4]
        # Ajout du suffixe .L pour Londres
        return [t + ".L" for t in df['Ticker'].tolist()]
    except:
        return []

def get_major_europe_japan_manual():
    """Liste manuelle des leaders (Japon, Suisse, Italie, etc.)"""
    print("Ajout des leaders Japonais, Suisses, Canadiens, etc. (Liste manuelle)...")
    return [
        # JAPON (Leaders)
        "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "9432.T", "7974.T", 
        # SUISSE (SMI Leaders)
        "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ZURN.SW",
        # ITALIE (FTSE Leaders)
        "FER.MI", "ENI.MI", "ISP.MI", "ENEL.MI", 
        # ESPAGNE
        "ITX.MC", "IBE.MC",
        # CANADA
        "RY.TO", "TD.TO", "ENB.TO", 
        # CHINE / HK
        "0700.HK", "9988.HK", "1299.HK",
        # AUSTRALIE
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
    
    # Nettoyage : on enlève les doublons
    clean_tickers = list(set(all_tickers))
    return clean_tickers

# --- 2. ANALYSE PRINCIPALE (Critères Warren Buffett) ---

def run_analysis():
    print("--- CONSTRUCTION DE LA LISTE MONDIALE ---")
    tickers = get_all_global_tickers()
    
    # Limite de scan fixée à 1500 pour respecter le temps d'exécution (6h max) de GitHub
    limit_scan = 1500 
    tickers = tickers[:limit_scan]
    print(f"Total actions à analyser (limité à {limit_scan}): {len(tickers)}")
    
    undervalued_stocks = []
    print(f"Démarrage du scan sur {len(tickers)} titres...")
    
    for i, ticker in enumerate(tickers):
        # Affichage de la progression pour le débug dans GitHub Actions
        if i % 100 == 0:
            print(f"Progression : {i}/{len(tickers)} - {ticker}")

        try:
            stock = yf.Ticker(ticker)
            
            # Filtre rapide : si pas de prix, l'action est ignorée
            try:
                price = stock.fast_info.last_price
            except:
                continue

            # Récupération des données lourdes
            info = stock.info
            pe = info.get('trailingPE')
            roe = info.get('returnOnEquity', 0)
            
            # --- STRATÉGIE WARREN BUFFETT ---
            # Critère 1 : P/E < 15 (Sous-évalué / La Marge de sécurité de Graham)
            cond_cheap = (pe is not None and 0 < pe < 15)
            
            # Critère 2 : P/E 15-25 MAIS ROE > 15% (Qualité/Prix / Le Moat de Munger)
            cond_quality = (pe is not None and 15 <= pe < 25 and roe is not None and roe > 0.15)
            
            if cond_cheap or cond_quality:
                name = info.get('longName', ticker)
                sector = info.get('sector', 'N/A')
                currency = info.get('currency', 'USD')
                tag = "Sous-évalué" if cond_cheap else "Qualité/Prix"
                
                print(f"✅ TROUVÉ: {ticker} - {name} ({tag}, P/E: {pe:.2f})")
                
                # --- CORRECTION ROE : ENREGISTRÉ EN POURCENTAGE ---
                undervalued_stocks.append({
                    "symbol": ticker,
                    "name": name,
                    "sector": sector,
                    "pe": round(pe, 2),
                    "roe": round(roe * 100, 2) if roe else 0, # ENREGISTRE LE ROE EN % AVEC 2 DÉCIMALES
                    "price": round(price, 2),
                    "currency": currency,
                    "tag": tag
                })
        
        except Exception:
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
