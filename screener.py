import yfinance as yf
import json
import datetime
import os

# --- LISTE DES ACTIONS À SURVEILLER ---
# Vous pouvez ajouter ou retirer des codes ici.
# Pour la France, ajoutez ".PA" à la fin (ex: Total = TTE.PA)
tickers_list = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", # US Tech
    "TTE.PA", "BNP.PA", "LVMH.PA", "AIR.PA", "GLE.PA", # France (CAC40)
    "SIE.DE", "VOW3.DE", "SAP.DE", # Allemagne
    "SHEL.L", "HSBA.L", # Royaume-Uni
    "7203.T", "6758.T", # Japon
    "BABA", "JD" # Chine
]

def get_undervalued_stocks():
    undervalued_stocks = []
    
    print("--- Démarrage de l'analyse ---")
    
    for ticker in tickers_list:
        try:
            print(f"Analyse de {ticker}...")
            # Récupération des données via Yahoo Finance
            stock = yf.Ticker(ticker)
            
            # On utilise fast_info pour le prix actuel (plus rapide/fiable)
            current_price = stock.fast_info.last_price
            
            # On récupère les infos fondamentales
            info = stock.info
            
            # Récupération du P/E Ratio (Trailing)
            pe_ratio = info.get('trailingPE')
            
            # Si le P/E est manquant, on essaie de le calculer (Prix / EPS)
            if pe_ratio is None:
                eps = info.get('trailingEps')
                if eps and eps != 0:
                    pe_ratio = current_price / eps

            name = info.get('longName', ticker)
            sector = info.get('sector', 'N/A')
            currency = info.get('currency', 'USD')
            
            # --- CRITÈRES DE SÉLECTION ---
            # On garde si P/E existe, est positif, et inférieur à 20 (sous-évalué)
            if pe_ratio is not None and 0 < pe_ratio < 20:
                print(f"--> OPPORTUNITÉ : {name} (P/E: {pe_ratio:.2f})")
                undervalued_stocks.append({
                    "symbol": ticker,
                    "name": name,
                    "sector": sector,
                    "pe": round(pe_ratio, 2),
                    "price": round(current_price, 2),
                    "currency": currency
                })
                
        except Exception as e:
            print(f"Erreur sur {ticker}: {e}")
            continue

    # Tri du plus petit P/E au plus grand (les moins chers en premier)
    undervalued_stocks.sort(key=lambda x: x['pe'])
    
    # Préparation des données finales avec la date
    final_data = {
        "last_updated": datetime.datetime.utcnow().strftime("%d/%m/%Y à %H:%M GMT"),
        "data": undervalued_stocks
    }

    # Sauvegarde dans le fichier data.json
    with open("data.json", "w") as f:
        json.dump(final_data, f)
    
    print("--- Analyse terminée. Fichier data.json généré. ---")

if __name__ == "__main__":
    get_undervalued_stocks()
