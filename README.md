# 📈 Deep In-The-Money (DITM) LEAPS Portal

A lightweight, zero-friction financial dashboard that automates the evaluation of long-dated, deep in-the-money Call options as capital-efficient stock substitutes. 

Built with **Python**, **Streamlit**, and **Google Gemini Flash**, this application eliminates manual option-chain scrolling by scraping real-time options data, executing intrinsic/extrinsic structural math, and utilizing AI to isolate optimal value vs. leverage entries.

---

## 🎯 What It Does (Single-Input Automation)

Simply input a stock ticker (e.g., `NVDA`, `AAPL`), and the app instantly executes a complete options-trading analysis pipeline:

1. **Automated Expiration Targeting:** Detects the current market price and dynamically isolates the standard monthly option chains sitting precisely **1 to 1.5 years out** from today's date.
2. **Structural Math Scraper:** Filters the chain for deep ITM strikes and calculates crucial stock-replacement metrics:
   * **Extrinsic Drag %** (The exact time-decay premium "waste" relative to the stock price).
   * **Break-Even % Move** (The exact margin the underlying asset must gain to reach profitability).
   * **Open Interest (OI) Depth** (Live contract counts to verify market participation).
3. **Dual-Track AI Strategy Engine:** Hands the data matrix to an LLM reasoning layer to pinpoint:
   * **The "Best Premium Value" Strike:** Maximum stock replication with the absolute lowest structural time-decay cost.
   * **The "Maximum Leverage" Strike:** The optimal balance of low capital outlay while maintaining valid stock-substitute characteristics.
4. **Liquidity Guardrails:** Automatically flags low Open Interest danger zones to protect users from predatory bid-ask spreads.

---

## 🛠️ Tech Stack & Deployment

* **Frontend/UI:** Streamlit (Hosted via Streamlit Community Cloud)
* **Data Fetching:** `yfinance` (100% free financial scraping api)
* **AI Layer:** Google GenAI SDK (`gemini-1.5-flash`)
* **Cost To Run:** **$0.00** (Utilizes free open-source math engines and Gemini's free API rate limits).

---

## 🚀 Quick Start

1. Clone the repo.
2. Add your free `GEMINI_FREE_KEY` to your local environment or Streamlit Secrets.
3. Run `streamlit run app.py`.
