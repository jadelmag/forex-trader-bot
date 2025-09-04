"""Utility functions for strategy management."""

def get_available_strategies():
    """
    Returns a tuple of (forex_strategies, candle_strategies) where:
    - forex_strategies: List of available Forex strategy names
    - candle_strategies: List of available Candle strategy names
    """
    # Forex strategies - these should match method names in ForexStrategies class
    forex_strategies = [
        'ma_crossover',
        'bollinger_bands',
        'rsi_strategy',
        'macd_strategy',
        'stochastic_oscillator',
        'ichimoku_cloud',
        'adx_strategy',
        'parabolic_sar_strategy',
        'heikin_ashi_strategy',
        'keltner_channels_strategy'
    ]
    
    # Candle patterns - these should match method names in CandleStrategies class
    candle_strategies = [
        'engulfing',
        'harami',
        'morning_star',
        'evening_star',
        'hammer',
        'shooting_star',
        'three_white_soldiers',
        'three_black_crows',
        'doji',
        'piercing_line',
        'dark_cloud_cover'
    ]
    
    return forex_strategies, candle_strategies
