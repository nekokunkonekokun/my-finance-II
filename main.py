import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
import pytz

st.set_page_config(page_title="Mission Control [Accel Fit]", layout="wide")

# --- パラメータ設定 ---
ticker_sym = "NIY=F"
interval = "15m"
period = "7d"
ma_window = 25
std_window = 120

# 戦略閾値
T_SCORE_OVERHEAT = 90
T_SCORE_BEAR = 30
T_SCORE_CRITICAL = 25

st.title("🚀 Market Mission Control [Acceleration Mode]")

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

    # 基本指標計算
    df['MA25'] = df['Close'].rolling(window=ma_window).mean()
    df['Bias'] = (df['Close'] - df['MA25']) / df['MA25'] * 100
    df['Bias_Mean'] = df['Bias'].rolling(window=std_window).mean()
    df['Bias_Std'] = df['Bias'].rolling(window=std_window).std()
    
    # 位置のスコア
    df['T_Score_Pos'] = ((df['Bias'] - df['Bias_Mean']) / df['Bias_Std']) * 10 + 50
    
    # 加速度（勢い）の計算：window=5, 係数=3 で逆行現象を抑制
    df['Velocity'] = df['Close'].diff()
    df['Accel_Factor'] = (df['Velocity'].rolling(window=5).mean() / (df['Close'] * 0.001)) * 3
    df['T_Score'] = df['T_Score_Pos'] + df['Accel_Factor']

    df['CHI_Label'] = df['CST'].dt.strftime('%H:%M')
    return df

df = load_data()

if not df.empty:
    # 表示範囲：最新64件
    df_plot = df.tail(64).copy().reset_index(drop=True)
    
    if len(df_plot) > 0:
        latest = df_plot.iloc[-1]

        st.subheader("Mission Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("PRICE", f"¥{latest['Close']:,.0f}", f"{latest['Velocity']:+.0f}")
        with col2:
            st.metric("T-SCORE (Accel)", f"{latest['T_Score']:.1f}")
        with col3:
            st.write(f"**JST:** {latest['JST'].strftime('%m/%d %H:%M')}")
            st.write(f"**CST:** {latest['CST'].strftime('%m/%d %H:%M')}")

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})

        tick_interval = 4
        tick_positions = np.arange(0, len(df_plot), tick_interval)
        tick_labels = [df_plot['CHI_Label'].iloc[i] for i in tick_positions]

        # 価格チャート
        ax1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=1.5)
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels([])
        ax1.grid(alpha=0.2)

        # 偏差値チャート（加速度合成）
        ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=1.2, label="Accel T-Score")
        ax2.plot(df_plot.index, df_plot['T_Score_Pos'], color='gray', linewidth=0.8, alpha=0.3, label="Pos Only")
        
        ax2.axhline(T_SCORE_OVERHEAT, color='crimson', linestyle='--', alpha=0.6)
        ax2.axhline(T_SCORE_BEAR, color='orange', linestyle='--', alpha=0.6)
        ax2.axhline(T_SCORE_CRITICAL, color='red', linestyle=':', alpha=0.8)
        
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, rotation=45, fontsize=8)
        ax2.legend(loc='upper left', fontsize=7)
        ax2.grid(axis='x', alpha=0.2)

        st.pyplot(fig)
else:
    st.error("データが取得できません。")

# メリット：逆行現象を抑えつつ、角度の鋭さを維持しました。
# デメリット：完全に逆行を消すことはできません（勢いの変化を捉える仕様のため）。
# ハルシネーションを疑え
