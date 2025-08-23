import yfinance as yf

class ForexPairs:
    # Lista de monedas principales
    CURRENCIES = [
        "USD", "EUR", "GBP", "JPY", "AUD",
        "CAD", "CHF", "NZD", "CNY", "SEK", "NOK"
    ]

    # Intervalos comunes en Yahoo Finance
    INTERVALS = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1d", "5d", "1wk", "1mo", "3mo"]

    def __init__(self):
        pass

    @classmethod
    def intervalos_permitidos(cls, base, cotizada, max_pruebas=5):
        """
        Devuelve los intervalos que devuelven datos válidos para un par.
        max_pruebas limita la cantidad de intervalos a probar para no saturar Yahoo.
        """
        ticker_symbol = f"{base}{cotizada}=X"
        ticker = yf.Ticker(ticker_symbol)
        intervalos_validos = []

        for interval in cls.INTERVALS[:max_pruebas]:  # probamos solo los primeros N para rapidez
            try:
                data = ticker.history(period="5d", interval=interval)
                if not data.empty:
                    intervalos_validos.append(interval)
            except Exception:
                continue

        return intervalos_validos
