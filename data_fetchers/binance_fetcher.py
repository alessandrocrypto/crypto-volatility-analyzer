import requests
import pandas as pd


def fetch_klines(symbol, interval="1d", limit=100):
    """
    Получение исторических свечей с Bybit.
    Возвращает DataFrame в формате Binance, чтобы не менять остальной код.
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

    if data.get("retCode") != 0:
        raise Exception(f"Bybit API error: {data}")

    rows = data["result"]["list"]

    # Bybit отдаёт от новых к старым, разворачиваем
    rows = list(reversed(rows))

    binance_rows = []

    for row in rows:
        open_time = int(row[0])
        open_price = row[1]
        high = row[2]
        low = row[3]
        close = row[4]
        volume = row[5]
        turnover = row[6]

        binance_rows.append([
            open_time,
            open_price,
            high,
            low,
            close,
            volume,
            None,
            turnover,
            None,
            None,
            None,
            None
        ])

    df = pd.DataFrame(binance_rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
    ])

    return df
