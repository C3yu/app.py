import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
import pytz # สำคัญ: คุณจะต้องติดตั้งไลบรารี pytz ด้วย (pip install pytz)

# --- Configuration / Page Setup ---
st.set_page_config(layout="wide")
st.title("Stock Information Dashboard")

# --- User Input ---
st.sidebar.header("Select Stock")
# เพิ่ม Salesforce (CRM) เข้าไปในตัวเลือกหุ้นตามที่แจ้งไว้
stock_options = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "JPM", "V", "PG", "UNH", "HD", "DIS", "NFLX", "ADBE", "PYPL", "CMCSA", "INTC", "CSCO", "PEP", "KO", "BAC", "WMT", "XOM", "CVX", "LLY", "MRK", "PFE", "ABBV", "COST", "SBUX", "CRM"
]
selected_symbol = st.sidebar.selectbox("Choose a stock symbol:", stock_options)

# --- Fetch Stock Data Function ---
@st.cache_data(ttl=3600) # แคชข้อมูล 1 ชั่วโมงเพื่อลดการเรียกใช้ API ซ้ำซ้อน
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # ดึงข้อมูลย้อนหลัง 1 ปี (รายวัน)
        data = ticker.history(period="1y")
        if data.empty:
            st.error(f"No historical data found for {symbol}. Please check the symbol.")
            return None

        # --- สำคัญ: ไม่ต้องลบ Timezone ออกจาก data.index อีกต่อไป ---
        # เราจะทำให้ one_month_ago เป็น Timezone เดียวกันแทน

        return data
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return None

# --- Main Application Logic ---
if selected_symbol:
    stock_data = get_stock_data(selected_symbol)

    if stock_data is not None:
        # แยกเฉพาะราคาปิด 'Close'
        prices = stock_data['Close']

        # --- การคำนวณวันที่: ทำให้เป็น Timezone-aware เหมือนกับข้อมูล ---
        # 1. ตรวจสอบ Timezone ของข้อมูลหุ้น
        data_timezone = prices.index.tz
        
        if data_timezone is None:
            # กรณีที่ data.index ไม่มี timezone (ซึ่งไม่ควรเกิดขึ้นกับ yfinance โดยทั่วไป)
            # เราจะใช้ timezone-naive เหมือนเดิม เพื่อให้โค้ดไม่พัง
            st.warning("Stock data index does not have a timezone. Proceeding with timezone-naive comparison.")
            today = datetime.datetime.now()
            one_month_ago = today - relativedelta(months=1)
        else:
            # 2. แปลง datetime.datetime.now() ให้เป็น Timezone-aware ใน Timezone เดียวกัน
            # ตัวอย่าง: America/New_York
            st.info(f"Localizing date calculations to data's timezone: {data_timezone}")
            
            # Use tz_localize(None) first to ensure it's naive before localizing,
            # or directly use datetime.datetime.now() and then localize it.
            
            # This is the most common and robust way to get current time in a specific timezone
            today = datetime.datetime.now(data_timezone)
            one_month_ago = today - relativedelta(months=1)

        # --- เตรียมข้อมูลสำหรับการแสดงผล ---
        stock_info = {
            "Symbol": selected_symbol,
            "Current Price": f"{prices.iloc[-1]:,.2f}" if not prices.empty else "N/A", # Format เป็นทศนิยม 2 ตำแหน่ง
            "Previous Close": f"{prices.iloc[-2]:,.2f}" if len(prices) >= 2 else "N/A",
            "Volume": f"{stock_data['Volume'].iloc[-1]:,.0f}" if not stock_data['Volume'].empty else "N/A", # Format เป็นจำนวนเต็ม
        }

        # ประวัติราคา (1 เดือน) - ตรรกะการเปรียบเทียบที่แก้ไขแล้ว
        history_one_month = []
        # ตรวจสอบว่า prices ไม่ว่างเปล่าและ Index เป็น DatetimeIndex
        if not prices.empty and isinstance(prices.index, pd.DatetimeIndex):
            # การเปรียบเทียบจะทำงานได้อย่างถูกต้องแล้ว เพราะทั้งสองฝ่ายเป็น Timezone-aware ใน Timezone เดียวกัน
            history_one_month = prices.loc[prices.index >= one_month_ago].tolist()
        else:
            if prices.empty:
                st.warning("No price data available to generate 1-month history.")
            else:
                st.error("Price index is not in datetime format or could not be processed for history.")


        # --- แสดงข้อมูล ---
        st.subheader(f"Stock Information for {selected_symbol}")
        st.write(stock_info)

        st.subheader("Price Chart (Last 1 Year)")
        if not stock_data.empty:
            st.line_chart(stock_data['Close'])
        else:
            st.info("No data to display chart.")

        st.subheader("Price History (Last 1 Month)")
        if history_one_month:
            # สร้าง DataFrame เพื่อแสดงประวัติราคาให้ดูง่ายขึ้น
            # ตรวจสอบอีกครั้งว่า prices.index ยังคงเป็น DatetimeIndex ก่อนนำไปกรอง
            filtered_prices = prices.loc[prices.index >= one_month_ago]
            history_df = pd.DataFrame({
                "Date": pd.to_datetime(filtered_prices.index).strftime('%Y-%m-%d'), # Convert to string for display
                "Close Price": [f"{p:,.2f}" for p in history_one_month] # Format เป็นทศนิยม 2 ตำแหน่ง
            })
            st.dataframe(history_df, use_container_width=True) # ให้ตารางปรับขนาดตามความกว้าง
        else:
            st.info("No price history for the last month available or data is insufficient.")

        # --- รายละเอียดหุ้นเพิ่มเติม (ตัวอย่าง) ---
        st.subheader("Company Information")
        try:
            ticker_info = yf.Ticker(selected_symbol).info
            if ticker_info:
                st.write(f"**Company Name:** {ticker_info.get('longName', 'N/A')}")
                st.write(f"**Sector:** {ticker_info.get('sector', 'N/A')}")
                st.write(f"**Industry:** {ticker_info.get('industry', 'N/A')}")
                
                market_cap = ticker_info.get('marketCap')
                if isinstance(market_cap, (int, float)):
                    st.write(f"**Market Cap:** {market_cap:,.0f}")
                else:
                    st.write(f"**Market Cap:** {market_cap if market_cap else 'N/A'}")
                    
                st.write(f"**Website:** {ticker_info.get('website', 'N/A')}")
                # st.write(f"**Description:** {ticker_info.get('longBusinessSummary', 'N/A')}") # อาจจะยาวเกินไป
            else:
                st.info("Additional company information not available.")
        except Exception as e:
            st.error(f"Could not fetch additional company information: {e}")

    else:
        st.warning("Please select a stock symbol to view its information.")
