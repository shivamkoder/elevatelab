# crypto_tracker.py
import os
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pycoingecko import CoinGeckoAPI

# Try to load from .env locally, but also allow passing credentials directly
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class CryptoPriceTracker:
    def __init__(self, sender_email=None, sender_password=None):
        self.client = CoinGeckoAPI()
        # If credentials are passed, use them; otherwise try env/secrets
        if sender_email and sender_password:
            self.sender_email = sender_email
            self.sender_password = sender_password
        else:
            # For local: use os.getenv; for Streamlit: use st.secrets later
            self.sender_email = os.getenv("EMAIL_SENDER")
            self.sender_password = os.getenv("EMAIL_PASSWORD")

    def get_top_coins(self, vs_currency='usd', limit=10):
        try:
            data = self.client.get_coins_markets(
                vs_currency=vs_currency,
                order='market_cap_desc',
                per_page=limit,
                page=1,
                sparkline=False
            )
            df = pd.DataFrame(data)
            df = df[['id', 'symbol', 'name', 'current_price', 'market_cap', 
                     'total_volume', 'price_change_percentage_24h']]
            df.columns = ['ID', 'Symbol', 'Name', 'Price', 'Market Cap', 
                          '24h Volume', '24h Change (%)']
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()

    def get_coin_history(self, coin_id, vs_currency='usd', days=30):
        try:
            data = self.client.get_coin_market_chart_by_id(
                id=coin_id,
                vs_currency=vs_currency,
                days=days
            )
            prices = data['prices']
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching history for {coin_id}: {e}")
            return pd.DataFrame()

    def send_alert_email(self, coin_name, current_price, target_price, recipient_email):
        if not self.sender_email or not self.sender_password:
            print("⚠️ Email credentials not set. Alert not sent.")
            return False

        subject = f"🚨 Price Alert: {coin_name} reached ${current_price:,.2f}!"
        body = f"""
        Hello,

        Your price alert for {coin_name} has been triggered!

        Current Price: ${current_price:,.2f}
        Target Price: ${target_price:,.2f}

        Time to check the market!

        Regards,
        Crypto Price Tracker
        """

        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            print(f"✅ Alert sent to {recipient_email}")
            return True
        except Exception as e:
            print(f"❌ Email failed: {e}")
            return False
