import yfinance as yf
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Page configuration
st.set_page_config(page_title="Nifty Technical Analysis", layout="wide")

@st.cache_data
def load_data(ticker, start_date, end_date):
    df = yf.download(ticker, start=start_date, end=end_date)
    df.dropna(inplace=True)
    return df

# Indicator functions
def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

def compute_roc(series, window=12):
    return (series - series.shift(window)) / series.shift(window) * 100

def compute_adx(df, window=14):
    high, low, close = df['High'], df['Low'], df['Close']
    tr_components = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1)
    tr = tr_components.max(axis=1)
    atr = tr.rolling(window).mean()

    up_move = high.diff()
    down_move = low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    plus_di = 100 * plus_dm.rolling(window).sum() / atr
    minus_di = 100 * minus_dm.rolling(window).sum() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(window).mean()
    adx.name = 'ADX'
    return adx

# Sidebar inputs
ticker = st.sidebar.text_input("Ticker", value="AAPL")
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2020-01-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2025-01-01"))
print(f"Ticker: {ticker}, Start: {start_date}, End: {end_date}")

st.sidebar.markdown("---")
st.sidebar.markdown("**Indicator Parameters**")
rsi_window = st.sidebar.number_input("RSI Window", min_value=2, max_value=50, value=14)
macd_fast = st.sidebar.number_input("MACD Fast EMA", min_value=2, max_value=50, value=12)
macd_slow = st.sidebar.number_input("MACD Slow EMA", min_value=2, max_value=100, value=26)
macd_signal = st.sidebar.number_input("MACD Signal EMA", min_value=2, max_value=50, value=9)
roc_window = st.sidebar.number_input("ROC Window", min_value=2, max_value=50, value=12)
adx_window = st.sidebar.number_input("ADX Window", min_value=2, max_value=50, value=14)

# Load data
data = load_data(ticker, start_date, end_date)
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
    adx_series = compute_adx(data[['High', 'Low', 'Close']], window=adx_window)
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

# Plotting helper
def plot_series(index, series, ylabel=None, markers=None):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(index, series)
    if markers:
        for level in markers:
            ax.axhline(level, linestyle='--', alpha=0.5)
    if ylabel:
        ax.set_ylabel(ylabel)
    st.pyplot(fig)

# Closing Price chart
st.subheader("Closing Price")
plot_series(data.index, data['Close'], ylabel='Price')

# RSI chart
st.subheader("Relative Strength Index (RSI)")
plot_series(data.index, data['RSI'], ylabel='RSI', markers=[70, 30])

# MACD chart
st.subheader("MACD")
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(data.index, data['MACD'], label='MACD')
ax.plot(data.index, data['MACD_Signal'], label='Signal')
ax.legend()
st.pyplot(fig)

# ROC and ADX side-by-side
col1, col2 = st.columns(2)
with col1:
    st.subheader("Rate of Change (ROC)")
    plot_series(data.index, data['ROC'], ylabel='ROC (%)')
with col2:
    st.subheader("Average Directional Index (ADX)")
    plot_series(data.index, data['ADX'], ylabel='ADX')

# Raw data toggle
if st.checkbox("Show raw data"):
    if data.empty:
        st.write("No data to display.")
    else:
        st.write(data)
