import os
import time
from alpaca_trade_api.rest import REST, TimeFrame
from dotenv import load_dotenv
from decimal import Decimal, ROUND_DOWN
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

load_dotenv()
BASE_URL = "https://paper-api.alpaca.markets"  # For paper trading; use "https://api.alpaca.markets" for live
KEY_ID = os.getenv("KEY_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

# Validate API credentials
if not KEY_ID or not SECRET_KEY:
    raise ValueError("API credentials are not set in the .env file.")

# Initialize REST API with explicit API version
api = REST(key_id=KEY_ID, secret_key=SECRET_KEY, base_url=BASE_URL, api_version='v2')

# Trading parameters
SYMBOL = 'AAPL'               # Equity symbol to trade
SHORT_EMA_WINDOW = 12         # Short-term EMA window
LONG_EMA_WINDOW = 26          # Long-term EMA window
TIMEFRAME = TimeFrame.Hour     # Timeframe for historical data
LIMIT = 100                    # Number of bars to retrieve
SLEEP_INTERVAL = 5            # Sleep time in seconds between iterations
def get_position(symbol):
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
    try:
        # Define time range without microseconds and ensure correct format
        end_time = datetime.utcnow() - timedelta(hours=2)  # Set end_time to 2 hours ago to avoid recent SIP data
        start_time = end_time - timedelta(days=limit)
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

def calculate_ema(data, window):
    '''
    For an example of how ema works,
    import pandas as pd

    df = pd.DataFrame({'price': [10, 12, 11, 14, 13, 15]})

    # Calculate the 10-day EWMA
    df['ewma_10'] = df['price'].ewm(span=10).mean()

    print(df)
    alpha = 2/(span + 1) = 2/11 = 0.1818
    First is 10
    Second is 0.1818 * 12 + (1 - 0.1818) * 10 = 10.3634
    Third is 0.1818 * 14 + (1 - 0.1818) * 10.3634 = 10.4843
    And like that. The newest ones have a bigger weight because they are more recent.
    '''
    df = data.copy()
    df[f'ema_{window}'] = df['close'].ewm(span=window, adjust=False).mean()
    return df
def place_order(symbol, qty, side):
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
def calculate_ema_crossover_strategy(data, short_window=12, long_window=26):
    """
    Calculate EMAs and generate buy/sell signals based on EMA crossovers.

    :param data: DataFrame containing historical price data
    :param short_window: Short-term EMA window
    :param long_window: Long-term EMA window
    :return: DataFrame with EMA columns and signals
    """
    df = data.copy()
    df = calculate_ema(df, short_window)
    df = calculate_ema(df, long_window)

    # Generate signals
    df['signal'] = 0
    df['signal'] = np.where(df[f'ema_{short_window}'] > df[f'ema_{long_window}'], 1, 0)
    df['position'] = df['signal'].diff()

    return df

def main():
    while True:
        position = get_position(symbol=SYMBOL)
        historical_data = get_historical_data(SYMBOL, timeframe=TIMEFRAME, limit=LIMIT)
        if historical_data.empty:
            print("Skipping trading strategy due to lack of historical data.")
            print("*" * 20)
            time.sleep(SLEEP_INTERVAL)
            continue
        ema_df = calculate_ema_crossover_strategy(historical_data, short_window=SHORT_EMA_WINDOW, long_window=LONG_EMA_WINDOW)
        if len(ema_df) < LONG_EMA_WINDOW:
            print("Not enough data to calculate EMAs.")
            print("*" * 20)
            time.sleep(SLEEP_INTERVAL)
            continue

        # GET THE LATEST EMA values and generate signals
        current_ema_short = ema_df[f'ema_{SHORT_EMA_WINDOW}'].iloc[-1]
        current_ema_long = ema_df[f'ema_{LONG_EMA_WINDOW}'].iloc[-1]
        previous_ema_short = ema_df[f'ema_{SHORT_EMA_WINDOW}'].iloc[-2]
        previous_ema_long = ema_df[f'ema_{LONG_EMA_WINDOW}'].iloc[-2]

        print(f"Current EMA Short ({SHORT_EMA_WINDOW}): {current_ema_short} | Current EMA Long ({LONG_EMA_WINDOW}): {current_ema_long}")

        buy_signal = False
        # Buy when short EMA crosses above long EMA
        if (current_ema_short > current_ema_long) and (previous_ema_short <= previous_ema_long):
            buy_signal = True
            print("EMA Crossover Strategy: BUY signal detected.")

        sell_signal = False
        # Sell when short EMA crosses below long EMA
        if (current_ema_short < current_ema_long) and (previous_ema_short >= previous_ema_long):
            sell_signal = True
            print("EMA Crossover Strategy: SELL signal detected.")

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
            print("EMA Crossover Strategy: No trading signal.")

        print("*" * 20)
        time.sleep(SLEEP_INTERVAL)  # Wait before next iteration

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Trading bot stopped manually.")
    except Exception as e:
        print(f"Unexpected error: {e}")
