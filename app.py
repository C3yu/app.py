import yfinance as yf
import streamlit as st
import pandas as pd
import datetime
from streamlit.column_config import LineChartColumn # Import สำหรับ Sparkline

# -------------------------------
# Stock List (Default) - เพิ่ม Salesforce เข้ามาใน Default แล้ว
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
six_months_ago = today - datetime.timedelta(days=180) # ใช้สำหรับดึงข้อมูล 6 เดือนสำหรับ Sparkline

# -------------------------------
# Data Fetching
# -------------------------------
@st.cache_data(ttl=3600) # Cache data for 1 hour to prevent excessive API calls
def get_real_prices(symbol):
    try:
        # ดึงข้อมูล 6 เดือนเพื่อรองรับ Sparkline และการคำนวณย้อนหลัง
        df = yf.Ticker(symbol).history(period="6mo", interval="1d")
        if df.empty:
            st.warning(f"⚠️ No historical data found for {symbol}. It might be a new listing or incorrect symbol.")
            return pd.Series()
        return df["Close"]
    except Exception as e:
        st.error(f"❌ Error fetching data for {symbol}: {e}")
        return pd.Series()

# -------------------------------
# Growth Calculation
# -------------------------------
def calc_growth(df, reference_date):
    try:
        # ตรวจสอบว่า df ไม่ว่างเปล่า และมีข้อมูลเพียงพอ
        if df.empty or len(df) < 2: # อย่างน้อย 2 วัน สำหรับ daily change, และมากกว่านั้นสำหรับ monthly
            return None

        # หาวันที่ใน df ที่ใกล้ที่สุดก่อนหรือเท่ากับ reference_date
        # ใช้ df.index.get_loc เพื่อหาตำแหน่งที่แม่นยำ หรือ fallback ไปที่การกรองแบบเดิม
        past_price_candidates = df.loc[df.index <= pd.to_datetime(reference_date)]
        
        if past_price_candidates.empty:
            return None # ไม่พบข้อมูลก่อนวันที่อ้างอิง

        past_price = past_price_candidates.iloc[-1]
        current_price = df.iloc[-1]

        if past_price == 0: # ป้องกัน ZeroDivisionError
            return None 

        growth = ((current_price - past_price) / past_price) * 100
        return round(growth, 2)
    except Exception as e:
        # st.error(f"Error in calc_growth: {e}") # สำหรับ Debug
        return None

def calc_daily_change(df):
    try:
        if len(df) < 2:
            return None
        today_price = df.iloc[-1]
        yesterday_price = df.iloc[-2]
        if yesterday_price == 0: # ป้องกัน ZeroDivisionError
            return None
        
        change = ((today_price - yesterday_price) / yesterday_price) * 100
        return round(change, 2)
    except Exception:
        return None

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="AI Agent Stock Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.title("🤖📊 AI Agent Stock Tracker")

# Header 1
st.header("แสดงผลราคาหุ้น และการเปลี่ยนแปลงตามช่วงเวลา")

# Command Input (ยังคงไว้ตาม workflow เดิม)
command = st.text_input("ป้อนคำสั่ง (เช่น 'AI agent stock')", "AI agent stock").strip().lower()

if command == "ai agent stock":
    # Header 2
    st.subheader("ค้นหาราคาหุ้น")
    stock_input = st.text_input("ป้อนสัญลักษณ์หุ้นที่ต้องการ (คั่นด้วยคอมมา, เช่น MSFT,GOOGL):")

    # กำหนดรายการหุ้นที่จะแสดงผล
    if stock_input:
        custom_symbols = [x.strip().upper() for x in stock_input.split(",") if x.strip()]
        stocks = {sym: default_stocks.get(sym, "Unknown") for sym in custom_symbols}
    else:
        stocks = default_stocks # แสดงหุ้นทั้งหมดที่มีลิสต์ไว้แล้ว

    # ประมวลผลและแสดงผล
    stocks_data = []
    
    for symbol, name in stocks.items():
        prices = get_real_prices(symbol)

        if prices.empty:
            # st.error ข้อความ Error จะถูกแสดงใน get_real_prices แล้ว
            continue 

        current_price = round(prices.iloc[-1], 2) if not prices.empty else None

        # คำนวณ % การเปลี่ยนแปลง
        growth_1d = calc_daily_change(prices)
        growth_1m = calc_growth(prices, one_month_ago)
        growth_3m = calc_growth(prices, three_months_ago)
        
        # เตรียมข้อมูลสำหรับ Sparkline (ใช้ข้อมูลราคา 6 เดือน)
        sparkline_data = prices.tolist() if not prices.empty else []

        stocks_data.append({
            "Symbol": symbol,
            "Company": name,
            "Price (USD)": current_price,
            "% Change (1 Day)": growth_1d,
            "History (1 Month)": prices.loc[prices.index >= pd.to_datetime(one_month_ago)].tolist() if not prices.empty else [], # ดึงข้อมูล 1 เดือน
            "History (3 Month)": prices.loc[prices.index >= pd.to_datetime(three_months_ago)].tolist() if not prices.empty else [], # ดึงข้อมูล 3 เดือน
            "% Change (1 Month)": growth_1m,
            "% Change (3 Month)": growth_3m,
            "Trend (6 Months)": sparkline_data # ข้อมูลสำหรับ Sparkline
        })

    stocks_df = pd.DataFrame(stocks_data)

    if not stocks_df.empty:
        # คำนวณ min/max สำหรับ LineChartColumn
        # ใช้ list comprehension เพื่อจัดการกรณีที่ sparkline_data อาจว่างเปล่า
        all_sparkline_values = [val for sublist in stocks_df["Trend (6 Months)"] if sublist for val in sublist]
        
        y_min_val = min(all_sparkline_values) if all_sparkline_values else None
        y_max_val = max(all_sparkline_values) if all_sparkline_values else None

        # จัดเรียงคอลัมน์ตามที่ต้องการ
        column_order = ["Company", "Price (USD)", "% Change (1 Day)", "% Change (1 Month)", "% Change (3 Month)", "Trend (6 Months)"]
        
        # กำหนดการแสดงผลคอลัมน์ โดยเฉพาะ Sparkline
        st.dataframe(
            stocks_df[column_order], # เลือกและเรียงคอลัมน์
            column_config={
                "Trend (6 Months)": LineChartColumn(
                    "Trend (6 Months)",
                    y_min=y_min_val, # ปรับ scale Y ให้เหมาะสม
                    y_max=y_max_val, # ปรับ scale Y ให้เหมาะสม
                    width="small",
                    height="small",
                    help="แสดงแนวโน้มราคาหุ้นในช่วง 6 เดือนที่ผ่านมา"
                ),
                "Price (USD)": st.column_config.NumberColumn("Price (USD)", format="$%.2f"),
                "% Change (1 Day)": st.column_config.NumberColumn("% Change (1 Day)", format="%.2f%%"),
                "% Change (1 Month)": st.column_config.NumberColumn("% Change (1 Month)", format="%.2f%%"),
                "% Change (3 Month)": st.column_config.NumberColumn("% Change (3 Month)", format="%.2f%%"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("ไม่พบข้อมูลหุ้นที่สามารถแสดงผลได้ โปรดตรวจสอบสัญลักษณ์หุ้นหรือการเชื่อมต่อ.")

else:
    st.info("⌨️ โปรดป้อนคำสั่ง 'AI agent stock' เพื่อเริ่มต้นการใช้งานโมดูลติดตามหุ้น")
