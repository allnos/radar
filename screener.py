import yfinance as yf
import pandas as pd
import json
import datetime
import sys
import requests
import traceback
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

# --- 1. FONCTIONS DE CALCUL ET DE SÉCURITÉ ---

def get_safe_float(info, key, reject_value):
    val = info.get(key)
    try:
        return float(val) if val is not None else reject_value
    except:
        return reject_value

def calculate_roe(stock):
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
    try:
        financials = stock.financials
        if financials.empty: return -1.0
        
        gross_profit = financials.loc['Gross Profit'].iloc[0]
        revenue = financials.loc['Total Revenue'].iloc[0]
        return gross_profit / revenue if revenue > 0 else -1.0
    except:
        return -1.0

def calculate_de_ratio(stock):
    try:
        balance = stock.balance_sheet
        if balance.empty: raise ValueError
        
        debt = balance.loc['Total Debt'].iloc[0] if 'Total Debt' in balance.index else get_safe_float(stock.info, 'totalDebt', 0.0)
        equity = balance.loc['Total Stockholder Equity'].iloc[0] if 'Total Stockholder Equity' in balance.index else get_safe_float(stock.info, 'totalStockholderEquity', -1.0)
        
        return debt / equity if equity > 0 else 9999.0
    except:
        debt = get_safe_float(stock.info, 'totalDebt', 0.0)
        equity = get_safe_float(stock.info, 'totalStockholderEquity', -1.0)
        return debt / equity if equity > 0 else 9999.0

# --- 2. RÉCUPÉRATION WIKIPEDIA (VERSION ANTI-BOT) ---

def get_tickers_from_wiki(url, table_index, col_names, suffix=""):
    """Utilise requests avec un User-Agent pour éviter l'erreur 403 Forbidden."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        r = requests.get(url, headers=headers)
        r.raise_for_status() 
        
        dfs = pd.read_html(r.text, header=0)
        if not dfs or len(dfs) <= table_index: return []
        df = dfs[table_index]
        
        target_col = next((c for c in col_names if c in df.columns), None)
        if target_col:
            tickers = [str(t).replace('.', '-') + suffix for t in df[target_col].tolist() if pd.notna(t)]
            return tickers
        return []
    except Exception as e:
        return []

def get_all_global_tickers():
    print("--- Récupération des Tickers Mondiaux ---")
    tickers = []
    
    # USA
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0, ['Symbol']))
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/Nasdaq-100', 4, ['Symbol', 'Ticker']))
    # Russell 2000 (Pour plus de couverture US)
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/Russell_2000_Index', 1, ['Company'], ""))

    # Europe
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/CAC_40', 4, ['Ticker'], ".PA"))
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/DAX', 4, ['Ticker'], ".DE"))
    tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/FTSE_100_Index', 4, ['Ticker'], ".L"))
    
    # Liste Manuelle / Autres
    manual_list = ["7203.T", "6758.T", "9984.T", "NESN.SW", "NOVN.SW", "ROG.SW", "RY.TO", "TD.TO", "ENB.TO", "BHP.
