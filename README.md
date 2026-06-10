# MACD PRO Telegram Bot

Proyecto: monitor de señales MACD con envío de alertas a Telegram y panel web mínimo.

Descripción
-
`MACD PRO Telegram Bot` monitorea múltiples símbolos (tickers) aplicando una variante del indicador MACD con filtro de tendencia (por ejemplo EMA 200). Cuando se detectan cruces relevantes, el sistema envía notificaciones a un chat de Telegram y permite gestionar la lista de símbolos desde una interfaz web simple.

Características principales
-
- Monitorización de múltiples tickers desde `tickers.csv`.
- Soporte para criptomonedas con `ccxt` y para acciones NASDAQ usando `yfinance`.
- Lógica MACD configurable (`FAST_LEN`, `SLOW_LEN`, `SIGNAL_LEN`, tipos de medias).
- Filtro de tendencia (EMA 200) opcional para reducir ruido.
- Envío de alertas a Telegram (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
- Interfaz web ligera para ver/editar tickers y estado (carpeta `templates/`).

Requisitos
-
- Python 3.11+ (probado en 3.11)
- `pip` y un entorno virtual recomendado

Instalación rápida
-
1. Clona el repositorio.
2. Crea y activa un entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
.venv\Scripts\activate     # Windows (PowerShell/CMD)
```

3. Instala dependencias:

```bash
pip install -r requirements.txt
```

4. Configura variables de entorno copiando `.env.example` a `.env` y editando valores.

Uso
-
- Ejecutar el monitor:

```bash
python main.py
```

- La interfaz web (si está habilitada en el código) corre por defecto en `http://localhost:5000`.

Variables de entorno (ejemplo)
-
Agrega un fichero `.env` con al menos las siguientes claves (valores de ejemplo):

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
FAST_LEN=12
SLOW_LEN=26
SIGNAL_LEN=9
SOURCE_TYPE=close
OSC_MA_TYPE=EMA
SIGNAL_MA_TYPE=EMA
USE_TREND_FILTER=true
TREND_FILTER_MODE=Ambas
TREND_EMA_LEN=200
TIMEFRAME=1h
CHECK_INTERVAL_MINUTES=5
```

Estructura de `tickers.csv`
-
El archivo `tickers.csv` contiene los símbolos a monitorizar. Formato recomendado:

```csv
symbol,active,timeframe
BTC/USDT,True,1h
AAPL,True,1d
```

También se aceptan pares cripto sin slash, por ejemplo `BTCUSDT` o `AXTIUSDT`, y el sistema los normaliza internamente para usar `ccxt`.

Archivos relevantes
-
- `main.py` — punto de entrada del monitor.
- `data_fetcher.py` — obtiene datos de mercado.
- `macd_logic.py` — implementa la lógica MACD/alertas.
- `telegram_bot.py` — envía mensajes a Telegram.
- `templates/` — vistas mínimas para la interfaz web.

Pruebas y desarrollo
-
- Para pruebas rápidas edita `tickers.csv` y ejecuta `python main.py`.
- Revisa `test.py` para ejemplos o pruebas locales (si existen).

Depuración y notas
-
- Asegúrate de que el reloj del sistema y la zona horaria son correctos si trabajas con timeframes.
- Si no recibes mensajes de Telegram, verifica `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` con `@BotFather` y `@userinfobot`.

¿Quieres que traduzca este README al inglés o que incluya ejemplos concretos de `.env.example` y capturas de la interfaz web?
