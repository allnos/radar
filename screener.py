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
    manual_list = ["7203.T", "6758.T", "9984.T", "NESN.SW", "NOVN.SW", "ROG.SW", "RY.TO", "TD.TO", "ENB.TO", "BHP.AX", "CBA.AX", "0700.HK", "9988.HK", "AAPL", "MSFT", "TTE.PA"]
    tickers.extend(manual_list)
    
    unique_tickers = list(set(tickers))
    print(f"--- Total Tickers uniques trouvés : {len(unique_tickers)} ---")
    return unique_tickers

# --- 3. ANALYSE ET SEGMENTATION ---

def process_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info: return None

        price = get_safe_float(info, 'currentPrice', 0.0)
        if price <= 0: price = get_safe_float(info, 'regularMarketPrice', 0.0)
        if price <= 0: return None

        sector = info.get('sector', 'N/A')
        if sector in EXCLUDED_SECTORS: return None

        pe = get_safe_float(info, 'trailingPE', 9999.0)
        roe = calculate_roe(stock)
        gpm = calculate_gpm(stock)
        de = calculate_de_ratio(stock)

        ok_pe = (0 < pe < 25) # CRITÈRE P/E < 25
        ok_roe = (roe > 0.15)
        ok_gpm = (gpm > 0.20)
        ok_de = (de < 1.0) or (sector in EXEMPTED_DEBT_SECTORS)

        if ok_pe and ok_roe and ok_gpm and ok_de:
            name = info.get('longName', ticker)
            currency = info.get('currency', 'USD')
            tag = "Valeur d'Or"
            if sector in EXEMPTED_DEBT_SECTORS: tag += f" (Dette: {sector})"
            
            return {
                "symbol": ticker, "name": name, "sector": sector,
                "pe": round(pe, 2), "roe": round(roe*100, 2),
                "gpm": round(gpm*100, 2), "de_ratio": round(de, 2),
                "price": round(price, 2), "currency": currency, "tag": tag
            }
    except:
        return None

def run():
    try:
        # 1. Récupération des Tickers
        tickers = get_all_global_tickers()
        
        # 2. Récupération et Filtrage par Segment
        # LIGNE CRUCIALE : CORRECTION DE LA SYNTAXE
        if len(sys.argv) > 1: 
            segment = sys.argv[1] # Ex: "A-B"
        else:
            segment = "A-Z" # Par défaut, tout si lancé manuellement
            
        allowed_letters = None
            
        if segment == "A-Z":
            filtered_tickers = tickers
        else:
            try:
                start_char, end_char = segment.split('-')
                alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                start_index = alphabet.index(start_char.upper())
                end_index = alphabet.index(end_char.upper())
                # Définit l'ensemble des lettres valides pour le segment
                allowed_letters = set(alphabet[start_index:end_index + 1]) 
                
                filtered_tickers = [
                    t for t in tickers 
                    if t and t[0].upper() in allowed_letters
                ]
            except:
                print(f"Format de segment non reconnu: {segment}. Analyse complète.")
                filtered_tickers = tickers
                segment = "A-Z" # Revient à l'analyse complète pour ne pas planter la fusion

        # Sécurité : Limite à 2000 actions par job pour les très gros segments
        tickers_to_process = filtered_tickers[:2000] 

        print(f"Analyse du segment {segment}. Actions à traiter: {len(tickers_to_process)}")
        
        # 3. Exécution de l'Analyse
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_ticker, tickers_to_process))

        data = sorted([r for r in results if r], key=lambda x: x['pe'])
        
        # 4. Chargement des anciennes données et ajout des nouvelles (fusion)
        try:
            with open("data.json", "r") as f:
                existing_data = json.load(f)
            
            # Ne fusionne que si allowed_letters est définie (i.e. si ce n'est pas A-Z)
            if allowed_letters is not None:
                # 4.1. Suppression des anciennes valeurs du segment actuel
                existing_data['data'] = [
                    item for item in existing_data['data'] 
                    if not (item['symbol'] and item['symbol'][0].upper() in allowed_letters)
                ]
                
                # 4.2. Ajout des nouvelles valeurs du segment
                existing_data['data'].extend(data)
                data = existing_data['data']
        
        except (FileNotFoundError, json.JSONDecodeError):
            print("Création d'un nouveau fichier data.json.")
        
        # 5. Sauvegarde
        final = {
            "last_updated": datetime.datetime.utcnow().strftime("%d/%m/%Y %H:%M GMT"),
            "count": len(data),
            "data": data
        }
        
        with open("data.json", "w") as f:
            json.dump(final, f)
        print(f"Succès du segment {segment}. {len(data)} actions totales après fusion.")
        
    except Exception:
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    pd.options.mode.chained_assignment = None
    run()
