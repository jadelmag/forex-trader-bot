# app/handlers/strategy_handler.py
import tkinter as tk
from tkinter import messagebox
import numpy as np
import pandas as pd

from strategies import ForexStrategies, CandleStrategies
from strategies.strategy_utils import get_available_strategies, resolve_strategy_name
from strategies.risk_manager import RiskManager
from strategies.risk_manager_integration import RiskManagerIntegration, RiskConfig

class StrategyHandler:
    def __init__(self, main_app):
        self.main_app = main_app
        self.dinero_ficticio = 0
        self.beneficios = 0
        self.perdidas = 0
        self.risk_manager = None
        self.risk_integration = None
        
    def add_dinero(self):
        """Añade dinero ficticio a la simulación"""
        try:
            cantidad = float(self.main_app.menu_bar.entry_dinero.get())
            self.dinero_ficticio += cantidad
            
            # Sincronizar el RiskManager
            if self.risk_manager is not None:
                self.risk_manager.capital_inicial = float(self.dinero_ficticio)
                self.risk_manager.capital = float(self.dinero_ficticio)
                
            self.actualizar_labels()
            self.main_app.menu_bar.update_buttons_state()
            
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número válido")
            
    def actualizar_labels(self):
        """Actualiza las etiquetas de dinero, beneficios y pérdidas"""
        self.main_app.status_bar.actualizar_labels(
            self.dinero_ficticio, 
            self.beneficios, 
            self.perdidas
        )
  
    def cargar_estrategias(self):
        """Carga y aplica estrategias de trading"""
        if self.main_app.csv_handler.df_actual is None:
            messagebox.showwarning("Atención", "Cargue primero un CSV o datos procesados")
            return
            
        # Instanciar estrategias
        self.strategies_fx = ForexStrategies(self.main_app.csv_handler.df_actual)
        self.strategies_candle = CandleStrategies(self.main_app.csv_handler.df_actual)
        
        # Obtener estrategias disponibles
        fx_methods, candle_methods = get_available_strategies()
        
        # Abrir modal de selección de estrategias
        from ..modals.estrategias_modal import EstrategiasModal
        EstrategiasModal(
            self.main_app,
            estrategias_fx=sorted(fx_methods),
            estrategias_candle=sorted(candle_methods),
            callback=self._on_estrategias_seleccionadas
        )
        
    
        def _on_estrategias_seleccionadas(self, seleccion, max_orders=5, opciones=None):
        """
        Aplica las estrategias seleccionadas usando el Risk Manager
        """
        if opciones is None:
            opciones = {"mostrar_deteccion": True, "mostrar_simulacion": True}
        
        if not seleccion or self.df_actual is None:
            return

        # Obtener capital inicial del entry_dinero
        try:
            capital_inicial = float(self.entry_dinero.get())
            if capital_inicial <= 0:
                raise ValueError("El capital debe ser mayor a 0")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un capital válido en el campo 'Dinero ficticio'")
            return

        # Configurar Risk Manager
        self.risk_manager = RiskManager(max_operaciones_activas=max_orders, capital_inicial=capital_inicial)
        config = RiskConfig(enable_sell_operations=True)
        self.risk_integration = RiskManagerIntegration(self.risk_manager, debug_mode=False)
        self.risk_manager.reset()

        # Asegurar que las instancias existen
        if not hasattr(self, 'strategies_fx'):
            self.strategies_fx = ForexStrategies(self.df_actual)
        if not hasattr(self, 'strategies_candle'):
            self.strategies_candle = CandleStrategies(self.df_actual)

        df_new = self.df_actual.copy()
        patterns_instance = None

        # Mapa auxiliar: tipo de estrategia y un ID normalizado para unicidad
        estrategia_tipo_map = {nombre: params.get("tipo") for nombre, params in seleccion.items()}
        estrategia_id_map = {}
        for nombre, params in seleccion.items():
            tipo = params.get("tipo")
            if tipo == 'forex':
                try:
                    estrategia_id_map[nombre] = resolve_strategy_name(nombre, 'forex')
                except Exception:
                    estrategia_id_map[nombre] = nombre
            else:
                estrategia_id_map[nombre] = nombre

        for nombre, params in seleccion.items():
            try:
                tipo_sel = params.get("tipo")
                if tipo_sel == "forex":
                    metodo_real = resolve_strategy_name(nombre, "forex")
                    metodo = getattr(self.strategies_fx, metodo_real, None)
                    if not callable(metodo):
                        self.log(f"Estrategia Forex no encontrada: {nombre}", color='red')
                        continue
                    
                    risk_kwargs = {
                        'risk_per_trade': params.get('riesgo', 0.01),
                        'rr_ratio': params.get('rr', 2.0),
                    }
                    df_res = metodo(**risk_kwargs)

                elif tipo_sel == "candle":
                    metodo_real = resolve_strategy_name(nombre, "candle")
                    metodo = getattr(self.strategies_candle, metodo_real, None)
                    if not callable(metodo):
                        self.log(f"Estrategia Candle no encontrada: {nombre}", color='red')
                        continue
                    df_res = metodo()

                elif tipo_sel == "pattern":
                    if patterns_instance is None:
                        patterns_instance = CandlestickPatterns(self.df_actual)
                    # Permitir claves con namespace 'pattern::' para evitar colisiones
                    metodo_name = nombre.split("::", 1)[1] if nombre.startswith("pattern::") else nombre
                    metodo = getattr(patterns_instance, metodo_name, None)
                    if not callable(metodo):
                        self.log(f"Patrón no encontrado: {nombre}", color='red')
                        continue
                    df_res = metodo()
                else:
                    self.log(f"Tipo de selección desconocido: {tipo_sel}", color='red')
                    continue

                # Aplicar señales al df_new
                if 'Signal' in df_res.columns:
                    col_name = f"{nombre}_Signal"
                    sig_series = df_res['Signal']
                    nonzero_idx = sig_series[sig_series != 0].index
                    sig_indices = nonzero_idx if (isinstance(max_orders, int) and max_orders <= 0) else nonzero_idx[:max_orders]
                    df_new[col_name] = 0
                    df_new.loc[sig_indices, col_name] = sig_series.loc[sig_indices]

                    if opciones["mostrar_deteccion"]:
                        for idx in sig_indices:
                            val = sig_series.loc[idx]
                            close_val = df_new.loc[idx, 'Close'] if 'Close' in df_new.columns else None
                            fecha_str = idx.strftime('%d/%m/%Y %H:%M') if hasattr(idx, 'strftime') else str(idx)
                            if tipo_sel == "forex":
                                tipo = "Forex"
                                color = 'cyan'
                            elif tipo_sel == "candle":
                                tipo = "Candle"
                                color = 'yellow'
                            else:
                                tipo = "Pattern"
                                color = 'magenta'
                            msg = f"DETECCIÓN: {nombre} ({tipo}) | Fecha: {fecha_str} | Señal: {val}"
                            if close_val is not None:
                                msg += f" | Precio: {close_val:.5f}"
                            self.log(msg, color=color)

            except Exception as e:
                self.log(f"Error aplicando estrategia {nombre}: {e}", color='red')

        # --- Segunda pasada: Simulación con Risk Manager ---
        if opciones["mostrar_simulacion"]:
            self.log("="*60, color='white')
            self.log("INICIANDO SIMULACIÓN CON RISK MANAGER", color='yellow')
            self.log("="*60, color='white')

            df_new['ATR'] = (df_new['High'] - df_new['Low']).rolling(14).mean()
            df_new['ATR'] = df_new['ATR'].fillna((df_new['High'] - df_new['Low']).mean() * 0.1)

            beneficios_totales = 0
            perdidas_totales = 0
            resultados = []
            operaciones_abiertas = 0

            for idx, row in df_new.iterrows():
                if np.isnan(row['Close']):
                    continue

                operaciones_cerradas = self.risk_manager.verificar_cierre_operaciones(row['Close'], idx)

                for op in operaciones_cerradas:
                    profit = op.calcular_profit(op.precio_cierre)
                    if profit >= 0:
                        beneficios_totales += profit
                        # Actualizar beneficios acumulados en la UI inmediatamente
                        try:
                            self.beneficios = float(getattr(self, 'beneficios', 0.0) or 0.0) + float(profit)
                            self.label_beneficios.config(text=f"Beneficios: {self.beneficios:,.2f}$")
                        except Exception:
                            pass
                    else:
                        perdidas_totales += abs(profit)
                        # Actualizar pérdidas acumuladas en la UI inmediatamente
                        try:
                            self.perdidas = float(getattr(self, 'perdidas', 0.0) or 0.0) + float(abs(profit))
                            self.label_perdidas.config(text=f"Pérdidas: {self.perdidas:,.2f}$")
                        except Exception:
                            pass
                    resultados.append({'timestamp': idx, 'operacion': op, 'resultado': op.resultado, 'profit': profit})
                    color = 'green' if op.resultado == 'GANANCIA' else 'red'
                    self.log(f"CIERRE AUTOMÁTICO: {op} -> {op.resultado} | Profit: ${profit:+.2f}", color=color)

                # Tras procesar cierres, refrescar dinero visible inmediatamente
                try:
                    self._actualizar_dinero_visible(row['Close'])
                except Exception:
                    pass

                señales_del_dia = []
                for nombre in seleccion.keys():
                    col_name = f"{nombre}_Signal"
                    if col_name in df_new.columns and not np.isnan(df_new.loc[idx, col_name]) and df_new.loc[idx, col_name] != 0:
                        señales_del_dia.append({'estrategia': nombre, 'senal': df_new.loc[idx, col_name], 'precio': row['Close']})

                # Procesar señales de salida (-1) primero para cerrar operaciones
                for signal_info in señales_del_dia:
                    if signal_info['senal'] == -1:  # Solo procesar señales de salida
                        estrategia_id = estrategia_id_map.get(signal_info['estrategia'], signal_info['estrategia'])
                        atr_value = row.get('ATR')
                        if np.isnan(atr_value) or atr_value <= 0:
                            atr_value = (df_new['High'] - df_new['Low']).mean() * 0.1

                        # Procesar señal de salida
                        operaciones_cerradas_estrategia = self.risk_integration.procesar_senal(
                            senal=signal_info['senal'],
                            precio_actual=signal_info['precio'],
                            timestamp=idx,
                            atr_value=atr_value,
                            rr_ratio=2.0,
                            estrategia_nombre=estrategia_id
                        )

                        if operaciones_cerradas_estrategia and isinstance(operaciones_cerradas_estrategia, list):
                            for op in operaciones_cerradas_estrategia:
                                profit = op.calcular_profit(op.precio_cierre)
                                if profit >= 0:
                                    beneficios_totales += profit
                                    try:
                                        self.beneficios = float(getattr(self, 'beneficios', 0.0) or 0.0) + float(profit)
                                        self.label_beneficios.config(text=f"Beneficios: {self.beneficios:,.2f}$")
                                    except Exception:
                                        pass
                                else:
                                    perdidas_totales += abs(profit)
                                    try:
                                        self.perdidas = float(getattr(self, 'perdidas', 0.0) or 0.0) + float(abs(profit))
                                        self.label_perdidas.config(text=f"Pérdidas: {self.perdidas:,.2f}$")
                                    except Exception:
                                        pass
                                resultados.append({'timestamp': idx, 'operacion': op, 'resultado': op.resultado, 'profit': profit})
                                color = 'green' if op.resultado == 'GANANCIA' else 'red'
                                self.log(f"CIERRE POR ESTRATEGIA: {op} -> {op.resultado} | Profit: ${profit:+.2f}", color=color)

                        # Actualizar dinero visible tras cierre por estrategia
                        try:
                            self._actualizar_dinero_visible(row['Close'])
                        except Exception:
                            pass

                # Control por vela para señales de entrada:
                # - No abrir más de una COMPRA por la misma estrategia FOREX
                # - No abrir más de una COMPRA de ninguna estrategia FOREX en la misma vela
                opened_buy_for_strategy = set()
                opened_buy_any_forex = False

                # Procesar señales de entrada (1) después de las de salida
                for signal_info in señales_del_dia:
                    if signal_info['senal'] != 1:  # Solo procesar señales de entrada
                        continue
                    tipo_estrategia = estrategia_tipo_map.get(signal_info['estrategia'])
                    estrategia_id = estrategia_id_map.get(signal_info['estrategia'], signal_info['estrategia'])
                    if signal_info['senal'] == 1 and tipo_estrategia == 'forex' and estrategia_id in opened_buy_for_strategy:
                        # Ya se abrió un BUY para esta estrategia en esta misma vela; saltamos
                        continue
                    # Bloqueo por vela: si ya abrimos un BUY de cualquier estrategia FOREX en esta vela
                    if signal_info['senal'] == 1 and tipo_estrategia == 'forex' and opened_buy_any_forex:
                        try:
                            self.log(f"SKIP: Ya se abrió un BUY forex en esta vela, se omite {signal_info['estrategia']} en {idx}", color='yellow')
                        except Exception:
                            pass
                        continue
                    # Regla global: no permitir más de una BUY ACTIVA para la misma estrategia forex
                    if signal_info['senal'] == 1 and tipo_estrategia == 'forex':
                        try:
                            ya_activa = any(
                                (getattr(op, 'estado', 'ACTIVA') == 'ACTIVA') and 
                                (getattr(op, 'tipo', '') == 'BUY') and 
                                (getattr(op, 'estrategia', None) == estrategia_id)
                                for op in getattr(self.risk_manager, 'operaciones_activas', [])
                            )
                        except Exception:
                            ya_activa = False
                        if ya_activa:
                            # Ya existe una BUY activa para esta estrategia: saltamos apertura
                            try:
                                self.log(f"SKIP: BUY ya activa para estrategia {estrategia_id} en {idx}", color='yellow')
                            except Exception:
                                pass
                            continue

                    if self.risk_manager.puede_abrir_operacion():
                        atr_value = row.get('ATR')
                        if np.isnan(atr_value) or atr_value <= 0:
                            atr_value = (df_new['High'] - df_new['Low']).mean() * 0.1

                        # Solo procesar señales de entrada (1) aquí
                        operacion = self.risk_integration.procesar_senal(
                            senal=signal_info['senal'],
                            precio_actual=signal_info['precio'],
                            timestamp=idx,
                            atr_value=atr_value,
                            rr_ratio=2.0,
                            estrategia_nombre=estrategia_id
                        )

                        if operacion:
                            resultados.append({'timestamp': idx, 'operacion': operacion, 'tipo': 'APERTURA'})
                            self.log(f"APERTURA: {operacion} | Estrategia: {signal_info['estrategia']}", color='green')
                    
                        # Marcar que ya se abrió BUY para esta estrategia en esta vela
                        if signal_info['senal'] == 1 and tipo_estrategia == 'forex':
                            opened_buy_for_strategy.add(estrategia_id)
                            opened_buy_any_forex = True
                        # Refrescar dinero visible inmediatamente tras abrir
                        try:
                            self._actualizar_dinero_visible(row['Close'])
                        except Exception:
                            pass
                        # Refresco directo de Cash como respaldo
                        try:
                            cash_now = float(getattr(self.risk_manager, 'capital', self.dinero_ficticio))
                            self.label_cash.config(text=f"Dinero: {cash_now:,.2f}$")
                            try:
                                self.root.update_idletasks()
                            except Exception:
                                pass
                            # Log de verificación de cash y nocional
                            try:
                                if getattr(operacion, 'tipo', '') == 'BUY':
                                    self.log(f"Dinero tras apertura BUY: ${cash_now:,.2f} (Nocional: ${operacion.valor_posicion:,.2f})", color='cyan')
                                else:
                                    self.log(f"Dinero tras apertura {operacion.tipo}: ${cash_now:,.2f}", color='cyan')
                            except Exception:
                                pass
                        except Exception:
                            pass
                        # Actualizar dinero visible en tiempo real (capital - riesgo reservado + PnL flotante)
                        try:
                            self._actualizar_dinero_visible(row['Close'])
                        except Exception:
                            pass

                ops_activas = self.risk_manager.get_operaciones_activas_count()
                if ops_activas != operaciones_abiertas:
                    operaciones_abiertas = ops_activas
                    if operaciones_abiertas > 0:
                        den = '∞' if (isinstance(max_orders, int) and max_orders <= 0) else str(max_orders)
                        self.log(f"Operaciones activas: {operaciones_abiertas}/{den}", color='blue')

                # Actualizar dinero visible en tiempo real (capital - riesgo reservado + PnL flotante)
                try:
                    self._actualizar_dinero_visible(row['Close'])
                except Exception:
                    pass

            # Cerrar operaciones pendientes
            precio_cierre_final = df_new['Close'].iloc[-1] if not np.isnan(df_new['Close'].iloc[-1]) else df_new['Close'].dropna().iloc[-1]
            for op in self.risk_manager.operaciones_activas[:]:
                if op.estado == 'ACTIVA':
                    profit = op.cerrar(precio_cierre_final, df_new.index[-1])
                    if profit >= 0:
                        beneficios_totales += profit
                    else:
                        perdidas_totales += abs(profit)
                    self.risk_manager.capital += profit
                    self.risk_manager.beneficio_total += profit
                    if profit >= 0:
                        self.risk_manager.operaciones_ganadas += 1
                    else:
                        self.risk_manager.operaciones_perdidas += 1
                    color = 'green' if profit >= 0 else 'red'
                    self.log(f"CIERRE FINAL: {op} -> {op.resultado} | Profit: ${profit:+.2f}", color=color)
                    self.risk_manager.operaciones_cerradas.append(op)
                    self.risk_manager.operaciones_activas.remove(op)

            # Estadísticas finales
            self.log("="*60, color='white')
            self.log("ESTADÍSTICAS FINALES DEL RISK MANAGER", color='yellow')
            self.log("="*60, color='white')
            stats = self.risk_manager.get_estadisticas()
            capital_final = stats['capital_actual'] if not np.isnan(stats['capital_actual']) else capital_inicial
            beneficio_total = stats['beneficio_total'] if not np.isnan(stats['beneficio_total']) else 0
            self.log(f"Capital final: ${capital_final:,.2f}", color='cyan')
            self.log(f"Beneficio total: ${beneficio_total:,.2f}", color='cyan')
            self.log(f"Operaciones ganadas: {stats['operaciones_ganadas']}", color='green')
            self.log(f"Operaciones perdidas: {stats['operaciones_perdidas']}", color='red')
            total_ops = stats['operaciones_ganadas'] + stats['operaciones_perdidas']
            win_rate = (stats['operaciones_ganadas'] / total_ops * 100) if total_ops > 0 else 0
            self.log(f"Win Rate: {win_rate:.1f}%", color='white')
            max_ops = stats.get('max_operaciones', None)
            den_final = '∞' if (max_ops is None or (isinstance(max_ops, (int, float)) and max_ops <= 0)) else str(max_ops)
            self.log(f"Slots utilizados: {stats['operaciones_activas']}/{den_final}", color='blue')

            self.dinero_ficticio = capital_final
            self.beneficios = beneficios_totales
            self.perdidas = perdidas_totales
            self.actualizar_labels()

            self.log("="*60, color='white')
            self.log("RESUMEN EN INTERFAZ", color='yellow')
            self.log(f"Dinero total: ${capital_final:,.2f}", color='white')
            self.log(f"Beneficios acumulados: ${beneficios_totales:,.2f}", color='green')
            self.log(f"Pérdidas acumuladas: ${perdidas_totales:,.2f}", color='red')
            self.log("="*60, color='white')

        else:
            self.log("="*60, color='white')
            self.log("SIMULACIÓN DESHABILITADA - Solo se muestran detecciones", color='yellow')
            self.log("="*60, color='white')

        # Redibujar gráfico con las señales
        self.grafico_manager.dibujar_csv(df_new)
        self.df_actual = df_new

        if hasattr(self.grafico_manager, 'dibujar_operaciones'):
            operaciones_totales = self.risk_manager.operaciones_cerradas + [
                op for op in self.risk_manager.operaciones_activas if op.estado == 'ACTIVA'
            ]
            self.grafico_manager.dibujar_operaciones(operaciones_totales)
   
    def _calcular_dinero_visible(self, precio_actual: float) -> float:
        """Calcula el dinero visible (equity)"""
        try:
            capital = float(self.risk_manager.capital) if hasattr(self, 'risk_manager') and self.risk_manager is not None else float(self.dinero_ficticio)
        except Exception:
            capital = float(self.dinero_ficticio)

        total_valor_buys = 0.0
        total_pnl_sells = 0.0
        try:
            for op in getattr(self.risk_manager, 'operaciones_activas', []):
                if getattr(op, 'estado', 'ACTIVA') != 'ACTIVA':
                    continue
                if getattr(op, 'tipo', 'BUY') == 'BUY':
                    # Para BUY, calcular P&L flotante en lugar del valor nocional
                    pnl_flotante = (float(precio_actual) - float(op.precio_apertura)) * float(op.lote_size)
                    total_valor_buys += pnl_flotante
                else:
                    total_pnl_sells += (op.precio_apertura - float(precio_actual)) * float(op.lote_size)
        except Exception:
            pass

        try:
            if np.isnan(total_valor_buys) or np.isinf(total_valor_buys):
                total_valor_buys = 0.0
            if np.isnan(total_pnl_sells) or np.isinf(total_pnl_sells):
                total_pnl_sells = 0.0
        except Exception:
            pass

        # Cash ya está neto del valor nocional de BUY en RiskManager.capital
        # Equity = cash + valor de BUY abiertos + PnL de SELL abiertos
        equity = capital + total_valor_buys + total_pnl_sells
        return equity

    def _actualizar_dinero_visible(self, precio_actual: float):
        """Actualiza el dinero visible (equity) en tiempo real"""
        try:
            # Cash = capital actual (ya neto de compras)
            try:
                capital = float(self.risk_manager.capital)
            except Exception:
                capital = float(self.dinero_ficticio)

            total_valor_buys = 0.0
            total_pnl_sells = 0.0
            for op in getattr(self.risk_manager, 'operaciones_activas', []):
                if getattr(op, 'estado', 'ACTIVA') != 'ACTIVA':
                    continue
                if getattr(op, 'tipo', 'BUY') == 'BUY':
                    # Para BUY, calcular P&L flotante en lugar del valor nocional
                    pnl_flotante = (float(precio_actual) - float(op.precio_apertura)) * float(op.lote_size)
                    total_valor_buys += pnl_flotante
                else:
                    total_pnl_sells += (op.precio_apertura - float(precio_actual)) * float(op.lote_size)

            cash = capital
            equity = capital + total_valor_buys + total_pnl_sells

            # Proteger NaNs
            if np.isnan(cash) or np.isinf(cash):
                cash = capital
            if np.isnan(equity) or np.isinf(equity):
                equity = capital

            # Actualizar estado interno y labels
            self.dinero_ficticio = float(equity)
            self.label_dinero.config(text=f"Equidad: {equity:,.2f}$")
            self.label_cash.config(text=f"Dinero: {cash:,.2f}$")

            # Beneficios y pérdidas (cerradas) se actualizan donde corresponde
            self.root.update_idletasks()
        except Exception:
            # fallback silencioso
            pass

        
