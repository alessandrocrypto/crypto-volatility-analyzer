from data_fetchers.binance_fetcher import fetch_klines
from analyzers.volatility_analyzer import calculate_volatility
from writers.csv_writer import save_to_csv
from data_fetchers.sp500_fetcher import fetch_sp500_data
import pandas as pd


def run_volatility_analysis(days_to_analyze):
    symbols = ["BTCUSDT", "ETHUSDT"]
    all_results = []

    # --- Обработка криптовалют ---
    for coin in symbols:
        try:
            print(f"Обрабатываем {coin}...")
            klines = fetch_klines(coin, interval="1d", limit=1000)
            print(f"Получено {len(klines)} свечей для {coin}")

            result = calculate_volatility(klines, coin, days=days_to_analyze)
            if result:
                all_results.append(result)

        except Exception as e:
            print(f"⚠️ Ошибка при обработке {coin}: {e}")

    if all_results:
        save_to_csv(all_results)

    # --- Обработка индекса S&P500 ---
    print("\nОбрабатываем индекс S&P 500...")
    result_sp500 = None

    try:
        sp500_df = fetch_sp500_data(period=f"{days_to_analyze}d", interval="1d")

        if sp500_df is not None and not sp500_df.empty:
            sp500_df = sp500_df.copy()

            # Убираем строки с пустыми датами/high/low
            sp500_df = sp500_df.dropna(subset=["open_time", "high", "low"])

            if not sp500_df.empty:
                sp500_klines = sp500_df[["open_time", "high", "low"]].values.tolist()

                sp500_binance_format = []

                for row in sp500_klines:
                    try:
                        open_time = int(pd.to_datetime(row[0]).timestamp() * 1000)
                        high = float(row[1])
                        low = float(row[2])

                        if pd.isna(open_time) or pd.isna(high) or pd.isna(low):
                            continue

                        sp500_binance_format.append([
                            open_time, 0, high, low, 0, 0, 0, 0, 0, 0, 0, 0
                        ])

                    except Exception as e:
                        print(f"⚠️ Пропущена строка S&P500: {row}, ошибка: {e}")
                        continue

                if sp500_binance_format:
                    result_sp500 = calculate_volatility(
                        sp500_binance_format,
                        "S&P500",
                        days=days_to_analyze
                    )

                    if result_sp500:
                        save_to_csv([result_sp500], filename="sp500_volatility.csv")
                else:
                    print("⚠️ S&P500: нет валидных строк для анализа")
            else:
                print("⚠️ S&P500: после удаления NaN данных не осталось")
        else:
            print("⚠️ S&P500: данные не получены")

    except Exception as e:
        print(f"⚠️ Ошибка при обработке S&P500: {e}")

    return all_results, result_sp500
