import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai

# 1. Page Configuration
st.set_page_config(page_title="Market Data DITM LEAPS Portal", page_icon="📈", layout="wide")

# 2. Secure API Configurations from Streamlit Secrets
if "GEMINI_FREE_KEY" in st.secrets and "MARKETDATA_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_FREE_KEY"])
    MD_KEY = st.secrets["MARKETDATA_API_KEY"]
else:
    st.error("Missing API Keys (MARKETDATA_API_KEY or GEMINI_FREE_KEY) in Streamlit Secrets!")
    st.stop()

st.title("📈 Free Tier Deep In-The-Money (DITM) LEAPS Portal")
st.subheader("Powered by MarketData App (Free Options API) & Gemini")

# Calculate 1 to 1.5 year target window automatically
current_date = datetime.now()
target_start = current_date + timedelta(days=365)  
target_end = current_date + timedelta(days=545)    

st.info(f"📅 **Automated Window Tracking:** Target window between **{target_start.strftime('%B %Y')}** and **{target_end.strftime('%B %Y')}**.")

# 3. User Input
ticker_input = st.text_input("Enter Stock Ticker Symbol:", placeholder="e.g., AAPL, NVDA, MSFT").strip().upper()

if ticker_input:
    with st.spinner(f"Fetching option chains from MarketData for {ticker_input}..."):
        try:
            # --- PHASE 1: FETCH CURRENT UNDERLYING PRICE ---
            price_url = f"https://api.marketdata.app/v1/stocks/quotes/{ticker_input}/?token={MD_KEY}"
            price_res = requests.get(price_url).json()
            
            # --- INSTANT DEBUG PROTECTION ---
            if "status" in price_res and price_res["status"] == "ERROR":
                st.error(f"🛑 **MarketData API Error:** {price_res.get('message', 'Unknown Error')}")
                st.stop()
                
            if "s" in price_res and price_res["s"] != "ok":
                st.error(f"❌ **MarketData Server Notification:** {price_res.get('errmsg', 'No data available for this ticker.')}")
                st.stop()
                
            if "last" not in price_res or not price_res["last"]:
                st.error("⚠️ **Unexpected Response Grid Layout.** Raw server output displayed below:")
                st.json(price_res)  # This forces your portal screen to show the exact error message
                st.stop()
            # ---------------------------------
                
            current_price = float(price_res["last"][0])
            
            # --- PHASE 2: FETCH OPTIONS CHAIN ---
            chain_url = f"https://api.marketdata.app/v1/options/chain/{ticker_input}/?expiration=all&side=call&token={MD_KEY}"
            chain_res = requests.get(chain_url).json()
            
            if "status" in chain_res and chain_res["status"] == "ERROR":
                st.error(f"API Error: {chain_res.get('message', 'Failed to retrieve options data')}")
                st.stop()
                
            if "underlying" not in chain_res and "updated" not in chain_res:
                st.error(f"No option chain data returned for {ticker_input}. You may have exhausted your 100 daily credits.")
                st.stop()
                
            # --- PHASE 3: PARSE AND FILTER FOR DITM LEAPS ---
            # Rebuilding flat parallel arrays to prevent 'final_df not defined' error
            raw_df = pd.DataFrame({
                "Side": chain_res.get("side", []),
                "Expiration": chain_res.get("expiration", []),
                "Strike": [float(s) for s in chain_res.get("strike", [])],
                "Bid": [float(b) for b in chain_res.get("bid", [])],
                "Ask": [float(a) for a in chain_res.get("ask", [])],
                "OI": [int(o) for o in chain_res.get("openInterest", [])]
            })
            
            # Step 1: Force filter out everything except Calls
            raw_df = raw_df[raw_df["Side"] == "call"].copy()
            
            # Step 2: Safely parse text timestamps to dates
            raw_df["Exp_Date"] = pd.to_datetime(raw_df["Expiration"], errors="coerce")
            
            # Step 3: Run the 1 to 1.5 year target date filtering window
            leaps_df = raw_df[(raw_df["Exp_Date"] >= pd.to_datetime(target_start)) & 
                               (raw_df["Exp_Date"] <= pd.to_datetime(target_end))].copy()
            
            # Fallback Rail: If the free tier cuts far forward options short, grab furthest available
            if leaps_df.empty and not raw_df.empty:
                max_date = raw_df["Exp_Date"].max()
                leaps_df = raw_df[raw_df["Exp_Date"] == max_date].copy()
            
            if leaps_df.empty:
                st.error("No valid options contracts whatsoever were found for this asset.")
                st.stop()
                
            # Isolate the targeted expiration date layer
            target_expiry = leaps_df["Expiration"].min()
            final_df = leaps_df[leaps_df["Expiration"] == target_expiry].copy()
            
            # Step 4: Filter for Deep In-The-Money (Strikes less than current stock price)
            final_df = final_df[final_df["Strike"] < current_price].copy()
            
            if final_df.empty:
                st.error("No Deep In-The-Money options matched your filtration thresholds (Strikes are all above current price).")
                st.stop()
                
            # --- PHASE 4: STRUCTURAL METRICS & MATH ---
            final_df["Mid Premium"] = (final_df["Bid"] + final_df["Ask"]) / 2
            final_df["Intrinsic"] = current_price - final_df["Strike"]
            final_df["Extrinsic"] = (final_df["Mid Premium"] - final_df["Intrinsic"]).clip(lower=0)
            final_df["Extrinsic Drag %"] = ((final_df["Extrinsic"] / current_price) * 100).round(2)
            final_df["Break Even"] = final_df["Strike"] + final_df["Mid Premium"]
            final_df["B/E % Move"] = (((final_df["Break Even"] - current_price) / current_price) * 100).round(2)
            
            # Keep and format output presentation columns
            output_df = final_df[["Strike", "Mid Premium", "OI", "Extrinsic Drag %", "B/E % Move"]].copy()
            output_df = output_df.rename(columns={"OI": "Open Interest (OI)"})
            
            # Sort strikes from deep cushion to higher bounds, trim snapshot matrix for display
            output_df = output_df.sort_values(by="Strike", ascending=False).tail(8)
            data_payload = output_df.to_string(index=False)
            
            # --- PHASE 5: DISPLAY & AI ASSESSMENT ---
            st.success(f"### Live Market Sync: {ticker_input} is trading at ${current_price:.2f}")
            st.info(f"📦 Selected Expiration: **{target_expiry}**")
            
            st.markdown("#### 📊 Official Options Chain Metrics (MarketData Feed)")
            st.dataframe(output_df, use_container_width=True, hide_index=True)
            
            with st.spinner("Invoking free AI layer to verify risk-reward anomalies..."):
                ai_prompt = f"""
                You are an options trading specialist. Analyze this DITM LEAPS Call data for {ticker_input}.
                Current Stock Price: ${current_price:.2f}
                Expiration Date: {target_expiry}
                
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
