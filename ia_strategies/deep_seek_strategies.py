# strategies/candle_strategies.py

import pandas as pd
import numpy as np
from dataclasses import dataclass
import random

@dataclass
class QuantumExitConfig:
    """Configuración para estrategias de trading cuántico."""
    use_signal_change: bool = True
    use_stop_loss: bool = True
    use_take_profit: bool = True
    use_trailing_stop: bool = False
    
    # Parámetros específicos para estrategias rápidas
    quick_profit_multiplier: float = 0.5  # Multiplicador para take profit rápido
    quick_loss_multiplier: float = 0.5    # Multiplicador para stop loss
    atr_period: int = 14
    
    def __post_init__(self):
        # Validar parámetros
        # Permitir valores más bajos (ej. 0.1, 0.2) según los casos del usuario
        self.quick_profit_multiplier = max(0.05, min(self.quick_profit_multiplier, 2.0))
        self.quick_loss_multiplier = max(0.05, min(self.quick_loss_multiplier, 1.0))

class QuantumStrategies:
    def __init__(self, data):
        """
        data: DataFrame con columnas ['Open','High','Low','Close','Volume']
        """
        self.data = data.copy()
        
        # Asegurar que tenemos las columnas necesarias
        required_cols = ['Open', 'High', 'Low', 'Close']
        for col in required_cols:
            if col not in self.data.columns:
                raise ValueError(f"Columna requerida '{col}' no encontrada en los datos")
        
        # Agregar volumen dummy si no existe
        if 'Volume' not in self.data.columns:
            self.data['Volume'] = 1.0
            
        # Calcular indicadores básicos
        self._calculate_indicators()
    
    def _calculate_indicators(self):
        """Calcula indicadores técnicos necesarios para las estrategias"""
        # ATR para gestión de riesgo
        high_low = self.data['High'] - self.data['Low']
        high_close = np.abs(self.data['High'] - self.data['Close'].shift())
        low_close = np.abs(self.data['Low'] - self.data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        self.data['ATR'] = true_range.rolling(window=14).mean()
        
        # Medias móviles
        self.data['EMA20'] = self.data['Close'].ewm(span=20).mean()
        self.data['EMA50'] = self.data['Close'].ewm(span=50).mean()
        
        # RSI
        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))
        
        # Volumen promedio
        self.data['Volume_MA'] = self.data['Volume'].rolling(window=20).mean()
    
    def _apply_quantum_exit_logic(self, df, strategy_name, config=None):
        """Lógica de salida para estrategias rápidas usando umbrales configurables (TP/SL en $)."""
        if config is None:
            config = QuantumExitConfig()
        
        df = df.copy()
        
        # Inicializar columnas de salida
        df['ExecSignal'] = 0
        df['Position'] = 0
        df['StopLoss'] = np.nan
        df['TakeProfit'] = np.nan
        df['ExitReason'] = ''
        df['P/L'] = 0.0
        
        position = 0
        entry_price = 0.0
        entry_index = 0
        contract_size = 1  # Ajustar según el instrumento
        
        for i in range(len(df)):
            current_signal = int(df.iloc[i]['Signal']) if not pd.isna(df.iloc[i]['Signal']) else 0
            current_price = float(df.iloc[i]['Close'])
            current_low = float(df.iloc[i]['Low'])
            current_high = float(df.iloc[i]['High'])
            
            # Si hay posición abierta, calcular P/L actual
            if position != 0:
                if position == 1:
                    unrealized_pl = (current_price - entry_price) * contract_size
                else:  # position == -1
                    unrealized_pl = (entry_price - current_price) * contract_size
                
                # Verificar si alcanzamos take profit o stop loss
                exit_signal = 0
                exit_reason = ''
                
                # Umbrales de salida basados en configuración
                tp_target = float(config.quick_profit_multiplier)
                sl_target = float(config.quick_loss_multiplier)
                
                # Take Profit: cerrar cuando la ganancia alcance el objetivo
                if unrealized_pl >= tp_target:
                    exit_signal = -position
                    exit_reason = 'TAKE_PROFIT'
                # Stop Loss: cerrar cuando la pérdida alcance el objetivo
                elif unrealized_pl <= -sl_target:
                    exit_signal = -position
                    exit_reason = 'STOP_LOSS'
                
                # Cambio de señal
                elif config.use_signal_change and current_signal == -position:
                    exit_signal = -position
                    exit_reason = 'SIGNAL_CHANGE'
                
                if exit_signal != 0:
                    df.iloc[i, df.columns.get_loc('ExecSignal')] = exit_signal
                    df.iloc[i, df.columns.get_loc('ExitReason')] = exit_reason
                    df.iloc[i, df.columns.get_loc('P/L')] = unrealized_pl
                    position = 0
                    entry_price = 0.0
            
            # Entrar en nuevas posiciones
            if position == 0 and current_signal != 0:
                # Ajustar tamaño de contrato para objetivo de ganancia
                contract_size = 1.0 / max(abs(current_price - (current_price + (0.75 * np.sign(current_signal)))), 0.001)
                contract_size = min(max(contract_size, 0.1), 10)  # Limitar tamaño
                
                df.iloc[i, df.columns.get_loc('ExecSignal')] = current_signal
                position = current_signal
                entry_price = current_price
                entry_index = i
            
            df.iloc[i, df.columns.get_loc('Position')] = position
        
        return df

    # ----------------- ESTRATEGIAS RÁPIDAS -----------------
    
    def vortice_rapido(self, config=None):
        """Estrategia Vórtice Rápido: Entradas en cruces de EMA con alta volatilidad"""
        df = self.data.copy()
        df['Signal'] = 0
        
        # Señal de compra: EMA20 cruza por arriba EMA50 con RSI > 40
        buy_condition = (df['EMA20'] > df['EMA50']) & (df['EMA20'].shift(1) <= df['EMA50'].shift(1)) & (df['RSI'] > 40)
        
        # Señal de venta: EMA20 cruza por abajo EMA50 con RSI < 60
        sell_condition = (df['EMA20'] < df['EMA50']) & (df['EMA20'].shift(1) >= df['EMA50'].shift(1)) & (df['RSI'] < 60)
        
        df.loc[buy_condition, 'Signal'] = 1
        df.loc[sell_condition, 'Signal'] = -1
        
        return self._apply_quantum_exit_logic(df, 'vortice_rapido', config)
    
    def pulso_estelar(self, config=None):
        """Estrategia Pulso Estelar: Entradas en velas grandes con volumen"""
        df = self.data.copy()
        df['Signal'] = 0
        
        # Calcular tamaño de vela y volumen relativo
        candle_size = (df['Close'] - df['Open']).abs() / df['Open']
        volume_ratio = df['Volume'] / df['Volume_MA']
        
        # Señal de compra: Vela alcista grande con alto volumen
        buy_condition = (df['Close'] > df['Open']) & (candle_size > 0.01) & (volume_ratio > 1.5) & (df['RSI'] < 70)
        
        # Señal de venta: Vela bajista grande con alto volumen
        sell_condition = (df['Close'] < df['Open']) & (candle_size > 0.01) & (volume_ratio > 1.5) & (df['RSI'] > 30)
        
        df.loc[buy_condition, 'Signal'] = 1
        df.loc[sell_condition, 'Signal'] = -1
        
        return self._apply_quantum_exit_logic(df, 'pulso_estelar', config)
    
    def quantum_reversal(self, config=None):
        """Estrategia Quantum Reversal: Entradas en reversiones de RSI extremo"""
        df = self.data.copy()
        df['Signal'] = 0
        
        # RSI sale de sobrecompra (reversión bajista)
        rsi_sell = (df['RSI'] > 70) & (df['RSI'].shift(1) > 70) & (df['RSI'].shift(2) > 70) & (df['RSI'] < df['RSI'].shift(1))
        
        # RSI sale de sobreventa (reversión alcista)
        rsi_buy = (df['RSI'] < 30) & (df['RSI'].shift(1) < 30) & (df['RSI'].shift(2) < 30) & (df['RSI'] > df['RSI'].shift(1))
        
        df.loc[rsi_buy, 'Signal'] = 1
        df.loc[rsi_sell, 'Signal'] = -1
        
        return self._apply_quantum_exit_logic(df, 'quantum_reversal', config)
    
    def nexus_volatilidad(self, config=None):
        """Estrategia Nexus Volatilidad: Entradas en expansión de volatilidad"""
        df = self.data.copy()
        df['Signal'] = 0
        
        # Calcular bandas de volatilidad
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['UpperBand'] = df['MA20'] + 1.5 * df['ATR']
        df['LowerBand'] = df['MA20'] - 1.5 * df['ATR']
        
        # Señal de compra: Precio toca banda inferior con volumen
        buy_condition = (df['Low'] <= df['LowerBand']) & (df['Volume'] > df['Volume_MA']) & (df['RSI'] < 40)
        
        # Señal de venta: Precio toca banda superior con volumen
        sell_condition = (df['High'] >= df['UpperBand']) & (df['Volume'] > df['Volume_MA']) & (df['RSI'] > 60)
        
        df.loc[buy_condition, 'Signal'] = 1
        df.loc[sell_condition, 'Signal'] = -1
        
        return self._apply_quantum_exit_logic(df, 'nexus_volatilidad', config)
    
    def sincronia_dual(self, config=None):
        """Estrategia Sincronía Dual: Confirmación de precio y volumen"""
        df = self.data.copy()
        df['Signal'] = 0
        
        # Tendencia alcista confirmada
        uptrend = (df['Close'] > df['EMA20']) & (df['EMA20'] > df['EMA50']) & (df['Volume'] > df['Volume_MA'])
        
        # Tendencia bajista confirmada
        downtrend = (df['Close'] < df['EMA20']) & (df['EMA20'] < df['EMA50']) & (df['Volume'] > df['Volume_MA'])
        
        # Entrar en retrocesos dentro de la tendencia
        buy_condition = uptrend & (df['Close'] < df['EMA20']) & (df['RSI'] < 50)
        sell_condition = downtrend & (df['Close'] > df['EMA20']) & (df['RSI'] > 50)
        
        df.loc[buy_condition, 'Signal'] = 1
        df.loc[sell_condition, 'Signal'] = -1
        
        return self._apply_quantum_exit_logic(df, 'sincronia_dual', config)
    
    def impulso_ciclico(self, config=None):
        """Estrategia Impulso Cíclico: Patrones de momentum a corto plazo"""
        df = self.data.copy()
        df['Signal'] = 0
        
        # Calcular momentum
        df['Momentum'] = df['Close'].pct_change(periods=5)
        
        # Momento alcista con volumen
        buy_momentum = (df['Momentum'] > 0.02) & (df['Volume'] > df['Volume_MA'] * 1.2) & (df['RSI'] < 65)
        
        # Momento bajista con volumen
        sell_momentum = (df['Momentum'] < -0.02) & (df['Volume'] > df['Volume_MA'] * 1.2) & (df['RSI'] > 35)
        
        df.loc[buy_momentum, 'Signal'] = 1
        df.loc[sell_momentum, 'Signal'] = -1
        
        return self._apply_quantum_exit_logic(df, 'impulso_ciclico', config)
    
    def armonia_temporal(self, config=None):
        """Estrategia Armonía Temporal: Alineación de múltiples timeframes simulados"""
        df = self.data.copy()
        df['Signal'] = 0
        
        # Media rápida y lenta para simular múltiples timeframes
        df['EMA10'] = df['Close'].ewm(span=10).mean()
        df['EMA30'] = df['Close'].ewm(span=30).mean()
        df['EMA60'] = df['Close'].ewm(span=60).mean()
        
        # Alineación alcista: EMA10 > EMA30 > EMA60
        bullish_alignment = (df['EMA10'] > df['EMA30']) & (df['EMA30'] > df['EMA60'])
        
        # Alineación bajista: EMA10 < EMA30 < EMA60
        bearish_alignment = (df['EMA10'] < df['EMA30']) & (df['EMA30'] < df['EMA60'])
        
        # Entrar en la dirección de la alineación
        df.loc[bullish_alignment & (df['RSI'] < 60), 'Signal'] = 1
        df.loc[bearish_alignment & (df['RSI'] > 40), 'Signal'] = -1
        
        return self._apply_quantum_exit_logic(df, 'armonia_temporal', config)
    
    def eco_mercado(self, config=None):
        """Estrategia Eco Mercado: Reacciones a soportes y resistencias"""
        df = self.data.copy()
        df['Signal'] = 0
        
        # Calcular soportes y resistencias simples
        df['Resistance'] = df['High'].rolling(window=20).max()
        df['Support'] = df['Low'].rolling(window=20).min()
        
        # Rebote en soporte con volumen
        bounce_support = (df['Low'] <= df['Support'] * 1.005) & (df['Close'] > df['Open']) & (df['Volume'] > df['Volume_MA'])
        
        # Rechazo en resistencia con volumen
        bounce_resistance = (df['High'] >= df['Resistance'] * 0.995) & (df['Close'] < df['Open']) & (df['Volume'] > df['Volume_MA'])
        
        df.loc[bounce_support & (df['RSI'] < 60), 'Signal'] = 1
        df.loc[bounce_resistance & (df['RSI'] > 40), 'Signal'] = -1
        
        return self._apply_quantum_exit_logic(df, 'eco_mercado', config)
    
    def fractal_quantico(self, config=None):
        """Estrategia Fractal Cuántico: Patrones de precio repetitivos"""
        df = self.data.copy()
        df['Signal'] = 0
        
        # Detectar velas de ruptura
        df['Range'] = df['High'] - df['Low']
        avg_range = df['Range'].rolling(window=20).mean()
        
        # Ruptura alcista: Vela grande que cierra cerca del máximo
        breakout_bullish = (df['Range'] > avg_range * 1.5) & (df['Close'] > df['Open']) & ((df['Close'] - df['Low']) / df['Range'] > 0.7)
        
        # Ruptura bajista: Vela grande que cierra cerca del mínimo
        breakout_bearish = (df['Range'] > avg_range * 1.5) & (df['Close'] < df['Open']) & ((df['High'] - df['Close']) / df['Range'] > 0.7)
        
        df.loc[breakout_bullish & (df['Volume'] > df['Volume_MA'] * 1.5), 'Signal'] = 1
        df.loc[breakout_bearish & (df['Volume'] > df['Volume_MA'] * 1.5), 'Signal'] = -1
        
        return self._apply_quantum_exit_logic(df, 'fractal_quantico', config)
    
    def resonance_trading(self, config=None):
        """Estrategia Resonance Trading: Convergencia de múltiples indicadores"""
        df = self.data.copy()
        df['Signal'] = 0
        
        # Múltiples condiciones para confirmación
        bullish_conditions = (
            (df['Close'] > df['EMA20']) &
            (df['EMA20'] > df['EMA50']) &
            (df['RSI'] > 45) & (df['RSI'] < 70) &
            (df['Volume'] > df['Volume_MA']) &
            (df['Close'] > df['Open'])
        )
        
        bearish_conditions = (
            (df['Close'] < df['EMA20']) &
            (df['EMA20'] < df['EMA50']) &
            (df['RSI'] < 55) & (df['RSI'] > 30) &
            (df['Volume'] > df['Volume_MA']) &
            (df['Close'] < df['Open'])
        )
        
        df.loc[bullish_conditions, 'Signal'] = 1
        df.loc[bearish_conditions, 'Signal'] = -1
        
        return self._apply_quantum_exit_logic(df, 'resonance_trading', config)

    # Función para backtesting rápido
    def test_quantum_strategies(data, initial_balance=1000):
        """Prueba todas las estrategias y muestra resultados"""
        strategies = [
            'vortice_rapido', 'pulso_estelar', 'quantum_reversal',
            'nexus_volatilidad', 'sincronia_dual', 'impulso_ciclico',
            'armonia_temporal', 'eco_mercado', 'fractal_quantico', 'resonance_trading'
        ]
        
        results = {}
        quantum = QuantumStrategies(data)
        
        for strategy_name in strategies:
            try:
                strategy_func = getattr(quantum, strategy_name)
                result_df = strategy_func()
                
                # Calcular métricas de performance
                trades = result_df[result_df['ExecSignal'] != 0]
                if len(trades) > 0:
                    winning_trades = trades[trades['P/L'] > 0]
                    losing_trades = trades[trades['P/L'] < 0]
                    
                    win_rate = len(winning_trades) / len(trades) if len(trades) > 0 else 0
                    avg_win = winning_trades['P/L'].mean() if len(winning_trades) > 0 else 0
                    avg_loss = losing_trades['P/L'].mean() if len(losing_trades) > 0 else 0
                    profit_factor = abs(winning_trades['P/L'].sum() / losing_trades['P/L'].sum()) if losing_trades['P/L'].sum() != 0 else float('inf')
                    
                    results[strategy_name] = {
                        'total_trades': len(trades),
                        'win_rate': win_rate,
                        'avg_win': avg_win,
                        'avg_loss': avg_loss,
                        'profit_factor': profit_factor,
                        'total_profit': trades['P/L'].sum()
                    }
            
            except Exception as e:
                print(f"Error en {strategy_name}: {str(e)}")
                continue
        
        return results
