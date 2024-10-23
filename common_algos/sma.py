import os
import time
from alpaca_trade_api.rest import REST, TimeFrame
from dotenv import load_dotenv
from decimal import Decimal, ROUND_DOWN
import pandas as pd
from datetime import datetime, timedelta

# -----------------------------
# 1. Configuration and Setup
# -----------------------------

# Load environment variables from .env file
load_dotenv()

# Initialize the Alpaca API connection using environment variables
BASE_URL = "https://paper-api.alpaca.markets"  # For paper trading; use "https://api.alpaca.markets" for live
KEY_ID = os.getenv("KEY_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

# Validate API credentials
if not KEY_ID or not SECRET_KEY:
    raise ValueError("API credentials are not set in the .env file.")

# Initialize REST API with explicit API version
api = REST(key_id=KEY_ID, secret_key=SECRET_KEY, base_url=BASE_URL, api_version='v2')

# Trading parameters
SYMBOL = 'AAPL'              # Equity symbol to trade
SMA_WINDOW = 20              # Number of periods for SMA
TIMEFRAME = TimeFrame.Hour   # Timeframe for historical data
LIMIT = 100                  # Number of bars to retrieve
SLEEP_INTERVAL = 60          # Sleep time in seconds between iterations

# -----------------------------
# 2. Helper Functions
# -----------------------------

def get_position(symbol):
    """
    Fetch the current position for the given symbol.

    :param symbol: Trading symbol (e.g., 'AAPL')
    :return: Quantity held as a float. Returns 0 if no position exists.
    """
    try:
        position = api.get_position(symbol)
        qty = float(position.qty)
        print(f"Current position for {symbol}: {qty}")
        return qty
    except Exception as e:
        # Print the exception
        print(f"Error fetching position for {symbol}: {e}")
        # If no position exists (APIError), assume zero
        return 0.0

def get_historical_data(symbol, timeframe=TimeFrame.Day, limit=100):
    """
    Fetch historical bar data for a given symbol.

    :param symbol: The trading symbol (e.g., 'AAPL')
    :param timeframe: The timeframe for each bar (e.g., TimeFrame.Day)
    :param limit: The number of bars to retrieve
    :return: A pandas DataFrame containing the historical data
    """
    try:
        # Define time range without microseconds and ensure correct format
        end_time = datetime.utcnow() - timedelta(hours=1)  # Set end_time to 1 hour ago to avoid recent SIP data
        start_time = end_time - timedelta(days=limit)      # Adjust based on timeframe

        # Format times to RFC3339 without microseconds and with 'Z' for UTC
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        # Fetch bars using the get_bars method
        bars = api.get_bars(
            symbol,
            timeframe,
            start=start_time_str,
            end=end_time_str,
            limit=limit
        ).df

        if bars.empty:
            print(f"No historical data retrieved for {symbol}.")
            return pd.DataFrame()

        # For equities, the DataFrame is single-indexed
        # Log a sample of the data for verification
        print(f"Retrieved {len(bars)} bars for {symbol}.")
        print("Historical Data Sample:")
        print(bars.head())

        return bars

    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
        return pd.DataFrame()

def calculate_sma(data, window):
    """
    Calculate Simple Moving Average (SMA) for the provided data.

    :param data: DataFrame containing historical price data
    :param window: The window size for SMA
    :return: DataFrame with an additional 'sma' column
    """
    df = data.copy()
    df['sma'] = df['close'].rolling(window=window).mean()
    return df

def round_down(value, decimals):
    """
    Round down a float to a specified number of decimal places.

    :param value: The float value to round down
    :param decimals: Number of decimal places
    :return: Rounded Decimal object
    """
    return Decimal(value).quantize(Decimal('1.' + '0' * decimals), rounding=ROUND_DOWN)

def place_order(symbol, qty, side):
    """
    Place a market order.

    :param symbol: Trading symbol (e.g., 'AAPL')
    :param qty: Quantity to buy/sell
    :param side: 'buy' or 'sell'
    """
    try:
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type='market',
            time_in_force='gtc'
        )
        print(f"Order submitted: {side.upper()} {qty} {symbol}")
    except Exception as e:
        print(f"Error submitting {side} order for {symbol}: {e}")

# -----------------------------
# 3. Trading Strategy Implementation
# -----------------------------

def main():
    while True:
        # GET CURRENT POSITION
        position = get_position(symbol=SYMBOL)

        # FETCH HISTORICAL DATA
        historical_data = get_historical_data(SYMBOL, timeframe=TIMEFRAME, limit=LIMIT)

        if historical_data.empty:
            print("Skipping trading strategy due to lack of historical data.")
            print("*" * 20)
            time.sleep(SLEEP_INTERVAL)
            continue

        # CALCULATE SMA
        sma_df = calculate_sma(historical_data, window=SMA_WINDOW)

        if len(sma_df) < SMA_WINDOW:
            print("Not enough data to calculate SMA.")
            print("*" * 20)
            time.sleep(SLEEP_INTERVAL)
            continue

        # GET THE LATEST PRICE AND SMA
        current_price = sma_df['close'].iloc[-1]
        current_sma = sma_df['sma'].iloc[-1]
        previous_sma = sma_df['sma'].iloc[-2]

        print(f"Current Price: {current_price} | Current SMA: {current_sma}")

        # GENERATE BUY SIGNAL
        buy_signal = False
        # Buy when price crosses above SMA
        if current_price > current_sma and previous_sma <= current_sma:
            buy_signal = True
            print("SMA Strategy: BUY signal detected.")

        # GENERATE SELL SIGNAL
        sell_signal = False
        # Sell when price crosses below SMA
        if current_price < current_sma and previous_sma >= current_sma:
            sell_signal = True
            print("SMA Strategy: SELL signal detected.")

        # EXECUTE BUY ORDER
        if buy_signal and position == 0:
            qty_to_buy = 1  # Define the quantity you wish to buy
            print(f"Placing BUY order for {qty_to_buy} {SYMBOL}")
            place_order(SYMBOL, qty_to_buy, 'buy')

        # EXECUTE SELL ORDER
        elif sell_signal and position > 0:
            qty_to_sell = 1
            print(f"Placing SELL order for {qty_to_sell} {SYMBOL}")
            place_order(SYMBOL, qty_to_sell, 'sell')

        else:
            print("SMA Strategy: No trading signal.")

        print("*" * 20)
        time.sleep(SLEEP_INTERVAL)  # Wait before next iteration

# -----------------------------
# 4. Entry Point
# -----------------------------

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Trading bot stopped manually.")
    except Exception as e:
        print(f"Unexpected error: {e}")
