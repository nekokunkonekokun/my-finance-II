import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
import pytz

st.set_page_config(page_title="Dual Time Mission Control", layout="wide")

# パラメータ設定
ticker_sym = "NIY=F"
interval = "10m"
period = "1mo"
ma_window = 25
std_window = 160

# 戦略閾値
INERTIA_THRESHOLD = 180
VELOCITY_FADE = 40
T_SCORE_OVERHEAT = 90
T_SCORE_BEAR = 30
T_SCORE_CRITICAL = 25

st.title("🚀 Market Mission Control [10m Mode]")

@st.cache_data(ttl=300)
def load_data():
    data = yf.download(ticker_sym, period=period, interval=interval, auto_adjust=True)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    df = data.copy().dropna(subset=['Close'])
    
    # --- タイムゾーン変換 ---
    # yfinanceのIndex(Datetime)を日本時間とシカゴ時間に変換
    df['JST'] = df.index.tz_convert('Asia/Tokyo')
    df['CST'] = df.index.tz_convert('America/Chicago')
    
    # 計算用に一度Indexをリセット
    df = df.reset_index()

    # 指標計算
    df['MA25'] = df['Close'].rolling(window=ma_window).mean()
    df['Bias'] = (df['Close'] - df['MA25']) / df['MA25'] * 100
    df['Bias_Mean'] = df['Bias'].rolling(window=std_window).mean()
    df['Bias_Std'] = df['Bias'].rolling(window=std_window).std()
    df['T_Score'] = ((df['Bias'] - df['Bias_Mean']) / df['Bias_Std']) * 10 + 50
    df['Velocity'] = df['Close'].diff()

    # シグナル
    df['Inertia_UP'] = df['Velocity'] >= INERTIA_THRESHOLD
    df['Short_Signal'] = (df['T_Score'] >= T_SCORE_OVERHEAT) & (df['Velocity'].shift(1) > 150) & (df['Velocity'] < VELOCITY_FADE)
    
    # チャート用ラベル (シカゴ時間)
    df['CHI_Label'] = df['CST'].dt.strftime('%H:%M')
    return df

df = load_data()
last_time = df['JST'].max()
df_plot = df[df['JST'] >= (last_time - timedelta(hours=16))].copy().reset_index(drop=True)
latest = df_plot.iloc[-1]

# 目盛り設定
tick_interval = 6
tick_positions = np.arange(0, len(df_plot), tick_interval)
tick_labels = [df_plot['CHI_Label'].iloc[i] for i in tick_positions]

# --- パネル表示 ---
st.subheader("Mission Status")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("PRICE", f"¥{latest['Close']:,.0f}", f"{latest['Velocity']:+.0f}")
with col2:
    st.metric("T-SCORE", f"{latest['T_Score']:.1f}")
with col3:
    st.write(f"**JST:** {latest['JST'].strftime('%m/%d %H:%M')}")
    st.write(f"**CHI:** {latest['CST'].strftime('%m/%d %H:%M')}")

# --- Chart ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})

# 上段：価格
ax1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=1.5)
ax1.scatter(df_plot[df_plot['Inertia_UP']].index, df_plot[df_plot['Inertia_UP']]['Close'], color='red', s=60)
ax1.set_xticks(tick_positions)
ax1.set_xticklabels([])
ax1.grid(alpha=0.2)

# 下段：T-Score
ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=1)
ax2.axhline(T_SCORE_OVERHEAT, color='crimson', linestyle='--', alpha=0.6)
ax2.axhline(T_SCORE_BEAR, color='orange', linestyle='--', alpha=0.6)
ax2.axhline(T_SCORE_CRITICAL, color='red', linestyle=':', alpha=0.8)
ax2.set_xticks(tick_positions)
ax2.set_xticklabels(tick_labels, rotation=45, fontsize=8)
ax2.grid(axis='x', alpha=0.2)

st.pyplot(fig)
