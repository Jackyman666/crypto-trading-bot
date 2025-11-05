from roostoo_api import get_ticker
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
AVAILABLE_TICKERS = os.getenv('AVAILABLE_TICKERS')
TRADED_TICKERS = ['1000CHEEMS/USD', 'AAVE/USD', 'ADA/USD', 'APT/USD', 'ARB/USD', 'ASTER/USD', 'AVAX/USD', 'AVNT/USD', 'BIO/USD', 'BMT/USD', 'BNB/USD', 'BONK/USD', 'BTC/USD', 'CAKE/USD', 'CFX/USD', 'CRV/USD', 'DOGE/USD', 'DOT/USD', 'EDEN/USD', 'EIGEN/USD', 'ENA/USD', 'ETH/USD', 'FET/USD', 'FIL/USD', 'FLOKI/USD', 'FORM/USD', 'HBAR/USD', 'HEMI/USD', 'ICP/USD', 'LINEA/USD', 'LINK/USD', 'LISTA/USD', 'LTC/USD', 'MIRA/USD', 'NEAR/USD', 'ONDO/USD', 'OPEN/USD', 'PAXG/USD', 'PENDLE/USD', 'PENGU/USD', 'PEPE/USD', 'PLUME/USD', 'POL/USD', 'PUMP/USD', 'S/USD', 'SEI/USD', 'SHIB/USD', 'SOL/USD', 'SOMI/USD', 'STO/USD', 'SUI/USD', 'TAO/USD', 'TON/USD', 'TRUMP/USD', 'TRX/USD', 'TUT/USD', 'UNI/USD', 'VIRTUAL/USD', 'WIF/USD', 'WLD/USD', 'WLFI/USD', 'XLM/USD', 'XPL/USD', 'XRP/USD', 'ZEC/USD', 'ZEN/USD']

if __name__ == "__main__":
    #res = get_ticker()
    #df = pd.DataFrame(res['Data']).T
    #tickers = df.index.to_list()

    print(TRADED_TICKERS)
    