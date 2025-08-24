# app/forex_pairs.py

import yfinance as yf

class ForexPairs:
    CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]
    INTERVALS = ["1d", "5d", "1wk", "1mo"]
    VALID_TICKERS = [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
        "USDCAD=X", "USDCHF=X", "NZDUSD=X"
    ]
    
    _interval_cache = {}

    @classmethod
    def ticker_valido(cls, base, cotizada):
        ticker = f"{base}{cotizada}=X"
        if ticker in cls.VALID_TICKERS:
            return ticker, False
        ticker_inv = f"{cotizada}{base}=X"
        if ticker_inv in cls.VALID_TICKERS:
            return ticker_inv, True
        raise ValueError(f"No hay datos para {base}/{cotizada} en Yahoo Finance.")

    @classmethod
    def intervalos_permitidos(cls, base, cotizada):
        key = f"{base}_{cotizada}"
        if key in cls._interval_cache:
            return cls._interval_cache[key]

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
            except Exception as e:
                if "429" in str(e):
                    raise RuntimeError("Acceso limitado (429) a Yahoo Finance") from e
                continue

        cls._interval_cache[key] = intervalos_validos
        return intervalos_validos
