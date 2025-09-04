"""Utility functions for strategy management.

Centralized registry to map UI-friendly aliases to actual method names
implemented in `ForexStrategies` and `CandleStrategies`. This avoids
"strategy not found" errors when UI names differ from implementation names.
"""

from __future__ import annotations

from typing import Dict, Tuple


# Aliases for Forex strategies (left: alias shown in UI, right: real method name)
# Only include methods that actually exist in ForexStrategies.
_FOREX_ALIAS_TO_METHOD: Dict[str, str] = {
    # Short aliases -> concrete method names
    "ma_crossover": "moving_average_crossover",
    "bollinger_bands": "bollinger_bands_strategy",
    "stochastic_oscillator": "stochastic_strategy",
    "ichimoku_cloud": "ichimoku_cloud_strategy",
    "support_resistance": "support_resistance_strategy",
    "price_action": "price_action_patterns",
    "supply_demand": "supply_demand_zones",
    "trendline": "trendline_strategy",
    "scalping_1m": "scalping_1m_strategy",
    "news_trading": "news_trading_strategy",
    "range_trading": "range_trading_strategy",
    "carry_trade": "carry_trade_strategy",
    "hedging": "hedging_overlay",
    "grid_trading": "grid_trading_strategy",
    "mean_reversion": "mean_reversion_strategy",
    "martingale": "martingale_overlay",

    # Keep exact names also available as aliases to themselves
    "adx_strategy": "adx_strategy",
    "trend_following": "trend_following",
    "breakout": "breakout",
    "rsi_strategy": "rsi_strategy",
    "macd_strategy": "macd_strategy",
    "moving_average_crossover": "moving_average_crossover",
    "bollinger_bands_strategy": "bollinger_bands_strategy",
    "stochastic_strategy": "stochastic_strategy",
    "ichimoku_cloud_strategy": "ichimoku_cloud_strategy",
    "support_resistance_strategy": "support_resistance_strategy",
    "price_action_patterns": "price_action_patterns",
    "supply_demand_zones": "supply_demand_zones",
    "trendline_strategy": "trendline_strategy",
    "scalping_1m_strategy": "scalping_1m_strategy",
    "news_trading_strategy": "news_trading_strategy",
    "range_trading_strategy": "range_trading_strategy",
    "carry_trade_strategy": "carry_trade_strategy",
    "hedging_overlay": "hedging_overlay",
    "grid_trading_strategy": "grid_trading_strategy",
    "mean_reversion_strategy": "mean_reversion_strategy",
    "martingale_overlay": "martingale_overlay",
}


# Aliases for Candle strategies. If aliases are identical to implementation
# names, we can keep them as identity mapping. Adjust here if names diverge.
_CANDLE_ALIAS_TO_METHOD: Dict[str, str] = {
    "engulfing": "engulfing",
    "harami": "harami",
    "morning_star": "morning_star",
    "evening_star": "evening_star",
    "hammer": "hammer",
    "shooting_star": "shooting_star",
    "three_white_soldiers": "three_white_soldiers",
    "three_black_crows": "three_black_crows",
    "doji": "doji",
    "piercing_line": "piercing_line",
    "dark_cloud_cover": "dark_cloud_cover",
}


def get_strategy_registry() -> Dict[str, Dict[str, str]]:
    """Returns the full strategy registry grouped by type.

    Structure: {
      "forex": { alias: method_name, ... },
      "candle": { alias: method_name, ... }
    }
    """
    return {
        "forex": dict(_FOREX_ALIAS_TO_METHOD),
        "candle": dict(_CANDLE_ALIAS_TO_METHOD),
    }


def get_available_strategies() -> Tuple[list[str], list[str]]:
    """Return available alias names for forex and candle strategies.

    The returned names are UI-friendly aliases. Use `resolve_strategy_name`
    to map an alias to the real method name at runtime.
    """
    forex_strategies = sorted(list(_FOREX_ALIAS_TO_METHOD.keys()))
    candle_strategies = sorted(list(_CANDLE_ALIAS_TO_METHOD.keys()))
    return forex_strategies, candle_strategies


def resolve_strategy_name(name: str, tipo: str) -> str:
    """Resolve a user-facing alias to the actual callable method name.

    - tipo: "forex" | "candle"
    - If no mapping exists, returns the original name (graceful fallback).
    """
    if tipo == "forex":
        return _FOREX_ALIAS_TO_METHOD.get(name, name)
    if tipo == "candle":
        return _CANDLE_ALIAS_TO_METHOD.get(name, name)
    return name
