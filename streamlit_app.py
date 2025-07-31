import yfinance as yf
import pandas as pd
import streamlit as st
from typing import Tuple, Union

# Page configuration
st.set_page_config(page_title="Nifty Technical Analysis", layout="wide")

@st.cache_data
def load_data(ticker: str, start_date: Union[str, pd.Timestamp], end_date: Union[str, pd.Timestamp]) -> pd.DataFrame:
    df = yf.download(ticker, start=start_date, end=end_date)
    if df is None or df.empty:
        return pd.DataFrame()
    df.dropna(inplace=True)
    return df

# Indicator functions
def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

def compute_roc(series: pd.Series, window: int = 12) -> pd.Series:
    return (series - series.shift(window)) / series.shift(window) * 100

def compute_adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    # Ensure columns are numeric and 1D Series
    high = pd.to_numeric(df['High'].squeeze(), errors='coerce')
    low = pd.to_numeric(df['Low'].squeeze(), errors='coerce')
    close = pd.to_numeric(df['Close'].squeeze(), errors='coerce')

    # True Range and ATR
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window, min_periods=window).mean()

    # Directional Movements
    up_move = high.diff()
    down_move = low.diff()

    # Ensure up_move and down_move are numeric
    up_move = pd.to_numeric(up_move, errors='coerce')
    down_move = pd.to_numeric(down_move, errors='coerce')

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    plus_di = 100 * plus_dm.rolling(window=window, min_periods=window).sum() / atr
    minus_di = 100 * minus_dm.rolling(window=window, min_periods=window).sum() / atr

    # Directional Index and ADX calculation
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(window=window, min_periods=window).mean()

    # Ensure it returns only the ADX Series
    return adx


def ratio(x: float, y: float, z: float) -> float:
    ratio: float = (x - y) / z
    return ratio

def SharpeRatio(r_p: float, r_f: float, sigma_p: float) -> float:
    return ratio(r_p, r_f, sigma_p)

def sortinoRatio(r_p: float, r_f: float, sigma_d: float) -> float:
    return ratio(r_p, r_f, sigma_d)

def treynorRatio(r_p: float, r_f: float, beta_p: float) -> float:
    return ratio(r_p, r_f, beta_p)

def calmer(annualized_Return: float, Max_drawdown: float) -> float:
    return annualized_Return / Max_drawdown

def MDD(P_peak: float, trough: list[float]) -> float:
    return max(1 - i / P_peak for i in trough)

def winratio(NwinTrade: int, NTotaltrade: int) -> float:
    return NwinTrade / NTotaltrade

def averageWinRatio(MeanWinningtrade: float, MeanLoosingtrade: float) -> float:
    return MeanWinningtrade / MeanLoosingtrade

def drawdown_duration(values: list[float]) -> list[float]:
    drawdown = []
    start = None  # start of a drawdown
    for i in range(1, len(values)):
        if values[i] > values[i - 1]:  # Peak
            if start is not None:  # End of drawdown
                drawdown.append(i - start)
                start = None
        elif values[i] < values[i - 1]:  # Trough
            if start is None:  # Start of drawdown
                start = i 
    if start is not None:  # If still in a drawdown at the end
        drawdown.append(len(values) - start)
    return drawdown

# Sidebar inputs
ticker: str = st.sidebar.text_input("Ticker", value="AAPL")
start_date = pd.to_datetime(st.sidebar.date_input("Start Date", value=pd.to_datetime("2020-01-01")))
end_date = pd.to_datetime(st.sidebar.date_input("End Date", value=pd.to_datetime("2025-01-01")))

# Indicator Parameters
rsi_window: int = st.sidebar.number_input("RSI Window", min_value=2, max_value=50, value=14)
macd_fast: int = st.sidebar.number_input("MACD Fast EMA", min_value=2, max_value=50, value=12)
macd_slow: int = st.sidebar.number_input("MACD Slow EMA", min_value=2, max_value=100, value=26)
macd_signal: int = st.sidebar.number_input("MACD Signal EMA", min_value=2, max_value=50, value=9)
roc_window: int = st.sidebar.number_input("ROC Window", min_value=2, max_value=50, value=12)
adx_window: int = st.sidebar.number_input("ADX Window", min_value=2, max_value=50, value=14)

