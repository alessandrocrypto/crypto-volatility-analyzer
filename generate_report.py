import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import json
import os


def _load_volatility_files():
    datasets = []

    files = [
        ("BTCUSDT", "BTCUSDT_volatility.csv"),
        ("ETHUSDT", "ETHUSDT_volatility.csv"),
        ("S&P500", "S&P500_volatility.csv"),
    ]

    for name, filename in files:
        if not os.path.exists(filename):
            print(f"⚠️ Файл отсутствует, пропускаем: {filename}")
            continue

        try:
            df = pd.read_csv(filename)

            if df.empty:
                print(f"⚠️ Файл пустой, пропускаем: {filename}")
                continue

            if "date" not in df.columns or "percent_change" not in df.columns:
                print(f"⚠️ В файле нет нужных колонок, пропускаем: {filename}")
                continue

            df = df.dropna(subset=["date", "percent_change"]).copy()
            df["date"] = pd.to_datetime(df["date"])
            df.sort_values("date", inplace=True)

            datasets.append((name, df))

        except Exception as e:
            print(f"⚠️ Ошибка чтения {filename}: {e}")

    return datasets


def get_plot_data():
    datasets = _load_volatility_files()

    if not datasets:
        return None

    plot_items = []

    for name, df in datasets:
        plot_items.append({
            "x": df["date"].dt.strftime("%Y-%m-%d").tolist(),
            "y": df["percent_change"].tolist(),
            "type": "scatter",
            "mode": "lines+markers",
            "name": name
        })

    return json.dumps(plot_items)


def generate_pdf_report():
    datasets = _load_volatility_files()

    if not datasets:
        print("⚠️ PDF не создан: нет данных")
        return

    with PdfPages("crypto_volatility_report.pdf") as pdf:
        plt.figure(figsize=(12, 6))

        for name, df in datasets:
            plt.plot(
                df["date"],
                df["percent_change"],
                label=name,
                marker="o"
            )

        plt.xlabel("Дата")
        plt.ylabel("Изменение (%)")
        plt.title("Динамика дневной волатильности")
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend()

        pdf.savefig()
        plt.close()

    print("✅ PDF-отчёт успешно создан: crypto_volatility_report.pdf")
