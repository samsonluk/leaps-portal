import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import google.generativeai as genai

# 1. Page Configuration
st.set_page_config(page_title="Free yfinance LEAPS Portal", page_icon="📈", layout="wide")

# 2. Secure API Configurations
if "GEMINI_FREE_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_FREE_KEY"])
else:
    st.error("Missing GEMINI_FREE_KEY in Streamlit Secrets!")
    st.stop()

st.title("📈 Free Tier Deep In-The-Money (DITM) LEAPS Portal")
st.subheader("Powered by yfinance (100% Free Engine) & Gemini")

# Calculate 1 to 1.5 year target window automatically
current_date = datetime.now()
target_start = current_date + timedelta(days=365)  
target_end = current_date + timedelta(days=545)    

st.info(f"📅 **Automated Window Tracking:** Target window between **{target_start.strftime('%B %Y')}** and **{target_end.strftime('%B %Y')}**.")

# 3. User Input
ticker_input = st.text_input("Enter Stock Ticker Symbol:", placeholder="e.g., AAPL, NVDA, MSFT").strip().upper()

if ticker_input:
    with st.spinner(f"Connecting to yfinance for {ticker_input}..."):
        try:
            # --- PHASE 1: FETCH CURRENT UNDERLYING PRICE ---
            ticker_obj = yf.Ticker(ticker_input)
            fast_info = ticker_obj.fast_info
            
            if not fast_info or 'lastPrice' not in fast_info:
                st.error(f"Could not retrieve stock metrics for ticker: {ticker_input}. Verify symbol.")
                st.stop()
                
            current_price = float(fast_info['lastPrice'])
            
            # --- PHASE 2: FETCH OPTIONS EXPIRATIONS ---
            expirations = ticker_obj.options
            if not expirations:
                st.error(f"No options chain data available on yfinance for {ticker_input}.")
                st.stop()
                
            # Filter expirations matching our strict 1-1.5 year window
            valid_expirations = []
            for exp_str in expirations:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
                if target_start <= exp_date <= target_end:
                    valid_expirations.append(exp_str)
                    
            # Fallback Security Rail: If window is empty, grab the furthest available date
            if not valid_expirations:
                valid_expirations = [expirations[-1]]
                
            selected_expiry = valid_expirations[0]
            
            # --- PHASE 3: FETCH AND PARSE OPTIONS MATRIX ---
            opt_chain = ticker_obj.option_chain(selected_expiry)
            calls_df = opt_chain.calls
            
            if calls_df.empty:
                st.error(f"No Call option contracts found for expiration date: {selected_expiry}")
                st.stop()
                
            # Filter for Deep In-The-Money (Strikes less than current stock price)
            final_df = calls_df[calls_df["strike"] < current_price].copy()
            
            if final_df.empty:
                st.error("No Deep In-The-Money options matched your filtration thresholds.")
                st.stop()
                
            # --- PHASE 4: STRUCTURAL METRICS & MATH ---
            # Fill empty bid/ask gaps with the last trade price if volume is thin
            final_df["bid"] = final_df["bid"].fillna(final_df["lastPrice"])
            final_df["ask"] = final_df["ask"].fillna(final_df["lastPrice"])
            
            final_df["Mid Premium"] = (final_df["bid"] + final_df["ask"]) / 2
            final_df["Intrinsic"] = current_price - final_df["strike"]
            final_df["Extrinsic"] = (final_df["Mid Premium"] - final_df["Intrinsic"]).clip(lower=0)
            final_df["Extrinsic Drag %"] = ((final_df["Extrinsic"] / current_price) * 100).round(2)
            final_df["Break Even"] = final_df["strike"] + final_df["Mid Premium"]
            final_df["B/E % Move"] = (((final_df["Break Even"] - current_price) / current_price) * 100).round(2)
            
            # Keep and format output presentation columns
            output_df = final_df[["strike", "Mid Premium", "openInterest", "Extrinsic Drag %", "B/E % Move"]].copy()
            output_df = output_df.rename(columns={"strike": "Strike", "openInterest": "Open Interest (OI)"})
            
            # Sort strikes from deep cushion to higher bounds, trim snapshot matrix for display
            output_df = output_df.sort_values(by="Strike", ascending=False).tail(8)
            data_payload = output_df.to_string(index=False)
            
            # --- PHASE 5: DISPLAY & AI ASSESSMENT ---
            st.success(f"### Live Market Sync: {ticker_input} is trading at ${current_price:.2f}")
            st.info(f"📦 Selected Expiration: **{selected_expiry}**")
            
            st.markdown("#### 📊 Official Options Chain Metrics (yfinance Feed)")
            st.dataframe(output_df, use_container_width=True, hide_index=True)
            
            with st.spinner("Invoking free AI layer to verify risk-reward anomalies..."):
                ai_prompt = f"""
                You are an options trading specialist. Analyze this DITM LEAPS Call data for {ticker_input}.
                Current Stock Price: ${current_price:.2f}
                Expiration Date: {selected_expiry}
                
                Data Matrix:
                {data_payload}
                
                Please provide:
                1. Identify which strike represents the 'Best Premium Value' (lowest structural extrinsic drag while keeping a deep strike cushion).
                2. Identify which strike represents 'Maximum Leverage' (highest relative capital efficiency near the upper bounds of the data pool).
                3. Examine the Open Interest (OI) column. Warn the user specifically about any strikes suffering from dangerously low order depth.
                """
                
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(ai_prompt)
                
                st.markdown("---")
                st.markdown("### 🤖 Automated AI Strategic Assessment")
                st.markdown(response.text)
                
        except Exception as e:
            st.error(f"Error executing portal automation sequence: {str(e)}")
