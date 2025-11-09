
# Configurations for the crypto trading bot
TRADING_FREQUENCY_MS = 15*60*1000  # frequency of trading signals in milliseconds
SET_TRADE_QUANTITY = 0.01 # fixed trade quantity to place orders once set up(signal found)

# Configuration for Trend Detection
VOLATIILE_THRESHOLD = 20  # time threshold for determining if the market is volatile

# Configuration for Pivot Point Detection
PIVOT_POINT_COMPARE = 2  # number of candles to compare front and back for pivot point detection
PIVOT_POINT_INTERVAL_MIN = 1 # minimum interval between pivot points

# Configuration for Support Line Detection
MAXIMUM_PERCENTAGE_DIFFERENCE = 0.005  # maximum percentage difference between pivot points for support line detection
MINIMUM_BREAKTHROUGH_PERCENTAGE = 0.002  # minimum percentage price breakthrough for pivot_2 to consider support line broken
SUPPORT_LINE_TIMEFRAME = 20 * TRADING_FREQUENCY_MS  # maximum number of candles after pivot_2 for a trade setup detection

# Configuration for Opportunity
TIME_EXTEND_MS = 5 * TRADING_FREQUENCY_MS  # time extension for opportunity window if min/max is found




