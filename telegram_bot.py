import requests
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TOKEN:
    print('Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN is not set in .env')
if not CHAT_ID:
    print('Warning: TELEGRAM_CHAT_ID is not set in .env')

def send_telegram_alert(symbol: str, signal_type: str, price: float, momento: str, tendencia: str):
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
        print('Error: Faltan credenciales de Telegram.')
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
            print(f"Telegram API error: {data.get('description', 'Unknown')}")
            return False
        return True
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")
        return False