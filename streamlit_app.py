import yfinance as yf
import pandas as pd
import streamlit as st
from typing import Tuple, Union

# Page configuration
st.set_page_config(page_title="Nifty Technical Analysis", layout="wide")

@st.cache_data
def load_data(ticker: str, start_date: Union[str, pd.Timestamp], end_date: Union[str, pd.Timestamp]) -> pd.DataFrame:
    df: pd.DataFrame = yf.download(ticker, start=start_date, end=end_date)
    df.dropna(inplace=True)
    return df

# Indicator functions
def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta: pd.Series = series.diff()
    gain: pd.Series = delta.clip(lower=0)
    loss: pd.Series = -delta.clip(upper=0)
    avg_gain: pd.Series = gain.rolling(window).mean()
    avg_loss: pd.Series = loss.rolling(window).mean()
    rs: pd.Series = avg_gain / avg_loss
    rsi: pd.Series = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
    ema_fast: pd.Series = series.ewm(span=fast, adjust=False).mean()
    ema_slow: pd.Series = series.ewm(span=slow, adjust=False).mean()
    macd_line: pd.Series = ema_fast - ema_slow
    signal_line: pd.Series = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

def compute_roc(series: pd.Series, window: int = 12) -> pd.Series:
    return (series - series.shift(window)) / series.shift(window) * 100

def compute_adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high: pd.Series = df['High']
    low: pd.Series = df['Low']
    close: pd.Series = df['Close']
    tr_components: pd.DataFrame = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1)
    tr: pd.Series = tr_components.max(axis=1)
    atr: pd.Series = tr.rolling(window).mean()

    up_move: pd.Series = high.diff()
    down_move: pd.Series = low.diff()
    plus_dm: pd.Series = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm: pd.Series = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    plus_di: pd.Series = 100 * plus_dm.rolling(window).sum() / atr
    minus_di: pd.Series = 100 * minus_dm.rolling(window).sum() / atr

    dx: pd.Series = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx: pd.Series = dx.rolling(window).mean()
    adx.name = 'ADX'
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

# Sidebar inputs
ticker: str = st.sidebar.text_input("Ticker", value="AAPL")
start_date: pd.Timestamp = st.sidebar.date_input("Start Date", value=pd.to_datetime("2020-01-01"))
end_date: pd.Timestamp = st.sidebar.date_input("End Date", value=pd.to_datetime("2025-01-01"))
print(f"Ticker: {ticker}, Start: {start_date}, End: {end_date}")

st.sidebar.markdown("---")
st.sidebar.markdown("**Indicator Parameters**")
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
    adx_series: pd.Series = compute_adx(data[['High', 'Low', 'Close']], window=adx_window)
    print("adx_series type:", type(adx_series))
    print("adx_series shape:", getattr(adx_series, 'shape', None))
    print("adx_series ndim:", getattr(adx_series, 'ndim', None))
    print("data index shape:", data.index.shape)
    print("adx_series head:", adx_series.head())
    if isinstance(adx_series, pd.DataFrame):
        adx_series = adx_series.iloc[:, 0]
    elif hasattr(adx_series, 'ndim') and adx_series.ndim > 1:
        adx_series = pd.Series(adx_series.squeeze(), index=data.index)
    data['ADX'] = adx_series.reindex(data.index)
print("Data after indicators, before dropna:", data.shape)
print(data.head())

# Drop NaNs from warm-up periods
data.dropna(inplace=True)
print("Data after dropna:", data.shape)
print(data.head())

# Layout Title
st.title(f"Technical Analysis for {ticker}")

# --- Streamlit Native Charts ---

# Closing Price chart
st.subheader("Closing Price")
st.line_chart(data['Close'])

# RSI chart
st.subheader("Relative Strength Index (RSI)")
st.line_chart(data['RSI'])
st.markdown("Overbought: 70, Oversold: 30")

# MACD chart
st.subheader("MACD")
st.line_chart(data[['MACD', 'MACD_Signal']])

# ROC and ADX side-by-side
col1, col2 = st.columns(2)
with col1:
    st.subheader("Rate of Change (ROC)")
    st.line_chart(data['ROC'])
with col2:
    st.subheader("Average Directional Index (ADX)")
    st.line_chart(data['ADX'])

# Raw data toggle
if st.checkbox("Show raw data"):
    if data.empty:
        st.write("No data to display.")
    else:
        st.write(data)
