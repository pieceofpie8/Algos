import os
import random
import time
from alpaca_trade_api.rest import REST

# Initialize the Alpaca API connection
BASE_URL = "https://paper-api.alpaca.markets"
KEY_ID = "PKLA59MMTTTORKAAK8J9"
SECRET_KEY = "zpqlVjery1nsCzdk8YHKG3VkyOGBWOvzy94v3fXT"

api = REST(key_id=KEY_ID, secret_key=SECRET_KEY, base_url=BASE_URL)

# Define the currency pairs
CURRENCY_PAIRS = ['EURUSD', 'EURGBP', 'GBPUSD']

def get_exchange_rate(pair):
    try:
        barset = api.get_bars(pair, 'hour', limit = 1)
        bar = barset[pair][0]
        return bar.c
    except Exception as e:
        print(f"Error fetching {pair}: {e}")
        return None

eur_usd = get_exchange_rate('EURUSD')
print(eur_usd)