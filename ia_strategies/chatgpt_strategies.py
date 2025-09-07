import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class QuantumExitConfig:
    use_signal_change: bool = True
    use_stop_loss: bool = True
    use_take_profit: bool = True
    use_trailing_stop: bool = False
    
    quick_profit_multiplier: float = 0.5
    quick_loss_multiplier: float = 0.5
    atr_period: int = 14
    
    def __post_init__(self):
        # Permitir valores más bajos (ej. 0.1, 0.2) como en deep_seek_strategies
        self.quick_profit_multiplier = max(0.05, min(self.quick_profit_multiplier, 2.0))
        self.quick_loss_multiplier = max(0.05, min(self.quick_loss_multiplier, 1.0))

class SuperheroStrategies:
    def __init__(self, data):
        self.data = data.copy()
        required_cols = ['Open', 'High', 'Low', 'Close']
        for col in required_cols:
            if col not in self.data.columns:
                raise ValueError(f"Columna requerida '{col}' no encontrada en los datos")
        if 'Volume' not in self.data.columns:
            self.data['Volume'] = 1.0
        self._calculate_indicators()

    def _calculate_indicators(self):
        high_low = self.data['High'] - self.data['Low']
        high_close = np.abs(self.data['High'] - self.data['Close'].shift())
        low_close = np.abs(self.data['Low'] - self.data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        self.data['ATR'] = true_range.rolling(window=14).mean()
        
        self.data['EMA20'] = self.data['Close'].ewm(span=20).mean()
        self.data['EMA50'] = self.data['Close'].ewm(span=50).mean()
        
        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))
        
        self.data['Volume_MA'] = self.data['Volume'].rolling(window=20).mean()

    def _apply_quantum_exit_logic(self, df, strategy_name, config=None):
        if config is None:
            config = QuantumExitConfig()
        
        df = df.copy()
        df['ExecSignal'] = 0
        df['Position'] = 0
        df['StopLoss'] = np.nan
        df['TakeProfit'] = np.nan
        df['ExitReason'] = ''
        df['P/L'] = 0.0
        
        position = 0
        entry_price = 0.0
        contract_size = 1
        
        for i in range(len(df)):
            current_signal = int(df.iloc[i]['Signal']) if not pd.isna(df.iloc[i]['Signal']) else 0
            current_price = float(df.iloc[i]['Close'])
            
            if position != 0:
                if position == 1:
                    unrealized_pl = (current_price - entry_price) * contract_size
                else:
                    unrealized_pl = (entry_price - current_price) * contract_size
                
                exit_signal = 0
                exit_reason = ''
                
                # Usar umbrales configurables del QuantumExitConfig
                tp_target = float(config.quick_profit_multiplier)
                sl_target = float(config.quick_loss_multiplier)
                if unrealized_pl >= tp_target:
                    exit_signal = -position
                    exit_reason = 'TAKE_PROFIT'
                elif unrealized_pl <= -sl_target:
                    exit_signal = -position
                    exit_reason = 'STOP_LOSS'
                elif config.use_signal_change and current_signal == -position:
                    exit_signal = -position
                    exit_reason = 'SIGNAL_CHANGE'
                
                if exit_signal != 0:
                    df.iloc[i, df.columns.get_loc('ExecSignal')] = exit_signal
                    df.iloc[i, df.columns.get_loc('ExitReason')] = exit_reason
                    df.iloc[i, df.columns.get_loc('P/L')] = unrealized_pl
                    position = 0
                    entry_price = 0.0
            
            if position == 0 and current_signal != 0:
                df.iloc[i, df.columns.get_loc('ExecSignal')] = current_signal
                position = current_signal
                entry_price = current_price
            
            df.iloc[i, df.columns.get_loc('Position')] = position
        
        return df

    # ----------------- NUEVAS ESTRATEGIAS DE SUPERHÉROES -----------------

    def iron_guardian(self, config=None):
        df = self.data.copy()
        df['Signal'] = 0
        support = df['Low'].rolling(window=15).min()
        resistance = df['High'].rolling(window=15).max()
        buy_condition = (df['Close'] > df['Open']) & (df['Low'] <= support * 1.005) & (df['RSI'] < 55)
        sell_condition = (df['Close'] < df['Open']) & (df['High'] >= resistance * 0.995) & (df['RSI'] > 45)
        df.loc[buy_condition, 'Signal'] = 1
        df.loc[sell_condition, 'Signal'] = -1
        return self._apply_quantum_exit_logic(df, 'iron_guardian', config)

    def shadow_panther(self, config=None):
        df = self.data.copy()
        df['Signal'] = 0
        range_size = df['High'] - df['Low']
        avg_range = range_size.rolling(10).mean()
        breakout_up = (df['Close'] > df['High'].shift(1)) & (range_size > avg_range * 1.2) & (df['RSI'] < 65)
        breakout_down = (df['Close'] < df['Low'].shift(1)) & (range_size > avg_range * 1.2) & (df['RSI'] > 35)
        df.loc[breakout_up, 'Signal'] = 1
        df.loc[breakout_down, 'Signal'] = -1
        return self._apply_quantum_exit_logic(df, 'shadow_panther', config)

    def thunder_hawk(self, config=None):
        df = self.data.copy()
        df['Signal'] = 0
        buy_condition = (df['Close'] > df['EMA20']) & (df['EMA20'] > df['EMA50']) & (df['RSI'] > 50)
        sell_condition = (df['Close'] < df['EMA20']) & (df['EMA20'] < df['EMA50']) & (df['RSI'] < 50)
        df.loc[buy_condition, 'Signal'] = 1
        df.loc[sell_condition, 'Signal'] = -1
        return self._apply_quantum_exit_logic(df, 'thunder_hawk', config)

    def crimson_blade(self, config=None):
        df = self.data.copy()
        df['Signal'] = 0
        big_green = (df['Close'] > df['Open']) & ((df['Close'] - df['Open']) / df['Open'] > 0.015)
        big_red = (df['Close'] < df['Open']) & ((df['Open'] - df['Close']) / df['Open'] > 0.015)
        df.loc[big_green & (df['Volume'] > df['Volume_MA']), 'Signal'] = 1
        df.loc[big_red & (df['Volume'] > df['Volume_MA']), 'Signal'] = -1
        return self._apply_quantum_exit_logic(df, 'crimson_blade', config)

    def phantom_rider(self, config=None):
        df = self.data.copy()
        df['Signal'] = 0
        momentum = df['Close'].pct_change(3)
        df.loc[(momentum > 0.01) & (df['RSI'] < 65), 'Signal'] = 1
        df.loc[(momentum < -0.01) & (df['RSI'] > 35), 'Signal'] = -1
        return self._apply_quantum_exit_logic(df, 'phantom_rider', config)

    def star_guardian(self, config=None):
        df = self.data.copy()
        df['Signal'] = 0
        ma10 = df['Close'].rolling(10).mean()
        ma30 = df['Close'].rolling(30).mean()
        df.loc[(ma10 > ma30) & (df['RSI'] > 45) & (df['RSI'] < 70), 'Signal'] = 1
        df.loc[(ma10 < ma30) & (df['RSI'] < 55) & (df['RSI'] > 30), 'Signal'] = -1
        return self._apply_quantum_exit_logic(df, 'star_guardian', config)

    def lunar_knight(self, config=None):
        df = self.data.copy()
        df['Signal'] = 0
        low_volatility = (df['ATR'] < df['ATR'].rolling(20).mean() * 0.8)
        breakout = (df['Close'] > df['EMA20']) | (df['Close'] < df['EMA20'])
        df.loc[low_volatility & breakout & (df['RSI'] < 60), 'Signal'] = 1
        df.loc[low_volatility & breakout & (df['RSI'] > 40), 'Signal'] = -1
        return self._apply_quantum_exit_logic(df, 'lunar_knight', config)

    def omega_sentinel(self, config=None):
        df = self.data.copy()
        df['Signal'] = 0
        df.loc[(df['RSI'] < 30) & (df['RSI'].shift(1) < 30), 'Signal'] = 1
        df.loc[(df['RSI'] > 70) & (df['RSI'].shift(1) > 70), 'Signal'] = -1
        return self._apply_quantum_exit_logic(df, 'omega_sentinel', config)

    def nova_striker(self, config=None):
        df = self.data.copy()
        df['Signal'] = 0
        cross_up = (df['Close'] > df['EMA20']) & (df['Close'].shift(1) <= df['EMA20'].shift(1))
        cross_down = (df['Close'] < df['EMA20']) & (df['Close'].shift(1) >= df['EMA20'].shift(1))
        df.loc[cross_up & (df['RSI'] < 65), 'Signal'] = 1
        df.loc[cross_down & (df['RSI'] > 35), 'Signal'] = -1
        return self._apply_quantum_exit_logic(df, 'nova_striker', config)

    def titan_shadow(self, config=None):
        df = self.data.copy()
        df['Signal'] = 0
        body = (df['Close'] - df['Open']).abs()
        candle_range = df['High'] - df['Low']
        upper_shadow = df['High'] - df[['Close', 'Open']].max(axis=1)
        lower_shadow = df[['Close', 'Open']].min(axis=1) - df['Low']
        hammer = (lower_shadow > body * 2) & (body / candle_range < 0.3)
        shooting_star = (upper_shadow > body * 2) & (body / candle_range < 0.3)
        df.loc[hammer & (df['RSI'] < 60), 'Signal'] = 1
        df.loc[shooting_star & (df['RSI'] > 40), 'Signal'] = -1
        return self._apply_quantum_exit_logic(df, 'titan_shadow', config)
