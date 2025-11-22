import yfinance as yf
import pandas as pd
import json
import datetime
import sys
from concurrent.futures import ThreadPoolExecutor

# --- FILTRES ET CRITÈRES BUFFETT ---

# Secteurs exclus (Qualitatif)
EXCLUDED_SECTORS = [
    'Technology', 'Biotechnology', 'Basic Materials', 'Energy', 
    'Oil & Gas', 'Mining', 'Semiconductors', 'Aerospace & Defense', 
    'Capital Goods', 'Industrials', 'Real Estate', 'Telecommunication Services' 
]

# Secteurs exemptés du critère strict de Dette (Banques, Utilities)
EXEMPTED_DEBT_SECTORS = ['Financial Services', 'Utilities']

# --- 1. FONCTIONS ROBUSTES DE CALCUL DES RATIOS ---

def get_safe_float(info, key, reject_value):
    val = info.get(key)
    try:
        return float(val) if val is not None else reject_value
    except:
        return reject_value

def calculate_roe(stock):
    """Calcule le ROE via les états financiers."""
    try:
        financials = stock.financials
        balance = stock.balance_sheet
        if financials.empty or balance.empty: return -1.0
        
        net_income = financials.loc['Net Income'].iloc[0]
        equity = balance.loc['Total Stockholder Equity'].iloc[0]
        return net_income / equity if equity > 0 else -1.0
    except:
        return -1.0

def calculate_gpm(stock):
    """Calcule la Marge Brute."""
    try:
        financials = stock.financials
        if financials.empty: return -1.0
        
        gross_profit = financials.loc['Gross Profit'].iloc[0]
        revenue = financials.loc['Total Revenue'].iloc[0]
        return gross_profit / revenue if revenue > 0 else -1.0
    except:
        return -1.0

def calculate_de_ratio(stock):
    """Calcule le ratio Dette/Capitaux Propres."""
    try:
        balance = stock.balance_sheet
        if balance.empty: raise ValueError
        
        # Tente de trouver les clés exactes ou utilise info comme fallback
        debt = balance.loc['Total Debt'].iloc[0] if 'Total Debt' in balance.index else get_safe_float(stock.info, 'totalDebt', 0.0)
        equity = balance.loc['Total Stockholder Equity'].iloc[0] if 'Total Stockholder Equity' in balance.index else get_safe_float(stock.info, 'totalStockholderEquity', -1.0)
        
        return debt / equity if equity > 0 else 9999.0
    except:
        # Fallback complet sur .info
        debt = get_safe_float(stock.info, 'totalDebt', 0.0)
        equity = get_safe_float(stock.info, 'totalStockholderEquity', -1.0)
        return debt / equity if equity > 0 else 9999.0

# --- 2. RÉCUPÉRATION WIKIPEDIA ROBUSTE ---

def get_tickers_from_wiki(url, table_index, col_names, suffix=""):
    try:
        dfs = pd.read_html(url, header=0)
        if not dfs or len(dfs) <= table_index: return []
        df = dfs[table_index]
        
        # Cherche la bonne colonne
        target_col = next((c for c in col_names if c in df.columns), None)
        if target_col:
            return [str(t).replace('.', '-') + suffix for t in df[target_col].tolist() if pd.notna(t)]
        return []
    except:
        return []

def get_all_global_tickers():
    print("--- Récupération des Tickers Mondiaux ---")
    tickers = []
    # USA
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0, ['Symbol']))
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/Nasdaq-100', 4, ['Symbol', 'Ticker']))
    # Europe
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/CAC_40', 4, ['Ticker'], ".PA"))
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/DAX', 4, ['Ticker'], ".DE"))
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/FTSE_100_Index', 4, ['Ticker'], ".L"))
    # Manuel (Asie/Canada/Suisse)
    tickers.extend(["7203.T", "6758.T", "9984.T", "NESN.SW", "NOVN.SW", "ROG.SW", "RY.TO", "TD.TO", "ENB.TO", "BHP.AX", "CBA.AX", "0700.HK", "9988.HK"])
    
    return list(set(tickers))

# --- 3. ANALYSE ---

def process_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info: return None

        # Vérif Prix
        price = get_safe_float(info, 'currentPrice', 0.0)
        if price <= 0: price = get_safe_float(info, 'regularMarketPrice', 0.0)
        if price <= 0: return None

        # 1. Secteur
        sector = info.get('sector', 'N/A')
        if sector in EXCLUDED_SECTORS: return None

        # 2. Ratios
        pe = get_safe_float(info, 'trailingPE', 9999.0)
        roe = calculate_roe(stock)
        gpm = calculate_gpm(stock)
        de = calculate_de_ratio(stock)

        # 3. Filtres
        ok_pe = (0 < pe < 15)
        ok_roe = (roe > 0.15)
        ok_gpm = (gpm > 0.20)
        ok_de = (de < 1.0) or (sector in EXEMPTED_DEBT_SECTORS)

        if ok_pe and ok_roe and ok_gpm and ok_de:
            name = info.get('longName', ticker)
            currency = info.get('currency', 'USD')
            tag = "Valeur d'Or"
            if sector in EXEMPTED_DEBT_SECTORS: tag += f" (Dette: {sector})"
            
            return
