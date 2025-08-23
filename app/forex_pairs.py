# app/forex_pairs.py

import yfinance as yf

class ForexPairs:
    CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]
    
    # Intervalos probados y válidos para divisas
    INTERVALS = ["1d", "5d", "1wk", "1mo"]

    # Tickers válidos en Yahoo Finance
    VALID_TICKERS = [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
        "USDCAD=X", "USDCHF=X", "NZDUSD=X"
    ]

    @classmethod
    def ticker_valido(cls, base, cotizada):
        # Intentar ticker directo
        ticker = f"{base}{cotizada}=X"
        if ticker in cls.VALID_TICKERS:
            return ticker, False
        # Intentar ticker invertido
        ticker_inv = f"{cotizada}{base}=X"
        if ticker_inv in cls.VALID_TICKERS:
            return ticker_inv, True
        raise ValueError(f"No hay datos para {base}/{cotizada} en Yahoo Finance.")

    @classmethod
    def intervalos_permitidos(cls, base, cotizada):
        try:
            ticker_symbol, _ = cls.ticker_valido(base, cotizada)
        except ValueError:
            return []
        ticker = yf.Ticker(ticker_symbol)
        intervalos_validos = []
        for interval in cls.INTERVALS:
            try:
                data = ticker.history(period="5d", interval=interval)
                if not data.empty:
                    intervalos_validos.append(interval)
            except Exception:
                continue
        return intervalos_validos
