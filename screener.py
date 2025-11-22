import yfinance as yf
import json
import datetime

# --- LISTE MONDIALE "GLOBAL TITANS" ---
# Sélection des plus grandes capitalisations par zone économique
tickers_list = [
    # --- ÉTATS-UNIS (S&P 500 / NASDAQ) ---
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "JNJ", "V", 
    "PG", "JPM", "UNH", "MA", "HD", "CVX", "MRK", "ABBV", "KO", "PEP", "BAC",
    "PFE", "TMO", "COST", "DIS", "MCD", "CSCO", "WMT", "INTC", "VZ",

    # --- FRANCE (CAC 40) ---
    "TTE.PA", "LVMH.PA", "AIR.PA", "BNP.PA", "SAN.PA", "OR.PA", "EL.PA", "RMS.PA",
    "AI.PA", "GLE.PA", "ACA.PA", "CS.PA", "BN.PA", "ORA.PA", "CAP.PA", "KER.PA",

    # --- ALLEMAGNE (DAX 40) ---
    "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "AIR.DE", "VOW3.DE", "BMW.DE", "BAS.DE",
    "ADS.DE", "MBG.DE", "DHL.DE", "IFX.DE", "MUV2.DE", "BAYN.DE",

    # --- ROYAUME-UNI (FTSE 100) ---
    "SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "DGE.L", "RIO.L", "GSK.L",
    "BATS.L", "GLEN.L", "REL.L", "VOD.L", "LLOY.L", "BARC.L",

    # --- SUISSE (SMI) ---
    "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ZURN.SW", "ABBN.SW", "CFR.SW",

    # --- ITALIE (FTSE MIB) ---
    "FER.MI", "ENI.MI", "ISP.MI", "ENEL.MI", "UCG.MI", "STLAM.MI", "G.MI",

    # --- ESPAGNE (IBEX 35) ---
    "ITX.MC", "IBE.MC", "SAN.MC", "BBVA.MC", "TEF.MC", "REP.MC",

    # --- PAYS-BAS (AEX) ---
    "ASML.AS", "UNA.AS", "SHELL.AS", "HEIA.AS", "INGA.AS", "AD.AS",

    # --- SUÈDE (OMX) ---
    "AZN.ST", "INVE-B.ST", "ATCO-A.ST", "VOLV-B.ST", "ERIC-B.ST", "HM-B.ST",

    # --- CANADA (TSX) ---
    "RY.TO", "TD.TO", "ENB.TO", "CNR.TO", "CP.TO", "BMO.TO", "SU.TO", "BNS.TO",

    # --- JAPON (NIKKEI 225) ---
    "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "9432.T", "7974.T", "8035.T",
    "4063.T", "6098.T", "4502.T", "6501.T", "7267.T",

    # --- AUSTRALIE (ASX 200) ---
    "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WDS.AX", "FMG.AX",

    # --- HONG KONG / CHINE (HANG SENG) ---
    "0700.HK", "9988.HK", "0939.HK", "1299.HK", "0941.HK", "3690.HK", "1398.HK", "2318.HK"
]

def get_undervalued_stocks():
    undervalued_stocks = []
    print(f"--- Démarrage de l'analyse mondiale ({len(tickers_list)} titres) ---")
    
    for ticker in tickers_list:
        try:
            stock = yf.Ticker(ticker)
            
            # fast_info est beaucoup plus rapide et consomme moins de ressources
            try:
                current_price = stock.fast_info.last_price
            except:
                print(f"Prix non disponible pour {ticker}")
                continue

            info = stock.info
            
            # Récupération des données fondamentales
            pe_ratio = info.get('trailingPE')
            roe = info.get('returnOnEquity', 0)
            name = info.get('longName', ticker)
            sector = info.get('sector', 'N/A')
            currency = info.get('currency', 'USD')

            # Si le P/E est manquant (fréquent), tentative de calcul manuel
            if pe_ratio is None:
                eps = info.get('trailingEps')
                if eps and eps != 0:
                    pe_ratio = current_price / eps

            # --- CRITÈRES WARREN BUFFETT ---
            # 1. Le "Pas cher" (Graham) : P/E < 15
            is_cheap = (pe_ratio is not None and 0 < pe_ratio < 15)

            # 2. La "Qualité à prix juste" (Buffett moderne) : P/E entre 15 et 25 AVEC un ROE fort (>15%)
            is_quality = (pe_ratio is not None and 15 <= pe_ratio < 25 and roe is not None and roe > 0.15)

            if is_cheap or is_quality:
                reason = "Sous-évalué" if is_cheap else "Qualité/Prix"
                print(f"--> TROUVÉ [{reason}]: {name} (P/E: {pe_ratio:.2f} | ROE: {roe:.2%})")
                
                undervalued_stocks.append({
                    "symbol": ticker,
                    "name": name,
                    "sector": sector,
                    "pe": round(pe_ratio, 2),
                    "roe": round(roe * 100, 2) if roe else 0, # On stocke le ROE pour l'affichage futur
                    "price": round(current_price, 2),
                    "currency": currency,
                    "tag": reason
                })
                
        except Exception as e:
            # On ignore silencieusement les erreurs pour ne pas bloquer le script
            continue

    # Tri par P/E croissant
    undervalued_stocks.sort(key=lambda x: x['pe'])
    
    final_data = {
        "last_updated": datetime.datetime.utcnow().strftime("%d/%m/%Y à %H:%M GMT"),
        "data": undervalued_stocks
    }

    with open("data.json", "w") as f:
        json.dump(final_data, f)
    
    print("--- Analyse terminée. ---")

if __name__ == "__main__":
    get_undervalued_stocks()
