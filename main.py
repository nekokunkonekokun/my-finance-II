import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

st.set_page_config(page_title="Dual Logic Mission Control", layout="wide")

ticker_sym = "NIY=F"
interval = "30m"
period = "1mo"
ma_window = 25
std_window = 160

INERTIA_THRESHOLD = 500
T_SCORE_OVERHEAT = 75
VELOCITY_FADE = 100

st.title("🚀 Market Mission Control")

@st.cache_data(ttl=600)
def load_data():
    data = yf.download(ticker_sym, period=period, interval=interval, auto_adjust=True)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    df = data.copy().dropna(subset=['Close']).reset_index()

    df['MA25'] = df['Close'].rolling(window=ma_window).mean()
    df['Bias'] = (df['Close'] - df['MA25']) / df['MA25'] * 100
    df['Bias_Mean'] = df['Bias'].rolling(window=std_window).mean()
    df['Bias_Std'] = df['Bias'].rolling(window=std_window).std()
    df['T_Score'] = ((df['Bias'] - df['Bias_Mean']) / df['Bias_Std']) * 10 + 50
    df['Velocity'] = df['Close'].diff()

    df['Inertia_UP'] = df['Velocity'] >= INERTIA_THRESHOLD
    df['Inertia_DOWN'] = df['Velocity'] <= -INERTIA_THRESHOLD
    df['Short_Signal'] = (df['T_Score'] >= T_SCORE_OVERHEAT) & (df['Velocity'].shift(1) > 300) & (df['Velocity'] < VELOCITY_FADE)

    df['CHI_DT'] = df['Datetime'] - timedelta(hours=14)
    df['CHI_Label'] = df['CHI_DT'].apply(lambda x: int(f"{x.hour}{x.minute // 10}"))
    return df

df = load_data()
last_time = df['Datetime'].max()
df_plot = df[df['Datetime'] >= (last_time - timedelta(days=2))].copy().reset_index(drop=True)
latest = df_plot.iloc[-1]

st.subheader("Mission Control Panel")
col1, col2, col3 = st.columns(3)
col1.metric("PRICE", f"¥{latest['Close']:,.0f}", f"{latest['Velocity']:+.0f}")
col2.metric("T-SCORE", f"{latest['T_Score']:.1f}")
col3.write(f"**Update(CHI):** {latest['CHI_DT'].strftime('%Y/%m/%d %H:%M')}")

c_a, c_b = st.columns(2)
with c_a:
    st.info("**LOGIC-A: BULLISH INERTIA**")
    if latest['Velocity'] >= INERTIA_THRESHOLD:
        st.error("!!! RED INERTIA (UP) !!!\n\nADVICE: BUY!")
    elif latest['Velocity'] <= -INERTIA_THRESHOLD:
        st.info("!!! BLUE INERTIA (DOWN) !!!\n\nADVICE: DROP!")
    else:
        st.write("STATUS: CRUISING SPEED")

with c_b:
    st.info("**LOGIC-B: BEARISH SNIPER**")
    if latest['T_Score'] >= T_SCORE_OVERHEAT and latest['Velocity'] < VELOCITY_FADE:
        st.warning("!!! SNIPER SHORT READY !!!\n\nADVICE: SHOOT!")
    else:
        st.write("STATUS: STAY CALM")

tick_interval = 4
tick_positions = list(range(0, len(df_plot), tick_interval))
tick_labels = [str(df_plot['CHI_Label'].iloc[i]) for i in tick_positions]
x_vals = np.arange(len(df_plot))

# Chart 1
st.subheader("1. Long position: Inertia & Deviation Grid")
fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

ax1_1.plot(x_vals, df_plot['Close'], color='black', linewidth=2)
ax1_1.plot(x_vals, df_plot['MA25'], color='orange', linestyle='--', alpha=0.7)
ax1_1.scatter(df_plot[df_plot['Inertia_UP']].index, df_plot[df_plot['Inertia_UP']]['Close'], color='red', s=100)
ax1_1.scatter(df_plot[df_plot['Inertia_DOWN']].index, df_plot[df_plot['Inertia_DOWN']]['Close'], color='blue', s=100)

ax1_2.plot(x_vals, df_plot['T_Score'], color='darkviolet')
ax1_2.axhline(70, color='red', alpha=0.5)
ax1_2.axhline(30, color='green', alpha=0.5)

ax1_2.set_xticks(tick_positions)
ax1_2.set_xticklabels(tick_labels, fontsize=8)
ax1_2.grid(True, axis='x', alpha=0.2)

# 強制描画更新
plt.draw()
st.pyplot(fig1)

# Chart 2
st.subheader("2. Short position: Gravity Sniper Scope")
fig2, ax2 = plt.subplots(figsize=(10, 5))
ax2.plot(x_vals, df_plot['T_Score'], color='darkviolet', linewidth=2)
ax2.axhline(y=T_SCORE_OVERHEAT, color='crimson', linestyle='--')
ax2.scatter(df_plot[df_plot['Short_Signal']].index, df_plot[df_plot['Short_Signal']]['T_Score'], color='blue', s=200, marker='v')

ax2.set_xticks(tick_positions)
ax2.set_xticklabels(tick_labels, fontsize=8)
ax2.grid(True, axis='x', alpha=0.2)

plt.draw()
st.pyplot(fig2)
