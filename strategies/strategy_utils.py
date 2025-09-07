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
    # Alias (métodos alias directos)
    "hammer_reversal": "hammer_reversal",
    "bullish_engulfing_reversal": "bullish_engulfing_reversal",
    "morning_star_swing": "morning_star_swing",
    "hanging_man_reversal": "hanging_man_reversal",
    "bearish_engulfing_reversal": "bearish_engulfing_reversal",
    "evening_star_swing": "evening_star_swing",
    "doji_indecision": "doji_indecision",
    "three_white_soldiers": "three_white_soldiers",
    "three_black_crows": "three_black_crows",

    # Estrategias principales basadas en patrones (sufijo _strategy)
    "hammer_reversal_strategy": "hammer_reversal_strategy",
    "bullish_engulfing_strategy": "bullish_engulfing_strategy",
    "bearish_engulfing_strategy": "bearish_engulfing_strategy",
    "morning_star_strategy": "morning_star_strategy",
    "evening_star_strategy": "evening_star_strategy",
    "hanging_man_strategy": "hanging_man_strategy",
    "three_white_soldiers_strategy": "three_white_soldiers_strategy",
    "three_black_crows_strategy": "three_black_crows_strategy",
    "doji_reversal_strategy": "doji_reversal_strategy",

    # Tendencia / combinadas
    "marubozu_trend": "marubozu_trend",
    "filter_with_trend": "filter_with_trend",
    "stop_loss_take_profit": "stop_loss_take_profit",
    "scalping_reversal": "scalping_reversal",
    "swing_trading": "swing_trading",

    # Nuevos métodos añadidos
    "shooting_star_strategy": "shooting_star_strategy",
    "spinning_top_strategy": "spinning_top_strategy",
    "inverted_hammer_strategy": "inverted_hammer_strategy",
    "piercing_line_strategy": "piercing_line_strategy",
    "dark_cloud_cover_strategy": "dark_cloud_cover_strategy",
    "tweezer_top_strategy": "tweezer_top_strategy",
    "tweezer_bottom_strategy": "tweezer_bottom_strategy",
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
    # Excluir estrategias que no deben aparecer en la selección del modal
    _forex_exclude = {"carry_trade_strategy", "hedging_overlay", "martingale_overlay"}
    forex_strategies = sorted([
        name for name in _FOREX_ALIAS_TO_METHOD.keys()
        if name not in _forex_exclude
    ])
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
