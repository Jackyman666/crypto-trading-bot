from .models import PivotPoint, Opportunity
from .config import VOLATIILE_THRESHOLD, PIVOT_POINT_COMPARE, PIVOT_POINT_INTERVAL_MIN, MAXIMUM_PERCENTAGE_DIFFERENCE, MINIMUM_BREAKTHROUGH_PERCENTAGE, SUPPORT_LINE_TIMEFRAME


def check_trend_conditions(data: list) -> str:
    """
    input data: list of OHLCV data points (timestamp, open, high, low, close, volume)
    return "bullish" | ""bearish" | "volatile" based on trend analysis"""
        # Convert data to DataFrame
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Calculate SMAs
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    
    # Need at least 50 periods to calculate both SMAs
    if len(df) < 50:
        return "volatile"
    
    # Create comparison for last 20 periods
    df['is_bullish'] = df['SMA_20'] > df['SMA_50']
    
    # Get last n periods to check whether it is volatile
    n = VOLATIILE_THRESHOLD
    check_volatile = df['is_bullish'].tail(n)
    
    # Check if all last 20 periods are bullish or bearish
    if all(check_volatile):
        return "bullish"
    elif not any(check_volatile):
        return "bearish"
    
    return "volatile"

def check_pivot_conditions(data: list) -> str:
    """
    input data: list of OHLCV data points (timestamp, open, high, low, close, volume)
    return high | low | both | none based on pivot point analysis
    """

    if not data:
        return "none"

    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    n = len(df)

    # sensible defaults
    try:
        window = int(PIVOT_POINT_COMPARE)
    except Exception:
        window = 2
    try:
        min_gap = int(PIVOT_POINT_INTERVAL_MIN)
    except Exception:
        min_gap = 2

    piv = np.zeros(n, dtype=int)  # 0 none, 1 high, 2 low, 3 both

    for idx in range(n):
        # skip edges where full neighborhood is not available
        if idx - window < 0 or idx + window >= n:
            continue

        pivotHigh = True
        pivotLow = True

        # check neighborhood [idx-window, idx+window]
        for i in range(idx - window, idx + window + 1):
            if df.iloc[idx].low > df.iloc[i].low:
                pivotLow = False
            if df.iloc[idx].high < df.iloc[i].high:
                pivotHigh = False

        if pivotHigh and pivotLow:
            piv[idx] = 3
        elif pivotHigh:
            piv[idx] = 1
        elif pivotLow:
            piv[idx] = 2

    # === Spacing enforcement: at most one pivot in any `min_gap` bars ===
    last_kept = -10**9
    pivot_idxs = np.where(piv != 0)[0]
    for i in pivot_idxs:
        if i - last_kept >= min_gap:
            last_kept = i
        else:
            piv[i] = 0

    # classification for the last candle
    last_code = int(piv[-1])
    if last_code == 1:
        return "high"
    if last_code == 2:
        return "low"
    if last_code == 3:
        return "both"
    return "none"
    

def check_support_line_conditions(pivot_1: PivotPoint, pivot_2: PivotPoint) -> bool:
    """Check if price is bouncing off support line"""

    # ensure pivot_1 is earlier than pivot_2
    if pivot_2.position < pivot_1.position:
        pivot_1, pivot_2 = pivot_2, pivot_1

    # types: require lows
    if pivot_1.type != "low" or pivot_2.type != "low":
        return False

    
    try:
        if isinstance(SUPPORT_LINE_TIMEFRAME, dict):
            max_bars = SUPPORT_LINE_TIMEFRAME.get(pivot_1.type, SUPPORT_LINE_TIMEFRAME.get("default", 20))
        elif isinstance(SUPPORT_LINE_TIMEFRAME, (int, float)):
            max_bars = float(SUPPORT_LINE_TIMEFRAME)
        else:
            max_bars = 20  # default fallback
    except Exception:
        max_bars = 20  # safe fallback

    # Check position difference
    if abs(pivot_2.position - pivot_1.position) > max_bars:
        return False

    # price sanity checks
    if pivot_1.price is None or pivot_2.price is None:
        return False
    if pivot_1.price == 0:
        return False

    # relative price closeness
    if abs(pivot_2.price - pivot_1.price) / abs(pivot_1.price) > tol_pct:
        return False

    return True

def check_minimum_conditions(pivot: PivotPoint, opportunity: Opportunity) -> bool:
    """Check if minimum conditions after breaking through support are met"""
        # require a low pivot

    if pivot.type != "low":
        return False

    # ensure timestamps fall inside opportunity window when provided
    if getattr(opportunity, "start", None) is not None and pivot.timestamp < opportunity.start:
        return False


    # threshold: pivot must be lower than avg by the configured percentage
    try:
        pct = float(MINIMUM_BREAKTHROUGH_PERCENTAGE)
    except Exception:
        return False
    
    avg = opportunity.support_line
    threshold = avg * (1.0 - pct)
    if pivot.price >= threshold:
        return False

    return True

def check_maximum_conditions(pivot: PivotPoint, opportunity: Opportunity) -> bool:
    """Check if maximum conditions after breaking out the previous high are met"""
    # require a high pivot
    if pivot.type != "high":
        return False

    # ensure timestamps fall inside opportunity window when provided
    if getattr(opportunity, "start", None) is not None and pivot.timestamp < opportunity.start:
        return False
    

    # Check if price breaks above previous pivot high
    try:
        if opportunity.pivot_high is None or opportunity.pivot_high <= 0:
            return False
        
    except Exception:
        return False
    
    return True

def check_trade_conditions(data: list,opportunity: Opportunity) -> bool:
    """Check if the fibonacci retracement levels are met"""
    
    if not data or opportunity is None:
        return False

    # local import to avoid assuming module-level pandas import

    # build DataFrame from incoming data (columns: timestamp, open, high, low, close, volume)
    try:
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    except Exception:
        return False

    if df.empty:
        return False

    last = df.iloc[-1]

    # pl1 is opportunity.minimum, ph2 is opportunity.maximum per your models
    try:
        pl1 = float(getattr(opportunity, "minimum"))
        ph2 = float(getattr(opportunity, "maximum"))
    except Exception:
        return False

    # sanity: PH2 should be above PL1
    if not (ph2 > pl1):
        return False

    # compute 0.618 retracement buy price (PH2 down to PL1)
    buy_price = pl1 + 0.618 * (ph2 - pl1)

    try:
        low = float(last['low'])
        high = float(last['high'])
    except Exception:
        return False

    # entry condition: the latest bar's range touches/includes the buy_price
    return low <= buy_price <= high