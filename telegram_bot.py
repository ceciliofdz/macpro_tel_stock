import requests
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TOKEN:
    print('Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN is not set in .env')
if not CHAT_ID:
    print('Warning: TELEGRAM_CHAT_ID is not set in .env')

def send_telegram_alert(symbol: str, signal_type: str, price: float, momento: str, tendencia: str):
    """signal_type: 'BUY' o 'SELL'"""
    if signal_type == 'BUY':
        titulo = "🟢 MACD PRO: Compra Detectada"
    else:
        titulo = "🔴 MACD PRO: Venta Detectada"
    
    mensaje = f"""{titulo}
📌 Símbolo: {symbol}
💰 Precio: {price:.4f}
📈 Momento: {momento}
📊 Tendencia: {tendencia}
    """
    if not TOKEN or not CHAT_ID:
        print('Error: TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN or TELEGRAM_CHAT_ID no está configurado.')
        return False
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': mensaje,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data.get('ok', False):
            error_description = data.get('description', 'Unknown error')
            print(f"Telegram API returned error: {error_description}")
            print(f"Payload: {payload}")
            return False
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error enviando a Telegram: {e}")
        print(f"URL: {url}")
        print(f"Payload: {payload}")
        return False
    except ValueError as e:
        print(f"Error parsing Telegram response: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'no response'}")
        return False