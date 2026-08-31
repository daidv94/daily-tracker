import os
import sys

import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
GOLD_API = "https://vang.today/api/prices"
FX_API = "https://open.er-api.com/v6/latest/USD"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# 1 troy oz = 31.1035g, 1 tael = 37.5g
TAEL_PER_OZ = 37.5 / 31.1035

# API code -> (icon, display name)
# "SJL1L10" is SJC bar (miếng), listed first with crown icon
VENDOR_MAP = {
    "SJL1L10":      ("👑", "Miếng SJC"),
    "DOHNL":        ("⚜️", "Doji HN"),
    "DOHCML":       ("⚜️", "Doji HCM"),
    "BTSJC":        ("⚜️", "BTMC"),
    "SJ9999":       ("⚜️", "Nhẫn SJC"),
    "PQHNVM":       ("⚜️", "PNJ HN"),
    "PQHN24NTT":    ("⚜️", "PNJ 24K"),
    "BT9999NTT":    ("⚜️", "BT 9999"),
    "DOJINHTV":     ("⚜️", "Doji NTrang"),
    "VIETTINMSJC":  ("⚜️", "Viettin SJC"),
    "VNGSJC":       ("⚜️", "VN Gold"),
}


def fmt_vnd(value):
    """Format VND with dot separators (Vietnamese style): 164.500.000 -> 164.500"""
    # Prices are in VND (e.g. 148700000), display in thousands: 148.700
    thousands = round(value / 1000)
    return f"{thousands:,}".replace(",", ".")


def fmt_vnd_full(value):
    """Format full VND with dot separators: 150034273 -> 150.034.273"""
    return f"{round(value):,}".replace(",", ".")


def fetch_gold_prices():
    resp = requests.get(GOLD_API, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        print("Gold API returned unsuccessful response")
        sys.exit(1)
    return data


def fetch_exchange_rate():
    resp = requests.get(FX_API, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("result") != "success":
        print("Exchange rate API returned unsuccessful response")
        sys.exit(1)
    return data["rates"]["VND"]


def build_message(gold_data, usd_vnd_rate):
    prices = gold_data.get("prices", {})

    # World gold price
    xau = prices.get("XAUUSD", {})
    xau_usd = xau.get("buy", 0)

    # Convert world gold to VND per tael
    # 1 tael = 37.5g, 1 troy oz = 31.1035g
    world_vnd_per_tael = xau_usd * usd_vnd_rate * TAEL_PER_OZ

    # SJC bar sell price for spread calculation
    sjc = prices.get("SJL1L10", {})
    sjc_sell = sjc.get("sell", 0)

    spread = sjc_sell - world_vnd_per_tael
    spread_icon = "📈" if spread > 0 else "📉"

    # Format exchange rate: 26367 -> 26.367
    fx_display = f"{usd_vnd_rate / 1000:.3f}"

    lines = [
        f"🌏 Giá TG: {xau_usd:,.2f} USD/oz",
        f"🏦 Tỷ giá bank: {fx_display} → Giá Hiện tại: {fmt_vnd_full(world_vnd_per_tael)} VND",
        f"🏅 Chênh lệch với SJC: {spread_icon} {fmt_vnd_full(abs(spread))} VND",
        "",
        "━━━━━━━━━━━━━━━━",
    ]

    for code, (icon, name) in VENDOR_MAP.items():
        info = prices.get(code)
        if not info:
            continue
        buy = fmt_vnd(info["buy"])
        sell = fmt_vnd(info["sell"])
        lines.append(f"{icon} {name}: {buy} - {sell}")

    return "\n".join(lines)


def send_telegram(message):
    resp = requests.post(
        TELEGRAM_API,
        json={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("ok"):
        print(f"Telegram API error: {result}")
        sys.exit(1)


def main():
    print("Fetching gold prices...")
    gold_data = fetch_gold_prices()

    print("Fetching exchange rate...")
    usd_vnd_rate = fetch_exchange_rate()

    message = build_message(gold_data, usd_vnd_rate)
    print(message)

    print("\nSending to Telegram...")
    send_telegram(message)
    print("Done!")


if __name__ == "__main__":
    main()

