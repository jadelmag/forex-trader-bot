def trend_following(self, short_window=20, long_window=50, exec_lag=1, **risk_kwargs):
    df = self.data.copy()
    df['EMA_short'] = df['Close'].ewm(span=short_window, adjust=False).mean()
    df['EMA_long']  = df['Close'].ewm(span=long_window, adjust=False).mean()

    cond = df['EMA_short'] > df['EMA_long']
    
    # Usar el método recomendado por pandas para evitar downcasting
    cond_shifted = cond.shift(1)
    cond_shifted_filled = cond_shifted.fillna(False)
    cond_shifted_filled = cond_shifted_filled.infer_objects(copy=False)  # <-- Método recomendado
    
    cross_up = cond & (~cond_shifted_filled)
    cross_dn = (~cond) & cond_shifted_filled

    df['Signal'] = 0
    df.loc[cross_up, 'Signal'] = 1
    df.loc[cross_dn, 'Signal'] = -1

    df = self._apply_risk_management(df, **risk_kwargs)
    return self._attach_execution(df[['Close','EMA_short','EMA_long',
                                    'Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)



# ============================================================
# Capital final: $1,199.49
# Beneficio total: $199.49
# Operaciones ganadas: 16
# Operaciones perdidas: 13
# Win Rate: 55.2%
# Slots utilizados: 0/5
# ============================================================
# RESUMEN EN INTERFAZ
# Dinero total: $1,199.49
# Beneficios acumulados: $337.20
# Pérdidas acumuladas: $137.71
# ============================================================

# Current Function

def trend_following(self, short_window=20, long_window=50, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        df['EMA_short'] = df['Close'].ewm(span=short_window, adjust=False).mean()
        df['EMA_long']  = df['Close'].ewm(span=long_window, adjust=False).mean()

        cond = df['EMA_short'] > df['EMA_long']
        
        # Usar numpy para manejar los NaN de manera más eficiente
        cond_shifted = cond.shift(1)
        cond_shifted_filled = cond_shifted.where(cond_shifted.notna(), False)
        
        cross_up = cond & (~cond_shifted_filled)
        cross_dn = (~cond) & cond_shifted_filled

        df['Signal'] = 0
        df.loc[cross_up, 'Signal'] = 1
        df.loc[cross_dn, 'Signal'] = -1

        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','EMA_short','EMA_long',
                                        'Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)


# ============================================================
# ESTADÍSTICAS FINALES DEL RISK MANAGER
# ============================================================
# Capital final: $1,175.74
# Beneficio total: $175.74
# Operaciones ganadas: 15
# Operaciones perdidas: 13
# Win Rate: 53.6%
# Slots utilizados: 0/5
# ============================================================
# RESUMEN EN INTERFAZ
# Dinero total: $1,175.74
# Beneficios acumulados: $312.56
# Pérdidas acumuladas: $136.83
# ============================================================