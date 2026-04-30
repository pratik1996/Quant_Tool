import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

import pytz
import requests
import yfinance as yf

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
})

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


def get_trading_date():
    """Return today's date in IST (script runs after 6 PM IST, market already closed)."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).date()


def batch_pct_change(tickers, date):
    """Download all tickers in one API call. Returns dict of ticker -> pct_change."""
    start = date - timedelta(days=7)
    end = date + timedelta(days=1)

    df = None
    for attempt in range(4):
        df = yf.download(
            tickers, start=start, end=end,
            progress=False, auto_adjust=True, session=_SESSION,
        )
        if not df.empty:
            break
        wait = 2 ** attempt * 5  # 5s, 10s, 20s, 40s
        print(f"Rate limited or empty response, retrying in {wait}s...")
        time.sleep(wait)

    if df is None or df.empty:
        return {}

    # Multi-ticker download gives MultiIndex columns; single ticker gives flat columns
    if len(tickers) == 1:
        close_df = df[["Close"]].rename(columns={"Close": tickers[0]})
    else:
        close_df = df["Close"]

    results = {}
    for ticker in tickers:
        if ticker not in close_df.columns:
            continue
        series = close_df[ticker].dropna()
        if len(series) < 2:
            continue
        if series.index[-1].date() != date:
            continue
        prev_close = float(series.iloc[-2])
        last_close = float(series.iloc[-1])
        if prev_close == 0:
            continue
        results[ticker] = round((last_close - prev_close) / prev_close * 100, 2)

    return results


def color_cell(value):
    if value is None:
        return "<td style='padding:6px 12px;color:#888;'>N/A</td>"
    color = "#16a34a" if value >= 0 else "#dc2626"
    arrow = "▲" if value >= 0 else "▼"
    return f"<td style='padding:6px 12px;color:{color};font-weight:600;'>{arrow} {abs(value):.2f}%</td>"


def build_html(report_date, sector_data, gainers, losers):
    date_str = report_date.strftime("%A, %d %B %Y")

    sector_rows = "".join(
        f"<tr><td style='padding:6px 12px;'>{name}</td>{color_cell(pct)}</tr>"
        for name, pct in sector_data
    )

    def stock_rows(stocks):
        return "".join(
            f"<tr><td style='padding:6px 12px;'>{name}</td>{color_cell(pct)}</tr>"
            for name, pct in stocks
        )

    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f9fafb;padding:24px;color:#111;">
  <div style="max-width:560px;margin:auto;background:#fff;border-radius:10px;
              box-shadow:0 2px 8px rgba(0,0,0,0.08);padding:28px;">

    <h2 style="margin-top:0;border-bottom:2px solid #e5e7eb;padding-bottom:10px;">
      India Market Report
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
</html>"""


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
    report_date = get_trading_date()
    print(f"Fetching data for {report_date}")

    # Single batch call for all sectoral indices
    index_tickers = list(SECTORAL_INDICES.values())
    index_changes = batch_pct_change(index_tickers, report_date)

    # Check if market was open using Nifty 50 as anchor
    nifty_ticker = SECTORAL_INDICES["Nifty 50"]
    if nifty_ticker not in index_changes:
        print("No market data available for this date (holiday or data unavailable). Skipping.")
        return

    sector_data = [(name, index_changes.get(ticker)) for name, ticker in SECTORAL_INDICES.items()]

    # Single batch call for all Nifty 50 stocks
    stock_changes_map = batch_pct_change(NIFTY50_STOCKS, report_date)
    if not stock_changes_map:
        print("No stock data available. Skipping.")
        return

    stock_changes = sorted(
        [(t.replace(".NS", ""), p) for t, p in stock_changes_map.items()],
        key=lambda x: x[1],
        reverse=True,
    )
    gainers = stock_changes[:3]
    losers = stock_changes[-3:][::-1]

    html = build_html(report_date, sector_data, gainers, losers)
    subject = f"India Market Report — {report_date.strftime('%d %b %Y')}"
    send_email(subject, html)
    print(f"Email sent successfully for {report_date}")


if __name__ == "__main__":
    main()
