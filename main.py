import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
import pytz

st.set_page_config(page_title="Mission Control [Pure Position]", layout="wide")

# --- パラメータ設定 ---
ticker_sym = "NIY=F"
interval = "15m"
period = "7d"
ma_window = 25
std_window = 120  # 30時間分の平均・標準偏差を基準にする

# 戦略閾値
T_SCORE_OVERHEAT = 90
T_SCORE_BEAR = 30
T_SCORE_CRITICAL = 25

st.title("🚀 Market Mission Control [Pure Mode]")

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

    # 【純粋な位置の計算】
    df['MA25'] = df['Close'].rolling(window=ma_window).mean()
    df['Bias'] = (df['Close'] - df['MA25']) / df['MA25'] * 100
    df['Bias_Mean'] = df['Bias'].rolling(window=std_window).mean()
    df['Bias_Std'] = df['Bias'].rolling(window=std_window).std()
    
    # 加速度を排除した、純粋なT-Score
    df['T_Score'] = ((df['Bias'] - df['Bias_Mean']) / df['Bias_Std']) * 10 + 50
    df['Velocity'] = df['Close'].diff()

    df['CHI_Label'] = df['CST'].dt.strftime('%H:%M')
    return df

df = load_data()

if not df.empty:
    df_plot = df.tail(64).copy().reset_index(drop=True)
    
    if len(df_plot) > 0:
        latest = df_plot.iloc[-1]

        st.subheader("Mission Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("PRICE", f"¥{latest['Close']:,.0f}", f"{latest['Velocity']:+.0f}")
        with col2:
            st.metric("T-SCORE", f"{latest['T_Score']:.1f}")
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

        # 偏差値チャート（加速度なし、純粋な位置）
        ax2.plot(df_plot.index, df_plot['T_Score'], color='darkviolet', linewidth=1.5)
        
        # 閾値ライン
        ax2.axhline(T_SCORE_OVERHEAT, color='crimson', linestyle='--', alpha=0.6)
        ax2.axhline(T_SCORE_BEAR, color='orange', linestyle='--', alpha=0.6) # 30
        ax2.axhline(T_SCORE_CRITICAL, color='red', linestyle=':', alpha=0.8) # 25
        
        # ロング検討ゾーンを薄く着色（視認性向上）
        ax2.axhspan(20, 30, color='orange', alpha=0.1)
        
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, rotation=45, fontsize=8)
        ax2.grid(axis='x', alpha=0.2)
        ax2.set_ylim(20, 80) # 表示範囲を固定して変化を捉えやすくする

        st.pyplot(fig)
else:
    st.error("データが取得できません。")
