"""Utility functions for candlestick pattern management."""

def get_available_patterns():
    """
    Returns a list of available candlestick pattern names.
    These should match method names in the CandlestickPatterns class.
    """
    return [
        'doji',
        'hammer',
        'hanging_man',
        'shooting_star',
        'spinning_top',
        'inverted_hammer',
        'engulfing',
        'harami',
        'morning_star',
        'evening_star',
        'three_white_soldiers',
        'three_black_crows',
        'piercing_line',
        'dark_cloud_cover'
    ]
