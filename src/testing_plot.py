import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import json
import sklearn
import statsmodels.api as sm
import loguru
import mplfinance as mpf
from tqdm import tqdm
from talib import ATR
from scipy.signal import find_peaks

def plot_local_extremes(ts,degree=2):
    pass

if __name__ == "__main__":
    ts = pd.read_csv('data/BTC_1d.csv', index_col='timestamp')
    ts.index = pd.to_datetime(ts.index)

    ts = ts.loc['2025-01-01':]
    lts = np.log(ts)

    for m, g in tqdm(lts.groupby(lts.index.month)):
        vol = lts['price'].diff().std()

        #min_point = g['low'].idxmin()
        #max_point = g['high'].idxmax()

        ax = g['price'].plot()
        buffer = vol * 0.5


        max_points = find_peaks(g['price'].fillna(0), threshold=buffer)[0]
        min_points = find_peaks(-g['price'].fillna(0), threshold=buffer)[0]
        for i in max_points:
            top_line = g['price'].iat[i]
            top_range = (top_line - buffer, top_line + buffer)
            ax.axhspan(ymin=top_range[0], ymax=top_range[1], xmin=max(0,(i-24*5)/len(g)), xmax=min(1,(i+24*5)/len(g)), color='green', alpha=0.3)

        for i in min_points:
            bot_line = g['price'].iat[i]
            bot_range = (bot_line - buffer, bot_line + buffer)
            ax.axhspan(ymin=bot_range[0], ymax=bot_range[1], xmin=max(0,(i-24*5)/len(g)), xmax=min(1,(i+24*5)/len(g)), color='red', alpha=0.3)

        #mpf.plot(lts,type='candle')
        plt.show()
        exit()
    
