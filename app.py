import os
import sys
from typing import Optional
import pandas as pd

try:
    from marketdata import MarketDataClient, OutputFormat
except ImportError:
    print("Error: The 'marketdata' SDK is not installed.")
    print("Please install it via pip: pip install marketdata-app-sdk")
    sys.exit(1)


def fetch_options_chain(
    symbol: str, 
    side: Optional[str] = None, 
    strike_range: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Fetches the current options chain for a given underlying ticker symbol.
    
    Parameters:
        symbol (str): The underlying stock ticker (e.g., 'AAPL').
        side (str, optional): Filter by 'call' or 'put'. Defaults to None (both).
        strike_range (str, optional): Filter by moneyness ('itm', 'otm', 'atm'). 
                                      Defaults to None (all).
                                      
    Returns:
        pd.DataFrame: A pandas DataFrame containing the option chain data,
                      or None if an error occurs.
    """
    # 1. Check for API Token
    # The SDK automatically checks MARKETDATA_TOKEN, but explicit validation
    # provides a much cleaner, human-readable error message.
    token = os.environ.get("MARKETDATA_TOKEN")
    if not token:
        print("[-] Error: MARKETDATA_TOKEN environment variable is not set.")
        print("    Please set it in your environment before running this script.")
        print("    Linux/macOS: export MARKETDATA_TOKEN='your_api_key'")
        print("    Windows (CMD): set MARKETDATA_TOKEN=your_api_key")
        print("    Windows (PowerShell): $env:MARKETDATA_TOKEN='your_api_key'")
        return None

    print(f"[+] Initializing Market Data Client...")
    client = MarketDataClient(token=token)

    # Configure parameters dynamically based on arguments passed
    kwargs = {
        "symbol": symbol.upper(),
        "output_format": OutputFormat.DATAFRAME
    }
    
    if side:
        kwargs["side"] = side.lower()
    if strike_range:
        kwargs["range"] = strike_range.lower()

    print(f"[+] Requesting option chain for {kwargs['symbol']}...")
    try:
        # 2. Fetch data via the Python SDK
        chain_df = client.options.chain(**kwargs)
        
        # 3. Validate response
        if chain_df is None or chain_df.empty:
            print(f"[-] No options data returned for {symbol}. Check the ticker symbol or filters.")
            return None
            
        print(f"[+] Successfully retrieved {len(chain_df)} option contracts.")
        return chain_df

    except Exception as e:
        print(f"[-] An unexpected error occurred while fetching the data: {e}")
        return None


if __name__ == "__main__":
    # --- Configuration ---
    TARGET_TICKER = "AAPL"
    OPTION_SIDE = None          # Options: 'call', 'put', or None for both
    MONEYNESS_RANGE = "itm"     # Options: 'itm' (In the Money), 'otm', 'all', or None
    
    # --- Execution ---
    df = fetch_options_chain(
        symbol=TARGET_TICKER, 
        side=OPTION_SIDE, 
        strike_range=MONEYNESS_RANGE
    )
    
    # --- Output & Display ---
    if df is not None:
        print("\n=== Data Preview (First 10 Rows) ===")
        # Adjust pandas settings to prevent truncation in terminal output
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        
        print(df.head(10))
        
        # Optional: Save results to a CSV file
        output_filename = f"{TARGET_TICKER.lower()}_options_chain.csv"
        df.to_csv(output_filename)
        print(f"\n[+] Full dataset exported safely to: {output_filename}")
