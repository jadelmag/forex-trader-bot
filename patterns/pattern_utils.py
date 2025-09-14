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


def get_default_pattern_detection_config() -> dict:
    """Centralized defaults for pattern detection aligned with CandlestickPatterns.

    These values are the single source of truth to avoid duplication across UI modals.
    """
    return {
        # Pattern parameters (aligned with CandlestickPatterns defaults)
        "doji_threshold": 0.15,
        "tweezer_tolerance": 0.01,
        "min_confidence": 0.3,
        "partial_factor": 0.5,
        "hammer_body_ratio": 1.2,
        "shooting_star_ratio": 1.5,
        "spinning_top_ratio": 0.4,
        "marubozu_ratio": 0.7,

        # Indicator parameters
        "atr_period": 14,
        "trend_period": 20,
        "volatility_period": 20,

        # Additional pattern params (kept for UI completeness)
        "engulfing_min_body_ratio": 1.05,
        "harami_max_body_ratio": 0.9,
        "star_gap_threshold": 0.005,
        "three_methods_trend_strength": 0.5,
    }
