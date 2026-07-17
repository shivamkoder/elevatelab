# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import time
from crypto_tracker import CryptoPriceTracker

# Page config
st.set_page_config(page_title="Crypto Tracker", layout="wide")
st.title("📈 Crypto Price Tracker with Alerts")

# Initialize tracker
@st.cache_resource
def get_tracker():
    return CryptoPriceTracker()

tracker = get_tracker()

# --- SIDEBAR SETTINGS ---
st.sidebar.header("⚙️ Settings")
currency = st.sidebar.selectbox("Currency", ['usd', 'eur', 'gbp', 'jpy', 'inr'])
coin_limit = st.sidebar.slider("Number of Coins", 5, 50, 10)
refresh_rate = st.sidebar.selectbox("Refresh (seconds)", [15, 30, 60, 120], index=1)

st.sidebar.divider()

# --- ALERT SYSTEM (The feature you asked for) ---
st.sidebar.header("🔔 Set Price Alert")

# Get current data for the dropdown (we'll fetch it once)
if 'current_df' not in st.session_state or st.session_state.current_df.empty:
    st.session_state.current_df = tracker.get_top_coins(vs_currency=currency, limit=coin_limit)

if not st.session_state.current_df.empty:
    # Dropdown to select coin
    coin_names = st.session_state.current_df['Name'].tolist()
    selected_coin = st.sidebar.selectbox("Select Coin", coin_names)
    
    # Target price input
    target_price = st.sidebar.number_input("Target Price ($)", min_value=0.01, step=0.01, format="%.2f")
    
    # Email input
    alert_email = st.sidebar.text_input("Your Email for Alert")
    
    # Set Alert Button
    if st.sidebar.button("🚨 Set Alert"):
        if selected_coin and target_price > 0 and alert_email:
            # Store alert in session state
            if 'active_alerts' not in st.session_state:
                st.session_state.active_alerts = []
            
            # Get the current price for this coin
            coin_row = st.session_state.current_df[st.session_state.current_df['Name'] == selected_coin]
            if not coin_row.empty:
                current_price = coin_row.iloc[0]['Price']
                alert = {
                    'coin': selected_coin,
                    'coin_id': coin_row.iloc[0]['ID'],
                    'target': target_price,
                    'email': alert_email,
                    'current_price': current_price,
                    'triggered': False
                }
                st.session_state.active_alerts.append(alert)
                st.sidebar.success(f"✅ Alert set for {selected_coin} at ${target_price:,.2f}")
            else:
                st.sidebar.error("Coin not found. Please refresh.")
        else:
            st.sidebar.error("Please fill in all fields.")

    # Display Active Alerts
    if 'active_alerts' in st.session_state and st.session_state.active_alerts:
        st.sidebar.divider()
        st.sidebar.subheader("📋 Active Alerts")
        for i, alert in enumerate(st.session_state.active_alerts):
            if not alert['triggered']:
                st.sidebar.write(f"• {alert['coin']} @ ${alert['target']:,.2f} → {alert['email']}")

# --- MAIN CONTENT ---
# Fetch fresh data
with st.spinner("Fetching live data..."):
    df = tracker.get_top_coins(vs_currency=currency, limit=coin_limit)
    
    if df.empty:
        st.warning("⚠️ Could not fetch data. Check your internet connection.")
        st.stop()
    
    # Update session state
    st.session_state.current_df = df

# ---- CHECK ALERTS ----
if 'active_alerts' in st.session_state:
    for alert in st.session_state.active_alerts:
        if not alert['triggered']:
            # Get current price for this coin
            coin_data = df[df['Name'] == alert['coin']]
            if not coin_data.empty:
                current_price = coin_data.iloc[0]['Price']
                alert['current_price'] = current_price
                
                # Check if threshold is met
                if current_price >= alert['target']:
                    st.sidebar.warning(f"🚨 {alert['coin']} hit ${current_price:,.2f}! Sending alert...")
                    # Send email
                    success = tracker.send_alert_email(
                        alert['coin'],
                        current_price,
                        alert['target'],
                        alert['email']
                    )
                    if success:
                        alert['triggered'] = True
                        st.sidebar.success(f"✅ Alert sent for {alert['coin']}")

# --- DISPLAY TABLE ---
st.subheader(f"Top {coin_limit} Coins ({currency.upper()})")

# Color formatting for price changes
def color_change(val):
    if val > 0:
        return 'color: green'
    elif val < 0:
        return 'color: red'
    return 'color: gray'

styled_df = df.style.applymap(color_change, subset=['24h Change (%)'])
st.dataframe(styled_df, use_container_width=True)

# --- MARKET CAP BAR CHART ---
st.subheader("💰 Market Cap Distribution")
fig_bar = px.bar(df, x='Name', y='Market Cap', 
                 title=f"Market Cap in {currency.upper()}")
st.plotly_chart(fig_bar, use_container_width=True)

# --- HISTORICAL PRICE CHART ---
st.subheader("📉 Historical Price Trend")
selected_coin_for_chart = st.selectbox("Select coin for chart", df['Name'].tolist(), key="chart_select")

if selected_coin_for_chart:
    coin_id = df[df['Name'] == selected_coin_for_chart]['ID'].values[0]
    history = tracker.get_coin_history(coin_id, vs_currency=currency, days=30)
    
    if not history.empty:
        fig_line = px.line(history, x='timestamp', y='price', 
                           title=f"{selected_coin_for_chart} - Last 30 Days ({currency.upper()})")
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.warning("No historical data available for this coin.")

# --- AUTO REFRESH LOGIC ---
time.sleep(refresh_rate)
st.rerun()