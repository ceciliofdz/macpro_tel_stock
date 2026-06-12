import os
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
from shared import (
    read_tickers, add_ticker, update_ticker, delete_ticker,
    read_signals, delete_signal, delete_all_signals
)

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    tickers = read_tickers()
    active_count = sum(1 for t in tickers if t['active'].lower() == 'true')
    return render_template('index.html', tickers=tickers, active_count=active_count)

@app.route('/signals')
def signals():
    signals_list = read_signals(limit=200)
    return render_template('signals.html', signals=signals_list)

@app.route('/add', methods=['POST'])
def add():
    symbol = request.form['symbol']
    active = request.form['active']
    timeframe = request.form['timeframe']
    add_ticker(symbol, active, timeframe)
    return redirect(url_for('index'))

@app.route('/edit/<path:old_symbol>', methods=['GET', 'POST'])
def edit(old_symbol):
    if request.method == 'POST':
        new_symbol = request.form['symbol']
        active = request.form['active']
        timeframe = request.form['timeframe']
        update_ticker(old_symbol, new_symbol, active, timeframe)
        return redirect(url_for('index'))
    tickers = read_tickers()
    ticker = next((t for t in tickers if t['symbol'] == old_symbol), None)
    return render_template('edit.html', ticker=ticker)

@app.route('/delete/<path:symbol>')
def delete(symbol):
    delete_ticker(symbol)
    return redirect(url_for('index'))

@app.route('/delete_signal/<int:signal_id>')
def delete_signal_route(signal_id):
    delete_signal(signal_id)
    return redirect(url_for('signals'))

@app.route('/delete_all_signals')
def delete_all_signals_route():
    delete_all_signals()
    return redirect(url_for('signals'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)