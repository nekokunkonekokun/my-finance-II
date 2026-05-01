import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Mission Control [Pure Bull 25-30]", layout="wide")

# --- パラメータ設定 ---
ticker_sym = "NIY=F"
interval = "15m"
period = "7d"
lookback = 120  # 30時間の結界（ここでの高値を絶対基準にする）

st.title("🚀 Market Mission Control [Pure Bull Mode]")

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

    # 1. 120本の中での最高値を特定（北極星）
    df['High120'] = df['Close'].rolling(window=lookback, min_periods=1).max()
    
    # 2. 最高値からのドローダウン
    df['DD'] = (df['Close'] - df['High120']) / df['High120'] * 100
    
    # 3. 偏差値計算：スケーリングを「* 10」に戻して、25-30に刺さりやすくする
    df['DD_Mean'] = df['DD'].rolling(window=lookback).mean()
    df['DD_Std'] = df['DD'].rolling(window=lookback).std()
    df['T_Score'] = ((df['DD'] - df['DD_Mean']) / df['DD_Std']) * 10 + 50
    
    df['Velocity'] = df['Close'].diff()
    df['CHI_Label'] = df['CST'].dt.strftime('%H:%M')
    return df

df = load_data()

if not df.empty:
    # ズーム表示
    df_plot = df.tail(64).copy().reset_index(drop=True)
    latest = df_plot.iloc[-1]
    
    st.subheader(f"Current Target High: ¥{latest['High120']:,.0f}")
    
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

    # 上段：価格とターゲット
    ax1.plot(df_plot.index, df_plot['Close'], color='black', linewidth=1.5)
    ax1.plot(df_plot.index, df_plot['High120'], color='green', linestyle=':', alpha=0.6)
    ax1.set_xticks(tick_positions)
    ax1.set_xticklabels([])
    ax1.grid(alpha=0.2)

    # 下段：T-Score（入りどころ重視）
    ax2.plot(df_plot.index, df_plot['T_Score'], color='royalblue', linewidth=2)
    
    # 閾値ライン（30で検討、25で勝負）
    ax2.axhline(90, color='red', linestyle='--', alpha=0.7, label="Short Danger")
    ax2.axhline(30, color='orange', linestyle='--', alpha=0.8, label="Entry")
    ax2.axhline(25, color='red', linestyle='-', alpha=0.8, label="Critical")
    
    ax2.axhspan(15, 30, color='red', alpha=0.05) 
    ax2.set_ylim(10, 100)
    ax2.set_xticks(tick_positions)
    ax2.set_xticklabels(tick_labels, rotation=45, fontsize=8)
    ax2.grid(alpha=0.2)
    ax2.legend(loc='upper left', fontsize=8)

    st.pyplot(fig)
else:
    st.error("Data Error")

# メリット：物差しの長さを正常化したので、25-30ラインが再び「意味のある数字」になります。
# デメリット：爆騰時の数値が90付近で頭打ちになりやすくなります。
# ハルシネーションを疑え。
