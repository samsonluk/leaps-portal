import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai

# 1. Page Configuration
st.set_page_config(page_title="Alpha Vantage DITM LEAPS Portal", page_icon="📈", layout="wide")

# 2. Secure API Configurations
if "GEMINI_FREE_KEY" in st.secrets and "ALPHA_VANTAGE_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_FREE_KEY"])
    AV_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
else:
    st.error("Missing API Keys (ALPHA_VANTAGE_KEY or GEMINI_FREE_KEY) in Streamlit Secrets!")
    st.stop()

st.title("📈 Alpha Vantage Deep In-The-Money (DITM) LEAPS Portal")
st.subheader("Official Alpha Vantage data feed with automated AI strategy mapping.")

# Calculate 1 to 1.5 year target window automatically (targeting June 2026 anchor)
current_date = datetime.now()
target_start = current_date + timedelta(days=365)  
target_end = current_date + timedelta(days=545)    

st.info(f"📅 **Automated Window Tracking:** Target window between **{target_start.strftime('%B %Y')}** and **{target_end.strftime('%B %Y')}**.")

# 3. User Input
ticker_input = st.text_input("Enter Stock Ticker Symbol:", placeholder="e.g., AAPL, NVDA, MSFT").strip().upper()

if ticker_input:
    with st.spinner(f"Fetching option chains from Alpha Vantage for {ticker_input}..."):
        try:
            # --- PHASE 1: FETCH CURRENT REAL-TIME/DELAYED UNDERLYING PRICE ---
            price_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker_input}&apikey={AV_KEY}"
            price_res = requests.get(price_url).json()
            
            if "Global Quote" not in price_res or not price_res["Global Quote"]:
                st.error(f"Could not retrieve a valid stock quote for ticker: {ticker_input}. Verify symbol or API limits.")
                st.stop()
                
            current_price = float(price_res["Global Quote"]["05. price"])
            
            # --- PHASE 2: FETCH REAL-TIME OPTIONS CHAIN ---
            options_url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={ticker_input}&apikey={AV_KEY}"
            options_res = requests.get(options_url).json()
            
            if "data" not in options_res or not options_res["data"]:
                st.error(f"No option chain data returned for {ticker_input}. Alpha Vantage standard tier may be rate-limiting.")
                st.stop()
                
            raw_options = options_res["data"]
            
            # --- PHASE 3: PARSE AND FILTER FOR DITM LEAPS ---
            parsed_data = []
            valid_expirations = set()
            
            for contract in raw_options:
                # Isolate Calls only
                if contract.get("type") != "call":
                    continue
                    
                # Date validations
                exp_str = contract.get("expiration")
                if not exp_str:
                    continue
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
                
                # Check if expiration lands inside our strict 1 to 1.5 year window
                if target_start <= exp_date <= target_end:
                    valid_expirations.add(exp_str)
                    
                    strike = float(contract.get("strike", 0))
                    # Filter for Deep ITM (Strikes below current asset value)
                    if strike < current_price:
                        # Grab core pricing numbers
                        bid = float(contract.get("bid", 0) or 0)
                        ask = float(contract.get("ask", 0) or 0)
                        oi = int(contract.get("open_interest", 0) or 0)
                        
                        midpoint = (bid + ask) / 2 if (bid + ask) > 0 else (current_price - strike) * 1.02
                        intrinsic = current_price - strike
                        extrinsic = max(0.0, midpoint - intrinsic)
                        extrinsic_drag_pct = round((extrinsic / current_price) * 100, 2)
                        break_even = strike + midpoint
                        be_pct_move = round(((break_even - current_price) / current_price) * 100, 2)
                        
                        parsed_data.append({
                            "Expiration": exp_str,
                            "Strike": strike,
                            "Mid Premium": round(midpoint, 2),
                            "Open Interest (OI)": oi,
                            "Extrinsic Drag %": extrinsic_drag_pct,
                            "B/E % Move": be_pct_move
                        })
            
            if not parsed_data:
                st.error("No valid DITM LEAPS contracts found matching the 1-1.5 year target window rules.")
                st.stop()
                
            # Convert to Dataframe
            all_options_df = pd.DataFrame(parsed_data)
            
            # Group data to target the absolute nearest valid contract expiration month inside the window
            target_expiry = sorted(list(valid_expirations))[0]
            final_df = all_options_df[all_options_df["Expiration"] == target_expiry].copy()
            
            # Sort by strike and trim to a clear snapshot block for presentation and context size limits
            final_df = final_df.sort_values(by="Strike", ascending=False).tail(8)
            
            # Drop the redundant date column from the preview matrix
            preview_df = final_df.drop(columns=["Expiration"])
            data_payload = preview_df.to_string(index=False)
            
            # --- PHASE 4: RENDER & EXECUTE AI OVERLAY ---
            st.success(f"### Live Market Sync: {ticker_input} is trading at ${current_price:.2f}")
            st.info(f"📦 Selected Expiration: **{target_expiry}**")
            
            st.markdown("#### 📊 Official Options Chain Metrics (Alpha Vantage Feed)")
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
            
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
