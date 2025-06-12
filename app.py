import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta # อาจจะต้อง pip install python-dateutil

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

        # --- สำคัญ: แก้ไข Timezone ของ Index ---
        # ถ้า Index มี Timezone (เช่น datetime64[ns, America/New_York])
        # ให้ลบ Timezone ออกเพื่อให้เป็น timezone-naive (datetime64[ns])
        # เพื่อให้เปรียบเทียบกับ datetime.datetime ได้โดยตรง
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)
            st.info(f"Removed timezone from {symbol} data index for comparison.") # ใช้ st.info แทน st.warning เพื่อลดความกังวล
        
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

        # --- การคำนวณวันที่ ---
        # เนื่องจากเราทำให้ prices.index เป็น timezone-naive แล้ว
        # เราจึงสามารถใช้ datetime.datetime.now() ซึ่งเป็น timezone-naive ได้โดยตรง
        today = datetime.datetime.now()
        # คำนวณวันที่ย้อนหลัง 1 เดือนอย่างแม่นยำ
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
        # ตรวจสอบว่า prices ไม่ว่างเปล่าและ Index เป็น DatetimeIndex ที่ไม่มี Timezone
        if not prices.empty and isinstance(prices.index, pd.DatetimeIndex):
            # การเปรียบเทียบจะทำงานได้อย่างถูกต้องแล้ว
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
                "Date": pd.to_datetime(filtered_prices.index).strftime('%Y-%m-%d'),
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
