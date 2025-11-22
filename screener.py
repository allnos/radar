import yfinance as yf
import pandas as pd
import json
import datetime
import sys
from concurrent.futures import ThreadPoolExecutor

# --- FILTRES ET CRITÈRES BUFFETT ---

# Secteurs exclus (Qualitatif) : Trop cycliques, complexes ou à forte intensité capitalistique.
EXCLUDED_SECTORS = [
    'Technology', 'Biotechnology', 'Basic Materials', 'Energy', 
    'Oil & Gas', 'Mining', 'Semiconductors', 'Aerospace & Defense', 
    'Capital Goods', 'Industrials', 'Real Estate', 'Telecommunication Services' 
]

# Secteurs exemptés du critère strict de Dette/Capitaux Propres (D/E < 1.0).
EXEMPTED_DEBT_SECTORS = ['Financial Services', 'Utilities']


# --- 1. FONCTIONS ROBUSTES DE CALCUL DES RATIOS ---

def get_safe_float(info, key, reject_value):
    """Récupère une valeur de manière sécurisée ou renvoie une valeur de rejet."""
    val = info.get(key)
    try:
        return float(val) if val is not None else reject_value
    except (ValueError, TypeError):
        return reject_value

def calculate_roe(stock):
    """Calcule le Return on Equity (ROE). Vérifie l'existence des données."""
    try:
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        if financials.empty or balance_sheet.empty:
            return -1.0 # Échec
            
        net_income = financials.loc['Net Income'].iloc[0]
        total_equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0]
        
        if total_equity > 0:
            return net_income / total_equity
        return -1.0 
    except KeyError:
        # Index manquant dans les données financières
        return -1.0
    except Exception:
        return -1.0

def calculate_gpm(stock):
    """Calcule la Marge Brute (Gross Profit Margin). Vérifie l'existence des données."""
    try:
        financials = stock.financials
        if financials.empty:
            return -1.0
            
        gross_profit = financials.loc['Gross Profit'].iloc[0]
        total_revenue = financials.loc['Total Revenue'].iloc[0]
        
        if total_revenue > 0:
            return gross_profit / total_revenue
        return -1.0
    except KeyError:
        return -1.0
    except Exception:
        return -1.0

def calculate_de_ratio(stock):
    """Calcule le Ratio Dette/Capitaux Propres (Debt-to-Equity) de manière robuste."""
    try:
        balance_sheet = stock.balance_sheet
        if balance_sheet.empty:
            raise ValueError("Balance sheet empty")

        # Tente de récupérer les données précises, sinon utilise les valeurs de l'objet info
        total_debt = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else get_safe_float(stock.info, 'totalDebt', 0.0)
        total_equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0] if 'Total Stockholder Equity' in balance_sheet.index else get_safe_float(stock.info, 'totalStockholderEquity', -1.0)
        
        if total_equity > 0:
            return total_debt / total_equity
        return 9999.0 
    except Exception:
        # Fallback si les données détaillées ont échoué
        total_debt = get_safe_float(stock.info, 'totalDebt', reject_value=0.0)
        total_equity = get_safe_float(stock.info, 'totalStockholderEquity', reject_value=-1.0)
        if total_equity > 0:
            return total_debt / total_equity
        return 9999.0


# --- 2. FONCTIONS DE RÉCUPÉRATION DES TICKERS (VIA WIKIPEDIA) ---

def get_tickers_from_wiki(url, table_index, potential_cols, suffix=""):
    """Fonction générique pour scraper les tickers, avec colonnes flexibles."""
    try:
        df_list = pd.read_html(url, header=0) 
        if not df_list or len(df_list) <= table_index:
            return []
            
        df = df_list[table_index]
        
        # Trouve le nom de colonne correct
        symbol_col = next((col for col in potential_cols if col in df.columns), None)
        
        if symbol_col:
            # Nettoie les données et applique le suffixe
            return [str(t).replace('.', '-') + suffix for t in df[symbol_col].tolist() if pd.notna(t)]
        else:
            # print(f"  > Erreur: Colonne de symbole non trouvée dans {url}")
            return []
    except Exception:
        return []

def get_all_global_tickers():
    """Agrège les tickers des principales bourses mondiales."""
    all_tickers = []
    print("--- Démarrage de la récupération mondiale des Tickers (via Wikipedia) ---")

    # USA
    all_tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0, ['Symbol', 'Ticker']))
    all_tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/Nasdaq-100', 4, ['Symbol', 'Ticker']))
    
    # Europe
    all_tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/CAC_40', 4, ['Ticker'], suffix=".PA"))
    all_tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/DAX', 4, ['Ticker'], suffix=".DE"))
    all_tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/FTSE_100_Index', 4, ['Ticker'], suffix=".L"))

    # Asie et autres (couverture manuelle)
    print("  > Ajout des leaders Japonais, Suisses, Canadiens, etc. (Liste manuelle)...")
    all_tickers.extend([
        "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "9432.T", "7974.T", # Japon
        "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ZURN.SW", # Suisse
        "RY.TO", "TD.TO", "ENB.TO", # Canada
        "BHP.AX", "CBA.AX", "CSL.AX", "WBC.AX", # Australie
        "0700.HK", "9988.HK", "1299.HK", # Hong Kong
    ])

    # Nettoyage et dédoublonnage
    clean_tickers = list(set(filter(None, all_tickers))) 
    print(f"--- {len(clean_tickers)} Tickers agrégés et prêts pour l'analyse ---")
    return clean_tickers

# --- 3. ANALYSE PRINCIPALE MULTITHREADÉE ---

def process_ticker(ticker):
    """Analyse un seul ticker en appliquant les 4 filtres de Buffett avec gestion d'erreurs."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info:
             return None

        # Tente d'obtenir un prix de manière sécurisée
        price = get_safe_float(info, 'regularMarketPrice', reject_value=-1.0)
        if price <= 0:
             price = get_safe_float(info, 'currentPrice', reject_value=-1.0)
             if price <= 0:
                return None

        sector = info.get('sector', 'N/A')

        # 1. Exclusion Sectorielle
        if sector in EXCLUDED_SECTORS:
            return None

        # 2. Calcul des Ratios
        pe_val = get_safe_float(info, 'trailingPE', reject_value=9999.0)
        roe_val = calculate_roe(stock)
        gpm_val = calculate_gpm(stock)
        de_val = calculate_de_ratio(stock)

        # 3. Application des 4 Filtres
        is_pe_ok = (0.0 < pe_val < 15.0)
        is_roe_ok = (roe_val > 0.15)
        is_gpm_ok = (gpm_val > 0.20)
        # Règle D/E avec exception
        is_de_ok = (de_val < 1.0) or (sector in EXEMPTED_DEBT_SECTORS)

        if is_pe_ok and is_roe_ok and is_gpm_ok and is_de_ok:
            
            name = info.get('longName', ticker)
            currency = info.get('currency', 'USD')
            tag = "Valeur d'Or"

            if sector in EXEMPTED_DEBT_SECTORS:
                tag = f"Valeur d'Or (Dette adaptée : {sector})"

            return {
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
            }
        return None
    
    except Exception:
        # Capture
