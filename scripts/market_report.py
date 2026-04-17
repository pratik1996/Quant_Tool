import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

import pytz
import yfinance as yf

NIFTY50_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "BHARTIARTL.NS", "ICICIBANK.NS",
    "INFY.NS", "SBIN.NS", "HINDUNILVR.NS", "ITC.NS", "LT.NS",
    "KOTAKBANK.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "TITAN.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "WIPRO.NS", "NTPC.NS",
    "POWERGRID.NS", "HCLTECH.NS", "TATAMOTORS.NS", "ADANIPORTS.NS", "ONGC.NS",
    "NESTLEIND.NS", "COALINDIA.NS", "BAJAJFINSV.NS", "HINDALCO.NS", "JSWSTEEL.NS",
    "INDUSINDBK.NS", "TATASTEEL.NS", "TECHM.NS", "CIPLA.NS", "BRITANNIA.NS",
    "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS",
    "APOLLOHOSP.NS", "BPCL.NS", "GRASIM.NS", "TATACONSUM.NS", "SBILIFE.NS",
    "HDFCLIFE.NS", "ADANIENT.NS", "M&M.NS", "BEL.NS", "TRENT.NS",
]

SECTORAL_INDICES = {
    "Nifty 50":     "^NSEI",
    "Nifty Bank":   "^NSEBANK",
    "Nifty IT":     "^CNXIT",
    "Nifty Pharma": "^CNXPHARMA",
    "Nifty Auto":   "^CNXAUTO",
    "Nifty FMCG":   "^CNXFMCG",
    "Nifty Metal":  "^CNXMETAL",
    "Nifty Realty": "^CNXREALTY",
    "Nifty Energy": "^CNXENERGY",
    "Nifty Media":  "^CNXMEDIA",
}


def get_prev_trading_date():
    """Return the most recent weekday date in IST."""
    ist = pytz.timezone("Asia/Kolkata")
    today = datetime.now(ist).date()
    delta = 1
    if today.weekday() == 0:  # Monday → go back to Friday
        delta = 3
    elif today.weekday() == 6:  # Sunday → go back to Friday
        delta = 2
    return today - timedelta(days=delta)


def fetch_pct_change(ticker, date):
    """Return % change for ticker on the given date. Returns None if no data."""
    start = date - timedelta(days=5)
    end = date + timedelta(days=1)
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if df.empty or len(df) < 2:
        return None
    df = df.sort_index()
    # Confirm the last available date matches the requested date
    last_date = df.index[-1].date()
    if last_date != date:
        return None
    prev_close = float(df["Close"].iloc[-2])
    last_close = float(df["Close"].iloc[-1])
    if prev_close == 0:
        return None
    return round((last_close - prev_close) / prev_close * 100, 2)


def fetch_stock_changes(date):
    """Return list of (ticker, pct_change) for all Nifty 50 stocks."""
    results = []
    for ticker in NIFTY50_STOCKS:
        pct = fetch_pct_change(ticker, date)
        if pct is not None:
            name = ticker.replace(".NS", "")
            results.append((name, pct))
    return results


def color_cell(value):
    if value is None:
        return "<td style='color:#888;'>N/A</td>"
    color = "#16a34a" if value >= 0 else "#dc2626"
    arrow = "▲" if value >= 0 else "▼"
    return f"<td style='color:{color};font-weight:600;'>{arrow} {abs(value):.2f}%</td>"


def build_html(report_date, sector_data, gainers, losers):
    date_str = report_date.strftime("%A, %d %B %Y")

    sector_rows = ""
    for name, pct in sector_data:
        sector_rows += f"<tr><td style='padding:6px 12px;'>{name}</td>{color_cell(pct)}</tr>"

    def stock_rows(stocks):
        rows = ""
        for name, pct in stocks:
            rows += f"<tr><td style='padding:6px 12px;'>{name}</td>{color_cell(pct)}</tr>"
        return rows

    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f9fafb;padding:24px;color:#111;">
  <div style="max-width:560px;margin:auto;background:#fff;border-radius:10px;
              box-shadow:0 2px 8px rgba(0,0,0,0.08);padding:28px;">

    <h2 style="margin-top:0;border-bottom:2px solid #e5e7eb;padding-bottom:10px;">
      📊 India Market Report
    </h2>
    <p style="color:#6b7280;margin-top:0;">{date_str}</p>

    <h3 style="color:#374151;">Sectoral Performance</h3>
    <table style="border-collapse:collapse;width:100%;font-size:14px;">
      <thead>
        <tr style="background:#f3f4f6;">
          <th style="padding:6px 12px;text-align:left;">Index</th>
          <th style="padding:6px 12px;text-align:left;">Change</th>
        </tr>
      </thead>
      <tbody>{sector_rows}</tbody>
    </table>

    <h3 style="color:#16a34a;margin-top:24px;">Top 3 Gainers (Nifty 50)</h3>
    <table style="border-collapse:collapse;width:100%;font-size:14px;">
      <thead>
        <tr style="background:#f0fdf4;">
          <th style="padding:6px 12px;text-align:left;">Stock</th>
          <th style="padding:6px 12px;text-align:left;">Change</th>
        </tr>
      </thead>
      <tbody>{stock_rows(gainers)}</tbody>
    </table>

    <h3 style="color:#dc2626;margin-top:24px;">Top 3 Losers (Nifty 50)</h3>
    <table style="border-collapse:collapse;width:100%;font-size:14px;">
      <thead>
        <tr style="background:#fef2f2;">
          <th style="padding:6px 12px;text-align:left;">Stock</th>
          <th style="padding:6px 12px;text-align:left;">Change</th>
        </tr>
      </thead>
      <tbody>{stock_rows(losers)}</tbody>
    </table>

    <p style="margin-top:24px;font-size:11px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:12px;">
      Data sourced from Yahoo Finance. Prices reflect NSE closing values.
    </p>
  </div>
</body>
</html>
"""


def send_email(subject, html_body):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipient, msg.as_string())


def main():
    report_date = get_prev_trading_date()
    print(f"Fetching data for {report_date}")

    # Fetch sectoral indices
    sector_data = []
    for name, ticker in SECTORAL_INDICES.items():
        pct = fetch_pct_change(ticker, report_date)
        sector_data.append((name, pct))

    # Check if market was open — Nifty 50 index is the anchor
    nifty_pct = next((p for n, p in sector_data if n == "Nifty 50"), None)
    if nifty_pct is None:
        print("No market data available for this date (holiday or data unavailable). Skipping.")
        return

    # Fetch Nifty 50 stock movements
    stock_changes = fetch_stock_changes(report_date)
    if not stock_changes:
        print("No stock data available. Skipping.")
        return

    stock_changes.sort(key=lambda x: x[1], reverse=True)
    gainers = stock_changes[:3]
    losers = stock_changes[-3:][::-1]

    html = build_html(report_date, sector_data, gainers, losers)
    subject = f"India Market Report — {report_date.strftime('%d %b %Y')}"
    send_email(subject, html)
    print(f"Email sent successfully for {report_date}")


if __name__ == "__main__":
    main()
