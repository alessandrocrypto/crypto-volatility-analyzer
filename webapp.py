import matplotlib
matplotlib.use("Agg")

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from analysis_core import run_volatility_analysis
from generate_report import generate_pdf_report, get_plot_data

import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 🔁 глобальные объекты
bot = None
application = ApplicationBuilder().token(BOT_TOKEN).build()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals.update(zip=zip)

# Telegram Bot Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для анализа волатильности. Отправь одну из команд:\n"
        "/analyze_5\n/analyze_10\n/analyze_30\n/analyze_90"
    )

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
    await update.message.reply_text(f"🔍 Анализирую волатильность за {days} дней...")
    crypto_results, sp500_result = run_volatility_analysis(days)
    response = f"📊 <b>Волатильность за {days} дней:</b>\n\n"
    for coin in crypto_results:
        response += f"<b>{coin['symbol']}</b> — {coin['average_volatility_points']:.1f} пунктов, {coin['average_volatility_percent']:.2f}%\n"
    response += f"<b>{sp500_result['symbol']}</b> — {sp500_result['average_volatility_points']:.1f} пунктов, {sp500_result['average_volatility_percent']:.2f}%\n"
    response += "\n📌 Выберите период:\n/analyze_5  /analyze_10  /analyze_30  /analyze_90"
    await update.message.reply_text(response, parse_mode="HTML")

def make_analyze_handler(d):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await analyze_command(update, context, d)
    return handler

# Автоматическая проверка волатильности
scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Rome"))

async def daily_volatility_alert():
    print("🚀 Запуск daily_volatility_alert()")
    crypto_results, _ = run_volatility_analysis(90)

    rome_now = datetime.now(pytz.timezone("Europe/Rome"))
    yesterday = (rome_now - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"🔎 Проверяем данные за дату: {yesterday}")

    message_lines = []

    for coin in crypto_results:
        symbol = coin["symbol"]
        data = coin.get("daily_data", [])
        print(f"📘 Обрабатываем {symbol}, записей: {len(data)}")

        if not data:
            print(f"⚠️ Нет данных по {symbol}")
            continue

        for row in data:
            date = row["date"]
            percent = row["percent_change"]
            print(f"  📅 {date} — {percent:.2f}%")

            if date != yesterday:
                continue

            # Проверка на минимумы и максимумы
            if symbol == "BTCUSDT":
                if percent <= 2:
                    message_lines.append("📉 BTCUSDT — минимальная волатильность ≤2%")
                elif percent >= 8:
                    message_lines.append("📈 BTCUSDT — максимальная волатильность ≥8%")
            elif symbol == "ETHUSDT":
                if percent <= 3:
                    message_lines.append("📉 ETHUSDT — минимальная волатильность ≤3%")
                elif percent >= 15:
                    message_lines.append("📈 ETHUSDT — максимальная волатильность ≥15%")
            break  # Только одна проверка на дату

    if message_lines and TELEGRAM_CHAT_ID:
        header = "🚨 Обнаружена минимальная или максимальная волатильность!"
        advice = "💡 Рассмотрите покупку стредла при минимальной волатильности и продажу стренгла при максимальной."
        final_msg = f"<b>{header}</b>\n\n" + "\n".join(message_lines) + "\n\n" + advice
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=final_msg, parse_mode="HTML")
        print("✅ Отправлено сообщение в Telegram")
    else:
        print("ℹ️ Нет волатильности, попадающей под заданные пороги.")

# Веб-интерфейс
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.post("/analyze", response_class=HTMLResponse)
def analyze(request: Request, days: int = Form(...)):
    crypto_results, sp500_result = run_volatility_analysis(days)
    generate_pdf_report()
    plot_data = get_plot_data()

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "days": days,
            "crypto_results": crypto_results,
            "sp500_result": sp500_result,
            "report_url": "/download/report",
            "plot_data": plot_data,
            "crypto_tables": [coin["daily_data"] for coin in crypto_results],
            "sp500_table": sp500_result["daily_data"]
        }
    )

@app.get("/download/report")
def download_report():
    filepath = "crypto_volatility_report.pdf"
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type='application/pdf', filename="volatility_report.pdf")
    return {"error": "Файл не найден"}

# Запуск бота и установка webhook
@app.on_event("startup")
async def start_bot():
    print("🌀 Вызван start_bot()")

    if not BOT_TOKEN:
        print("⚠️ BOT_TOKEN не задан в переменных окружения.")
        return

    application.add_handler(CommandHandler("start", start_command))

    for d in [5, 10, 30, 90]:
        application.add_handler(
            CommandHandler(f"analyze_{d}", make_analyze_handler(d))
        )

    global bot
    bot = application.bot

    try:
        await daily_volatility_alert()
    except Exception as e:
        print(f"⚠️ Ошибка daily_volatility_alert: {e}")

    await application.initialize()
    await application.start()

    await application.bot.set_webhook(
        "https://crypto-volatility-analyzer.onrender.com/webhook"
    )

    print("✅ Webhook установлен")

    scheduler.add_job(
        daily_volatility_alert,
        CronTrigger(hour=6, minute=0)
    )

    scheduler.start()

# Обработка webhook-запросов от Telegram
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}

