import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai

# 1. Page Configuration
st.set_page_config(page_title="Free DITM LEAPS Portal", page_icon="📈", layout="wide")

# 2. Secure Free Backend Connection via Streamlit Secrets
if "GEMINI_FREE_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_FREE_KEY"])
else:
    genai.configure(api_key="PASTE_YOUR_FREE_GEMINI_KEY_HERE_IF_TESTING_LOCAL")

st.title("📈 Free Deep In-The-Money (DITM) LEAPS Portal")
st.subheader("Automated live chain scraping & AI analysis with zero user keys required.")

# Calculate 1 to 1.5 year target window automatically
current_date = datetime.now()
target_start = current_date + timedelta(days=365)  
target_end = current_date + timedelta(days=545)    

# 3. User Input
ticker_input = st.text_input("Enter Stock Ticker Symbol:", placeholder="e.g., AAPL, NVDA, MSFT").strip().upper()

if ticker_input:
    with st.spinner(f"Scraping live market options chains for {ticker_input}..."):
        try:
            # --- PHASE 1: FREE PYTHON LIVE DATA FETCHING ---
            asset = yf.Ticker(ticker_input)
            
            # Fetch current price
            price_history = asset.history(period="1d")
            if price_history.empty:
                st.error(f"Could not verify market pricing data for ticker: {ticker_input}")
                st.stop()
            current_price = round(price_history['Close'].iloc[-1], 2)
            
            # Filter for expiration dates 1 to 1.5 years away
            all_expirations = asset.options
            valid_expirations = []
            
            for exp in all_expirations:
                exp_date = datetime.strptime(exp, "%Y-%m-%d")
                if target_start <= exp_date <= target_end:
                    valid_expirations.append(exp)
            
            if not valid_expirations:
                valid_expirations = [all_expirations[-1]]
                
            selected_expiry = valid_expirations[0]
            
            # Grab the Call options chain data frame
            opt_chain = asset.option_chain(selected_expiry)
            calls = opt_chain.calls
            
            # Filter down to true deep ITM options (Strikes below current stock price)
            itm_calls = calls[calls['strike'] < current_price].copy()
            
            # Perform mathematical structural mappings
            itm_calls['midpoint'] = (itm_calls['bid'] + itm_calls['ask']) / 2
            itm_calls['intrinsic'] = current_price - itm_calls['strike']
            itm_calls['extrinsic'] = itm_calls['midpoint'] - itm_calls['intrinsic']
            itm_calls['extrinsic_drag_pct'] = round((itm_calls['extrinsic'] / current_price) * 100, 2)
            itm_calls['break_even'] = itm_calls['strike'] + itm_calls['midpoint']
            itm_calls['break_even_pct_move'] = round(((itm_calls['break_even'] - current_price) / current_price) * 100, 2)
            
            # Fill missing Open Interest numbers cleanly with 0
            itm_calls['openInterest'] = itm_calls['openInterest'].fillna(0).astype(int)
            
            # Grab relevant sample rows across the pricing spectrum to feed the AI (Now featuring openInterest)
            display_df = itm_calls[['strike', 'midpoint', 'openInterest', 'impliedVolatility', 'extrinsic_drag_pct', 'break_even_pct_move']].tail(8)
            
            # Rename columns for pristine table formatting
            formatted_df = display_df.rename(columns={
                'strike': 'Strike',
                'midpoint': 'Mid Premium',
                'openInterest': 'Open Interest (OI)',
                'impliedVolatility': 'IV',
                'extrinsic_drag_pct': 'Extrinsic Drag %',
                'break_even_pct_move': 'B/E % Move'
            })
            
            # Convert raw dataframe to a string segment for the LLM context pass
            data_payload = formatted_df.to_string(index=False)
            
            # --- PHASE 2: FREE AI STRATEGY RENDERING ---
            st.success(f"### Live Market Sync: {ticker_input} is trading at ${current_price}")
            st.info(f"📦 Selected Expiration: **{selected_expiry}**")
            
            # Show the raw math instantly to the user
            st.markdown("#### 📊 Live Scraped Options Chain Metrics")
            st.dataframe(formatted_df, use_container_width=True, hide_index=True)
            
            with st.spinner("Invoking free AI layer to cross-reference Open Interest thresholds..."):
                # Assemble context-specific prompt containing Open Interest figures
                ai_prompt = f"""
                You are an options trading specialist. Analyze this scraped DITM LEAPS Call data for {ticker_input}.
                Current Stock Price: ${current_price}
                Expiration Date: {selected_expiry}
                
                Data Matrix:
                {data_payload}
                
                Please provide:
                1. Identify which strike represents the 'Best Premium Value' (lowest structural extrinsic drag while keeping a deep strike cushion).
                2. Identify which strike represents 'Maximum Leverage' (highest relative capital efficiency near the upper bounds of the data pool).
                3. Examine the Open Interest (OI) column. Warn the user specifically about any strikes suffering from dangerously low order depth (e.g., OI under 100 contracts) which might result in predatory bid-ask spreads when trying to exit the trade.
                """
                
                # Call Gemini Flash model for completely free reasoning execution
                # NEW UPDATED LINE
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(ai_prompt)
                
                st.markdown("---")
                st.markdown("### 🤖 Automated AI Strategic Assessment")
                st.markdown(response.text)
                
        except Exception as e:
            st.error(f"Error executing portal automation sequence: {str(e)}")
