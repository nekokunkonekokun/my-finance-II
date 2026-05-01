import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
import pytz

# 基本設定
st.set_page_config(page_title="Mission Control [Bull 120 Absolute]", layout="wide")

# --- パラメータ設定 ---
ticker_sym = "NIY=F"
interval = "15m"
period = "7d"
lookback_window = 120  # 短期戦の結界（30時間）

# 戦略閾値
T_SCORE_BULL_RECOVERY = 60 
T_SCORE_LONG_ENTRY = 30    
T_SCORE_CRITICAL = 25      

st.title("🚀 Market Mission Control [120-Bar Absolute High]")

@st.cache_data(ttl=60)
def load_data():
    data = yf.download(ticker_sym, period=period, interval=interval, auto_adjust=True)
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    df = data.copy().dropna(subset=['Close'])
    
    # タイムゾーン変換（日本とシカゴ）
    df.index = df.index.tz_convert('Asia/Tokyo')
    df['JST'] = df.index
    df['CST'] = df.index.tz_convert('America/Chicago')
    df = df.reset_index(drop=True)

    # --- 120本絶対基準ロジック ---
    
    # 1. 過去120本の中での最高値を特定（短期戦の天井）
    df['Rolling_High'] = df['Close'].rolling(window=lookback_window, min_periods=1).max()
    
    # 2. その最高値からのドローダウン率（%）を計算
    df['DD'] = (df['Close'] - df['Rolling_High']) / df['Rolling_High'] * 100
    
    # 3. 120本の枠内での「下落の偏差」を算出
    # 平均(Mean)は「この120本の中での平均的な下げ幅」を示す
    df['DD_Mean'] = df['DD'].rolling(window=lookback_window).mean()
    df['DD_Std'] = df['DD'].rolling(window=lookback_window).std()
    
    # 4. T-Score化（最高値付近なら高く、120本の中で異常に売られれば低くなる）
    df['T_Score'] = ((df['DD'] - df['DD_Mean']) / df['DD_Std']) * 10 + 50
    
    df['Velocity'] = df['Close'].diff()
    df['CHI_Label'] = df['CST'].dt.strftime('%H:%M')
    return df

df = load_data()

if not df.empty:
    # 直近の動き（64本＝16時間分）をズーム表示
    df_plot = df.tail(64).copy().reset_index(drop=True)
    
    if len(df_plot) > 0:
        latest = df_plot.iloc[-1]
        
        st.subheader(f"120-Bar Target High: ¥{latest['Rolling_High']:,.0f}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("PRICE", f"¥{latest['Close']:,.0f}", f"{latest['Velocity']:+.0f}")
        with col2:
            st.metric("BULL SCORE", f"{latest['T_Score']:.1f}")
        with col3:
            st.write(f"**JST:** {latest['JST'].strftime('%m/%d %H:%M')}")
            st.write(f"**CST:** {latest['CST'].strftime('%m/%d %H:%M')}")

        # チャート描画
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})

        tick_interval = 4
        tick_positions = np.arange(0, len(df_plot), tick_interval)
        tick_labels = [df_plot['CHI_Label'].iloc[i] for i in tick_positions]

        # 上段：価格と120本最高値
        ax1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=1.5, label="Price")
        ax1.plot(df_plot.index, df_plot['Rolling_High'], color='green', linestyle=':', alpha=0.6, label="120-Bar High")
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels([])
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(alpha=0.2)

        # 下段：絶対基準T-Score
        ax2.plot(df_plot.index, df_plot['T_Score'], color='royalblue', linewidth=1.8)
        ax2.axhline(T_SCORE_BULL_RECOVERY, color='green', linestyle='--', alpha=0.5)
        ax2.axhline(T_SCORE_LONG_ENTRY, color='orange', linestyle='--', alpha=0.6) # 30
        ax2.axhline(T_SCORE_CRITICAL, color='red', linestyle=':', alpha=0.8)       # 25
        
        # 買い場ゾーンを強調
        ax2.axhspan(15, 30, color='red', alpha=0.05)
        
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, rotation=45, fontsize=8)
        ax2.set_ylim(10, 90)
        ax2.grid(axis='x', alpha=0.2)

        st.pyplot(fig)
else:
    st.error("データ取得に失敗しました。")

# メリット：短期戦の最高値を「北極星」とし、そこからの乖離に100%集中できます。
