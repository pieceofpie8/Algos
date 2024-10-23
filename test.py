import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# -----------------------------
# 1. Generate Random Price Data
# -----------------------------

def generate_random_price_data(start_price=100, days=100, seed=42):
    """
    Generate a DataFrame with random price data.

    :param start_price: Starting price of the stock
    :param days: Number of days to simulate
    :param seed: Random seed for reproducibility
    :return: DataFrame with 'Date' and 'Close' prices
    """
    np.random.seed(seed)
    # Simulate daily returns with a small random walk
    returns = np.random.normal(loc=0.001, scale=0.02, size=days)
    price = start_price * (1 + returns).cumprod()

    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    data = pd.DataFrame({'Date': dates, 'Close': price})
    data.set_index('Date', inplace=True)
    return data


# Generate the data
price_data = generate_random_price_data()


# -----------------------------
# 2. Calculate EMAs
# -----------------------------

def calculate_emas(data, short_window=12, long_window=26):
    """
    Calculate short-term and long-term EMAs.

    :param data: DataFrame with 'Close' prices
    :param short_window: Window for short-term EMA
    :param long_window: Window for long-term EMA
    :return: DataFrame with EMAs added
    """
    data[f'EMA_{short_window}'] = data['Close'].ewm(span=short_window, adjust=False).mean()
    data[f'EMA_{long_window}'] = data['Close'].ewm(span=long_window, adjust=False).mean()
    return data


# Calculate EMAs
price_data = calculate_emas(price_data)


# -----------------------------
# 3. Identify Crossover Points
# -----------------------------

def identify_crossovers(data, short_window=12, long_window=26):
    """
    Identify buy and sell signals based on EMA crossovers.

    :param data: DataFrame with EMAs calculated
    :param short_window: Window for short-term EMA
    :param long_window: Window for long-term EMA
    :return: DataFrame with 'Signal' column
    """
    data['Signal'] = 0
    # Buy signal: short EMA crosses above long EMA
    data['Signal'][short_window:] = np.where(
        data[f'EMA_{short_window}'][short_window:] > data[f'EMA_{long_window}'][short_window:], 1, 0
    )
    # Sell signal: short EMA crosses below long EMA
    data['Signal'][short_window:] = np.where(
        data[f'EMA_{short_window}'][short_window:] < data[f'EMA_{long_window}'][short_window:], -1,
        data['Signal'][short_window:]
    )
    # Calculate position
    data['Position'] = data['Signal'].diff()
    return data


# Identify crossovers
price_data = identify_crossovers(price_data)


# -----------------------------
# 4. Plot the Data
# -----------------------------

def plot_ema_crossover(data, short_window=12, long_window=26):
    """
    Plot closing prices, EMAs, and crossover signals.

    :param data: DataFrame with price and EMA data
    :param short_window: Window for short-term EMA
    :param long_window: Window for long-term EMA
    """
    plt.figure(figsize=(14, 7))
    plt.plot(data['Close'], label='Close Price', color='black')
    plt.plot(data[f'EMA_{short_window}'], label=f'EMA {short_window}', color='blue', alpha=0.7)
    plt.plot(data[f'EMA_{long_window}'], label=f'EMA {long_window}', color='red', alpha=0.7)

    # Plot buy signals
    buy_signals = data[data['Position'] == 2]
    plt.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='green', label='Buy Signal', s=100)

    # Plot sell signals
    sell_signals = data[data['Position'] == -2]
    plt.scatter(sell_signals.index, sell_signals['Close'], marker='v', color='red', label='Sell Signal', s=100)

    plt.title('EMA Crossover Strategy')
    plt.xlabel('Date')
    plt.ylabel('Price ($)')
    plt.legend()
    plt.grid(True)
    plt.show()


# Plot the EMA crossover
plot_ema_crossover(price_data)
