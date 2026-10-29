# testingcoin (BTC + ETH)

Educational Flask app: live BTC/ETH prices (CoinGecko), TradingView chart, and
simulated Buy Up / Buy Down contracts using a **virtual** balance. No real funds
are collected, held, or moved.

## Run
```
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
export SECRET_KEY="something-long-and-random"   # Windows: set SECRET_KEY=...
flask run
```
Open http://127.0.0.1:5000 — the SQLite DB is created automatically in `instance/`.

## Structure
app.py · models.py · forms.py · services.py (CoinGecko + settlement)
routes/{auth,market,contract}.py · templates/ · static/{css,js}

## Notes
- Contracts settle at the latest cached price (refreshed about every 60s), so it is an approximation, fine for a demo.
- The saved wallet address on Profile is a reference note only and is never used.