# Load data
data: pd.DataFrame = load_data(ticker, start_date, end_date)
# Flatten MultiIndex columns if present
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
print("Columns after flattening:", data.columns)
print("Loaded data shape:", data.shape)
print(data.head())
if data.empty:
    st.error(f"No data loaded for ticker '{ticker}' from {start_date} to {end_date}. Please check the ticker symbol and date range.")
    st.stop()

# Compute indicators
with st.spinner("Calculating indicators..."):
    data['RSI'] = compute_rsi(data['Close'], window=rsi_window)
    macd_line, signal_line = compute_macd(data['Close'], fast=macd_fast, slow=macd_slow, signal=macd_signal)
    data['MACD'] = macd_line
    data['MACD_Signal'] = signal_line
    data['ROC'] = compute_roc(data['Close'], window=roc_window)
    data['ADX'] = compute_adx(data[['High', 'Low', 'Close']], window=adx_window)

# Calculate performance metrics
annualized_return = data['Close'].pct_change().mean() * 252  # Simple annualized return estimate
sigma_p = data['Close'].pct_change().std() * (252 ** 0.5)  # Annualized volatility
risk_free_rate = 0.03  # Assuming a risk-free rate of 3% (can be adjusted)
beta_p = 1.0  # Assuming a beta of 1.0 for Treynor ratio (you can estimate this with a market model)

# Calculate Sharpe, Sortino, and Treynor Ratios
sharpe = SharpeRatio(annualized_return, risk_free_rate, sigma_p)
sortino = sortinoRatio(annualized_return, risk_free_rate, sigma_p)  # Replace sigma_p with downside volatility if needed
treynor = treynorRatio(annualized_return, risk_free_rate, beta_p)

# Calculate Max Drawdown and Calmer Ratio
peak = data['Close'].max()
trough = data['Close'].min()
mdd = MDD(peak, data['Close'].tolist())  # Max drawdown percentage
calmer_ratio = calmer(annualized_return, mdd)  # Calmer Ratio

# User checkboxes for visibility
show_rsi = st.checkbox("Show RSI", value=True)
show_macd = st.checkbox("Show MACD", value=True)
show_roc = st.checkbox("Show ROC", value=True)
show_adx = st.checkbox("Show ADX", value=True)
show_drawdown = st.checkbox("Show Drawdown Duration", value=True)
show_raw_data = st.checkbox("Show Raw Data", value=False)
show_performance_metrics = st.checkbox("Show Performance Metrics", value=True)

# Plotting
if show_rsi:
    st.subheader("Relative Strength Index (RSI)")
    st.line_chart(data['RSI'])
    st.markdown("Overbought: 70, Oversold: 30")

if show_macd:
    st.subheader("MACD")
    st.line_chart(data[['MACD', 'MACD_Signal']])

if show_roc:
    st.subheader("Rate of Change (ROC)")
    st.line_chart(data['ROC'])

if show_adx:
    st.subheader("Average Directional Index (ADX)")
    st.line_chart(data['ADX'])

if show_drawdown:
    drawdown_durations = drawdown_duration(data['Close'].tolist())
    st.subheader("Drawdown Duration")
    st.bar_chart(drawdown_durations)

# Show performance metrics
if show_performance_metrics:
    st.subheader("Performance Metrics")
    st.write(f"**Sharpe Ratio**: {sharpe:.2f}")
    st.write(f"**Sortino Ratio**: {sortino:.2f}")
    st.write(f"**Treynor Ratio**: {treynor:.2f}")
    st.write(f"**Max Drawdown**: {mdd:.2%}")
    st.write(f"**Calmer Ratio**: {calmer_ratio:.2f}")

# Show raw data toggle
if show_raw_data:
    st.subheader("Raw Data")
    st.write(data)
