import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
import pytz

st.set_page_config(page_title="Mission Control [Bull Mode]", layout="wide")

# --- パラメータ設定 ---
ticker_sym = "NIY=F"
interval = "15m"
period = "7d"
std_window = 120 # 30時間分の「押し目具合」を基準にする

# 戦略閾値（強気モード用）
T_SCORE_BULL_RECOVERY = 60 # 高値復帰の兆し
T_SCORE_LONG_ENTRY = 30    # 押し目買い検討
T_SCORE_CRITICAL = 25      # 絶好の買い場

st.title("🚀 Market Mission Control [Bull Mode]")

@st.cache_data(ttl=60)
def load_data():
    data = yf.download(ticker_sym, period=period, interval=interval, auto_adjust=True)
    if data.empty: return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    df = data.copy().dropna(subset=['Close'])
    df.index = df.index.tz_convert('Asia/Tokyo')
    df['JST'] = df.index
    df['CST'] = df.index.tz_convert('America/Chicago')
    df = df.reset_index(drop=True)

    # 【強気ロジック：高値からのドローダウン計算】
    # 直近30時間(120本)の最高値を基準とする
    df['Rolling_High'] = df['Close'].rolling(window=120, min_periods=1).max()
    
    # 最高値からの乖離率（常に0以下になる）
    df['DD'] = (df['Close'] - df['Rolling_High']) / df['Rolling_High'] * 100
    
    # 乖離率の平均と標準偏差
    df['DD_Mean'] = df['DD'].rolling(window=std_window).mean()
    df['DD_Std'] = df['DD'].rolling(window=std_window).std()
    
    # T-Score化（高値付近にいれば高い数値、押し目が深ければ低い数値）
    # 10台や20台は「高値から異常に離れている＝強気派には絶好の機会」
    df['T_Score'] = ((df['DD'] - df['DD_Mean']) / df['DD_Std']) * 10 + 50
    
    df['Velocity'] = df['Close'].diff()
    df['CHI_Label'] = df['CST'].dt.strftime('%H:%M')
    return df

df = load_data()

if not df.empty:
    df_plot = df.tail(64).copy().reset_index(drop=True)
    
    if len(df_plot) > 0:
        latest = df_plot.iloc[-1]
        st.subheader(f"Current Target: ATH ¥{latest['Rolling_High']:,.0f}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("PRICE", f"¥{latest['Close']:,.0f}", f"{latest['Velocity']:+.0f}")
        with col2:
            st.metric("BULL SCORE", f"{latest['T_Score']:.1f}")
        with col3:
            st.write(f"JST: {latest['JST'].strftime('%m/%d %H:%M')}")
            st.write(f"CST: {latest['CST'].strftime('%m/%d %H:%M')}")

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})

        tick_interval = 4
        tick_positions = np.arange(0, len(df_plot), tick_interval)
        tick_labels = [df_plot['CHI_Label'].iloc[i] for i in tick_positions]

        # 価格と最高値ライン
        ax1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=1.5, label="Current")
        ax1.plot(df_plot.index, df_plot['Rolling_High'], color='green', linestyle=':', alpha=0.5, label="Target(ATH)")
        ax1.legend(loc='upper left')
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels([])
        ax1.grid(alpha=0.2)

        # 強気偏差値チャート
        ax2.plot(df_plot.index, df_plot['T_Score'], color='blue', linewidth=1.5)
        ax2.axhline(T_SCORE_BULL_RECOVERY, color='green', linestyle='--', alpha=0.5)
        ax2.axhline(T_SCORE_LONG_ENTRY, color='orange', linestyle='--', alpha=0.6)
        ax2.axhline(T_SCORE_CRITICAL, color='red', linestyle=':', alpha=0.8)
        
        # 買い場ゾーンを着色
        ax2.axhspan(15, 30, color='red', alpha=0.05)
        
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, rotation=45, fontsize=8)
        ax2.set_ylim(10, 90)
        ax2.grid(axis='x', alpha=0.2)

        st.pyplot(fig)
else:
    st.error("データ取得失敗")
