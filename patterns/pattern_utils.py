"""Utility functions for candlestick pattern management."""

from .candlestickpatterns import CandlestickPatterns


def get_available_patterns():
    """
    Returns a sorted list of available candlestick pattern method names
    implemented in the CandlestickPatterns class.

    This is generated dynamically to avoid drift between the registry and
    the actual implementation. Helper methods are excluded.
    """
    exclude = {"__init__", "detect_all_patterns", "combined_signal_optimized"}
    patterns = []
    for name in dir(CandlestickPatterns):
        if name.startswith("_"):
            continue
        if name in exclude:
            continue
        attr = getattr(CandlestickPatterns, name)
        if callable(attr):
            patterns.append(name)
    return sorted(patterns)
