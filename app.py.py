import yfinance as yf
import streamlit as st
import pandas as pd
import datetime

# -------------------------------
# Stock List (Default)
# -------------------------------
default_stocks = {
    "GOOGL": "Alphabet",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "CRM": "Salesforce"
}

# -------------------------------
# Date Setup
# -------------------------------
today = datetime.date.today()
one_month_ago = today - datetime.timedelta(days=30)
three_months_ago = today - datetime.timedelta(days=90)
six_months_ago = today - datetime.timedelta(days=180)

# -------------------------------
# Sample Static Data (Fallback)
# -------------------------------
def get_real_prices(symbol):
    try:
        df = yf.Ticker(symbol).history(period="6mo")
        return df["Close"]
    except:
        return pd.Series()
    
# -------------------------------
# Growth Calculation
# -------------------------------
def calc_growth(prices, reference_date):
    if prices.empty:
        return None
    # หา index ที่ใกล้ที่สุดก่อนหรือเท่ากับ reference_date
    closest_date = prices.index[prices.index <= reference_date].max()
    if pd.isna(closest_date):
        return None
    past_price = prices.loc[closest_date]
    current_price = prices.iloc[-1]
    growth = ((current_price - past_price) / past_price) * 100
    return round(growth, 2)

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="AI Agent Stock Dashboard", layout="wide")
st.title("🤖📊 AI Agent Stock Tracker")

# Command Input
command = st.text_input("Command name (e.g., AI agent stock)", "AI agent stock")

if command.strip().lower() == "ai agent stock":
    st.subheader("🧠 Module: Stock Checker")
    stock_input = st.text_input("Enter stock symbols (comma-separated, e.g., MSFT,GOOGL):")

    # Determine stock list
    if stock_input:
        custom_symbols = [x.strip().upper() for x in stock_input.split(",") if x.strip()]
        stocks = {sym: default_stocks.get(sym, "Unknown") for sym in custom_symbols}
    else:
        stocks = default_stocks

    # Process and Display
    stocks_data = []
    alerts = []

for symbol, name in stocks.items():
    prices = get_real_prices(symbol)

    if prices.empty:
        st.error(f"❌ Cannot load data for {symbol}. Please check the symbol or your connection.")
        continue  # ข้าม symbol นี้ไป

    growth_1m = calc_growth(prices, one_month_ago)
    growth_3m = calc_growth(prices, three_months_ago)
    growth_6m = calc_growth(prices, six_months_ago)
    current_price = round(prices.iloc[-1], 2)

    if growth_1m is not None and growth_1m < -5:
        alerts.append(f"⚠️ Alert: {name} ({symbol}) has dropped {growth_1m}% in the past 1 month.")

    stocks_data.append({
        "Symbol": symbol,
        "Company": name,
        "Price (USD)": current_price,
        "1M Growth %": growth_1m,
        "3M Growth %": growth_3m,
        "6M Growth %": growth_6m
    })

    stocks_df = pd.DataFrame(stocks_data)

    st.dataframe(stocks_df, use_container_width=True)

    # Show Alerts
    if alerts:
        st.subheader("⚠️ Alerts")
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("✅ No critical price drops detected in the last 1 month.")

    # Optional: Download CSV
    st.download_button(
        label="📥 Download CSV",
        data=stocks_df.to_csv(index=False),
        file_name="ai_agent_stocks.csv",
        mime="text/csv",
        key="download_button_csv"
    )
else:
    st.info("⌨️ Enter a valid command to start using the stock tracker module.")
