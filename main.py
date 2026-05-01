import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
import pytz

st.set_page_config(page_title="Mission Control [15m]", layout="wide")

# --- パラメータ設定 ---
ticker_sym = "NIY=F"
interval = "15m"
period = "7d"
ma_window = 25
std_window = 120  # 15分足に合わせた感度設定

# 戦略閾値
INERTIA_THRESHOLD = 180
VELOCITY_FADE = 40
T_SCORE_OVERHEAT = 90
T_SCORE_BEAR = 30
T_SCORE_CRITICAL = 25

st.title("🚀 Market Mission Control [15m Mode]")

@st.cache_data(ttl=60)
def load_data():
    data = yf.download(ticker_sym, period=period, interval=interval, auto_adjust=True)
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    df = data.copy().dropna(subset=['Close'])
    
    # タイムゾーン変換
    df.index = df.index.tz_convert('Asia/Tokyo')
    df['JST'] = df.index
    df['CST'] = df.index.tz_convert('America/Chicago')
    df = df.reset_index(drop=True)

    # 指標計算
    df['MA25'] = df['Close'].rolling(window=ma_window).mean()
    df['Bias'] = (df['Close'] - df['MA25']) / df['MA25'] * 100
    df['Bias_Mean'] = df['Bias'].rolling(window=std_window).mean()
    df['Bias_Std'] = df['Bias'].rolling(window=std_window).std()
    df['T_Score'] = ((df['Bias'] - df['Bias_Mean']) / df['Bias_Std']) * 10 + 50
    df['Velocity'] = df['Close'].diff()

    # シグナル
    df['Inertia_UP'] = df['Velocity'] >= INERTIA_THRESHOLD
    df['CHI_Label'] = df['CST'].dt.strftime('%H:%M')
    return df

df = load_data()

if not df.empty:
    # 15分足で16時間分（64件）をスライス
    df_plot = df.tail(64).copy().reset_index(drop=True)
    
    if len(df_plot) > 0:
        latest = df_plot.iloc[-1]

        # パネル表示
        st.subheader("Mission Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("PRICE", f"¥{latest['Close']:,.0f}", f"{latest['Velocity']:+.0f}")
        with col2:
            st.metric("T-SCORE", f"{latest['T_Score']:.1f}")
        with col3:
            st.write(f"**JST:** {latest['JST'].strftime('%m/%d %H:%M')}")
            st.write(f"**CST:** {latest['CST'].strftime('%m/%d %H:%M')}")

        # チャート描画
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})

        # 1時間(4件)おきに目盛り
        tick_interval = 4
        tick_positions = np.arange(0, len(df_plot), tick_interval)
        tick_labels = [df_plot['CHI_Label'].iloc[i] for i in tick_positions]

        ax1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=1.5)
        ax1.scatter(df_plot[df_plot['Inertia_UP']].index, df_plot[df_plot['Inertia_UP']]['Close'], color='red', s=60)
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels([])
        ax1.grid(alpha=0.2)

        ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=1)
        ax2.axhline(T_SCORE_OVERHEAT, color='crimson', linestyle='--', alpha=0.6, label="Short (90)")
        ax2.axhline(T_SCORE_BEAR, color='orange', linestyle='--', alpha=0.6, label="Long (30)")
        ax2.axhline(T_SCORE_CRITICAL, color='red', linestyle=':', alpha=0.8, label="Alert (25)")
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, rotation=45, fontsize=8)
        ax2.legend(loc='upper left')
        ax2.grid(axis='x', alpha=0.2)

        st.pyplot(fig)
else:
    st.error("データ取得エラー。15分足設定を確認してください。")
