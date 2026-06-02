import requests
import pandas as pd


def fetch_klines(symbol, interval="1d", limit=100):
    """
    Получение исторических свечей с Bybit
    Возвращает DataFrame в том же формате, что и Binance
    """

    interval_map = {
        "1d": "D",
        "1h": "60",
        "15m": "15",
        "5m": "5"
    }

    bybit_interval = interval_map.get(interval, interval)

    url = "https://api.bybit.com/v5/market/kline"

    params = {
        "category": "spot",
        "symbol": symbol,
        "interval": bybit_interval,
        "limit": limit
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()

    if data["retCode"] != 0:
        raise Exception(f"Bybit error: {data}")

    rows = data["result"]["list"]

    rows.reverse()

    df = pd.DataFrame(rows, columns=[
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover"
    ])

    df["close_time"] = None
    df["quote_asset_volume"] = None
    df["number_of_trades"] = None
    df["taker_buy_base_asset_volume"] = None
    df["taker_buy_quote_asset_volume"] = None
    df["ignore"] = None

    return df
