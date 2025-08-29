# app/gui_main.py

import os
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np  # <-- AÑADIR ESTA IMPORTACIÓN
import pandas as pd  # <-- También es buena práctica añadir pandas

from .csv_manager import CSVManager
from .grafico_manager import GraficoManager
from .tooltip_zoom_pan import TooltipZoomPan
from .csv_loader_modal import CSVLoaderModal
from .patterns_modal import PatternsModal
from .strategies_modal import EstrategiasModal
from patterns.candlestickpatterns import CandlestickPatterns

# Imports externos
from strategies import ForexStrategies, CandleStrategies
from backtesting.backtester import ForexBacktester
from rl.rl_agent import RLTradingAgent
from strategies.risk_manager import RiskManager, RiskManagerIntegration, Operacion  # <-- Asegurar esta importación

class GUIPrincipal:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Bot - Forex Market")
        self.root.geometry("1900x950")
        self.root.configure(bg="#F0F0F0")
        self.root.attributes('-toolwindow', 1)

        # Set window icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
            icon = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(False, icon)
        except Exception as e:
            print(f"Error al cargar el icono: {e}")

        # Inicializaciones
        self.csv_manager = CSVManager(root)
        self.grafico_manager = GraficoManager(frame=None)
        self.tooltip_zoom_pan = None
        self.df_actual = None
        self.dinero_ficticio = 0
        self.beneficios = 0
        self.perdidas = 0
        self.rl_agent = None
        self.rl_signals = []
        self.compra_activa = None

        self.risk_manager = RiskManager(max_operaciones_activas=5)
        self.risk_integration = RiskManagerIntegration(self.risk_manager, None)

        # Frames principales
        self.frame_controls = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_controls.pack(fill="x", padx=20, pady=10)

        self.frame_grafico = tk.Frame(self.root, bg="#FFFFFF", relief="sunken", bd=1)
        self.frame_grafico.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.grafico_manager.frame = self.frame_grafico

        self.frame_log = tk.Frame(self.root, bg="#F8F8F8", relief="sunken", bd=1)
        self.frame_log.pack(fill="both", expand=False, padx=20, pady=(0, 20), ipady=120)
        
        # Estilo exclusivo para el scrollbar de logs (no afecta botones)
        self._logs_style = ttk.Style()
        self._logs_style.configure(
            "Logs.Vertical.TScrollbar",
            troughcolor="#EFEFEF",
            background="#B5B5B5",
            bordercolor="#EFEFEF",
            lightcolor="#EFEFEF",
            darkcolor="#EFEFEF",
            arrowcolor="#7A7A7A",
        )
        self._logs_style.map(
            "Logs.Vertical.TScrollbar",
            background=[("active", "#A0A0A0"), ("pressed", "#8C8C8C")],
        )

        # Área de logs con scrollbar vertical a la derecha
        self.text_log = tk.Text(
            self.frame_log,
            height=12,
            bg="black",
            fg="white",
            state="disabled",
            font=("Consolas", 10),
        )
        self.scrollbar_log_y = ttk.Scrollbar(
            self.frame_log,
            orient="vertical",
            style="Logs.Vertical.TScrollbar",
            command=self.text_log.yview,
        )
        self.text_log.configure(yscrollcommand=self.scrollbar_log_y.set)

        # Layout
        self.text_log.pack(side="left", fill="both", expand=True)
        self.scrollbar_log_y.pack(side="right", fill="y")

        # Contenedores de botones
        self.frame_left = tk.Frame(self.frame_controls, bg="#F0F0F0")
        self.frame_left.pack(side="left", anchor="w")

        self.frame_center = tk.Frame(self.frame_controls, bg="#F0F0F0")
        self.frame_center.pack(side="left", expand=True)

        self.frame_right = tk.Frame(self.frame_controls, bg="#F0F0F0")
        self.frame_right.pack(side="right", anchor="e")

        # ---------------- Botones CSV (izquierda) ----------------
        self.btn_cargar_csv = ttk.Button(self.frame_left, text="Cargar CSV", command=self.cargar_csv)
        self.btn_cargar_csv.pack(side="left", padx=5)

        self.btn_cargar_procesados = ttk.Button(
            self.frame_left, text="Cargar datos procesados", command=self.cargar_procesados
        )
        self.btn_cargar_procesados.pack(side="left", padx=5)

        self.btn_guardar_procesados = ttk.Button(
            self.frame_left, text="Guardar datos procesados", command=self.guardar_procesados
        )
        self.btn_guardar_procesados.pack(side="left", padx=5)

        self.btn_reset_zoom = ttk.Button(self.frame_left, text="Reset Zoom", command=self.reset_zoom)
        self.btn_reset_zoom.pack(side="left", padx=5)

        # ---------------- Dinero/beneficios/pérdidas (centro) ----------------
        self.label_dinero = tk.Label(
            self.frame_center, text=f"Dinero: ${self.dinero_ficticio:,.2f}", fg="black", bg="#F0F0F0"
        )
        self.label_dinero.pack(side="left", padx=10)

        self.label_beneficios = tk.Label(
            self.frame_center, text=f"Beneficios: ${self.beneficios:,.2f}", fg="green", bg="#F0F0F0"
        )
        self.label_beneficios.pack(side="left", padx=10)

        self.label_perdidas = tk.Label(
            self.frame_center, text=f"Pérdidas: ${self.perdidas:,.2f}", fg="red", bg="#F0F0F0"
        )
        self.label_perdidas.pack(side="left", padx=10)

        # ---------------- Botones derecha ----------------
        self.label_entry_dinero = tk.Label(self.frame_right, text="Dinero ficticio:", bg="#F0F0F0")
        self.label_entry_dinero.pack(side="left", padx=5)
        self.entry_dinero = ttk.Entry(self.frame_right, width=10)
        self.entry_dinero.pack(side="left", padx=5)
        self.btn_add_dinero = ttk.Button(self.frame_right, text="Añadir dinero", command=self.add_dinero)
        self.btn_add_dinero.pack(side="left", padx=5)

        self.btn_cargar_estrategias = ttk.Button(
            self.frame_right, text="Mostrar Estrategias", command=self.cargar_estrategias, state="disabled"
        )
        self.btn_cargar_estrategias.pack(side="left", padx=5)

        self.btn_aplicar_patrones = ttk.Button(
            self.frame_right, text="Mostrar Patrones", command=self.abrir_modal_patrones, state="disabled"
        )
        self.btn_aplicar_patrones.pack(side="left", padx=5)

        self.btn_backtesting = ttk.Button(
            self.frame_right, text="Iniciar Backtesting", command=self.abrir_modal_backtesting, state="disabled"
        )
        self.btn_backtesting.pack(side="left", padx=5)

        # ---------------- Botones RL ----------------
        self.btn_entrenar_rl = ttk.Button(
            self.frame_right, text="Entrenar RL", command=self.entrenar_rl, state="disabled"
        )
        self.btn_entrenar_rl.pack(side="left", padx=5)

        self.btn_cargar_rl = ttk.Button(
            self.frame_right, text="Cargar RL", command=self.cargar_rl, state="disabled"
        )
        self.btn_cargar_rl.pack(side="left", padx=5)

        self.btn_aplicar_rl = ttk.Button(
            self.frame_right, text="Aplicar Señales RL", command=self.aplicar_senales_rl, state="disabled"
        )
        self.btn_aplicar_rl.pack(side="left", padx=5)

    # ---------------- Funciones CSV ----------------
    def cargar_csv(self):
        df = self.csv_manager.cargar_csv()
        if df is not None:
            CSVLoaderModal(self.root, df, callback=self._on_csv_cargado)

    def _on_csv_cargado(self, df_seleccion):
        self.df_actual = df_seleccion
        self._dibujar_grafico(df_seleccion)

    def cargar_procesados(self):
        df = self.csv_manager.cargar_procesados()
        if df is not None:
            self.df_actual = df
            self._dibujar_grafico(df)
            # Habilitar botón de patrones tras cargar datos
            self.btn_aplicar_patrones.config(state="normal")
            self.btn_cargar_estrategias.config(state="normal")
            self.btn_backtesting.config(state="normal")
            self.btn_entrenar_rl.config(state="normal")
            self.btn_cargar_rl.config(state="normal")
            self.btn_aplicar_rl.config(state="normal")

    def guardar_procesados(self):
        self.csv_manager.df_cache = self.df_actual
        self.csv_manager.guardar_procesados()

    # ---------------- Funciones Dinero ----------------
    def add_dinero(self):
        try:
            cantidad = float(self.entry_dinero.get())
            self.dinero_ficticio += cantidad
            self.actualizar_labels()
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número válido")

    def actualizar_labels(self):
        self.label_dinero.config(text=f"Dinero: ${self.dinero_ficticio:,.2f}")
        self.label_beneficios.config(text=f"Beneficios: ${self.beneficios:,.2f}")
        self.label_perdidas.config(text=f"Pérdidas: ${self.perdidas:,.2f}")

    # ---------------- Funciones Estrategias ----------------
    def cargar_estrategias(self):
        if self.df_actual is None:
            messagebox.showwarning("Atención", "Cargue primero un CSV o datos procesados")
            return
    
        # Instanciar estrategias con el DataFrame actual
        self.strategies_fx = ForexStrategies(self.df_actual)
        self.strategies_candle = CandleStrategies(self.df_actual)

        # Obtener métodos públicos de cada clase
        fx_methods = [
            nombre for nombre in dir(ForexStrategies)
            if callable(getattr(ForexStrategies, nombre)) and not nombre.startswith("_")
        ]
        candle_methods = [
            nombre for nombre in dir(CandleStrategies)
            if callable(getattr(CandleStrategies, nombre)) and not nombre.startswith("_")
        ]

        # Abrir modal con las estrategias separadas
        EstrategiasModal(
            self.root, 
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

        # Configurar máximo de operaciones en el Risk Manager con el capital del entry
        self.risk_manager = RiskManager(max_operaciones_activas=max_orders, capital_inicial=capital_inicial)
        self.risk_integration = RiskManagerIntegration(self.risk_manager, None)
        self.risk_manager.reset()

        # Asegurar que las instancias existen
        if not hasattr(self, 'strategies_fx'):
            self.strategies_fx = ForexStrategies(self.df_actual)
        if not hasattr(self, 'strategies_candle'):
            self.strategies_candle = CandleStrategies(self.df_actual)

        df_new = self.df_actual.copy()

        # Primera pasada: aplicar estrategias y generar señales
        for nombre, params in seleccion.items():
            try:
                if params.get("tipo") == "forex":
                    # Estrategia Forex con gestión de riesgo
                    metodo = getattr(self.strategies_fx, nombre, None)
                    if not callable(metodo):
                        self.log(f"Estrategia Forex no encontrada: {nombre}", color='red')
                        continue
                    
                    risk_kwargs = {
                        'risk_per_trade': params.get('riesgo', 0.01),
                        'rr_ratio': params.get('rr', 2.0),
                    }
                    df_res = metodo(**risk_kwargs)
                    
                else:
                    # Estrategia Candle sin gestión de riesgo
                    metodo = getattr(self.strategies_candle, nombre, None)
                    if not callable(metodo):
                        self.log(f"Estrategia Candle no encontrada: {nombre}", color='red')
                        continue
                    df_res = metodo()

                if 'Signal' in df_res.columns:
                    col_name = f"{nombre}_Signal"
                    sig_series = df_res['Signal']
                    # Limitar a max_orders señales por estrategia
                    sig_indices = sig_series[sig_series != 0].index[:max_orders]
                    df_new[col_name] = 0
                    df_new.loc[sig_indices, col_name] = sig_series.loc[sig_indices]
                    
                    # Loguear detección de señales solo si está habilitado
                    if opciones["mostrar_deteccion"]:
                        for idx in sig_indices:
                            val = sig_series.loc[idx]
                            close_val = df_new.loc[idx, 'Close'] if 'Close' in df_new.columns else None
                            fecha_str = idx.strftime('%d/%m/%Y %H:%M') if hasattr(idx, 'strftime') else str(idx)
                            tipo = "Forex" if params.get("tipo") == "forex" else "Candle"
                            msg = f"DETECCIÓN: {nombre} ({tipo}) | Fecha: {fecha_str} | Señal: {val}"
                            if close_val is not None:
                                msg += f" | Precio: {close_val:.5f}"
                            self.log(msg, color='cyan' if tipo == "Forex" else 'yellow')
                        
            except Exception as e:
                self.log(f"Error aplicando estrategia {nombre}: {e}", color='red')

        # Segunda pasada: procesar el dataframe completo con el Risk Manager solo si está habilitado
        if opciones["mostrar_simulacion"]:
            self.log("="*60, color='white')
            self.log("INICIANDO SIMULACIÓN CON RISK MANAGER", color='yellow')
            self.log(f"Máximo de operaciones activas: {max_orders}", color='white')
            self.log(f"Capital inicial: ${capital_inicial:,.2f}", color='white')
            self.log("="*60, color='white')

            # Calcular ATR para el Risk Manager
            df_new['ATR'] = (df_new['High'] - df_new['Low']).rolling(14).mean()
            # Rellenar NaN values con un valor por defecto
            if df_new['ATR'].isna().all():
                df_new['ATR'] = (df_new['High'] - df_new['Low']).mean() * 0.1
            else:
                df_new['ATR'] = df_new['ATR'].fillna(df_new['ATR'].mean())
            
            # Variables para calcular beneficios y pérdidas totales
            beneficios_totales = 0
            perdidas_totales = 0
            
            resultados = []
            operaciones_abiertas = 0

            for idx, row in df_new.iterrows():
                # Saltar filas con valores NaN en precio
                if np.isnan(row['Close']):
                    continue
                    
                # Verificar cierre de operaciones existentes por SL/TP
                operaciones_cerradas = self.risk_manager.verificar_cierre_operaciones(
                    row['Close'], idx
                )
                
                # Registrar operaciones cerradas y acumular beneficios/pérdidas
                for op in operaciones_cerradas:
                    if op.tipo == 'BUY':
                        profit = (op.precio_cierre - op.precio_apertura) * op.lote_size
                    else:  # SELL
                        profit = (op.precio_apertura - op.precio_cierre) * op.lote_size
                    
                    # Validar profit
                    if np.isnan(profit) or np.isinf(profit):
                        profit = 0.0
                    
                    # Acumular en beneficios o pérdidas
                    if profit >= 0:
                        beneficios_totales += profit
                    else:
                        perdidas_totales += abs(profit)
                        
                    resultados.append({
                        'timestamp': idx,
                        'operacion': op,
                        'resultado': op.resultado,
                        'profit': profit
                    })
                    
                    color = 'green' if op.resultado == 'GANANCIA' else 'red'
                    self.log(f"CIERRE AUTOMÁTICO: {op} -> {op.resultado} | Profit: ${profit:+.2f}", color=color)

                # Procesar nuevas señales de todas las estrategias
                señales_del_dia = []
                for nombre in seleccion.keys():
                    col_name = f"{nombre}_Signal"
                    if col_name in df_new.columns and not np.isnan(df_new.loc[idx, col_name]) and df_new.loc[idx, col_name] != 0:
                        señales_del_dia.append({
                            'estrategia': nombre,
                            'senal': df_new.loc[idx, col_name],
                            'precio': row['Close']
                        })

                # Procesar cada señal del día
                for señal_info in señales_del_dia:
                    if self.risk_manager.puede_abrir_operacion():
                        # Obtener valor ATR válido
                        atr_value = row.get('ATR')
                        if np.isnan(atr_value) or atr_value <= 0:
                            atr_value = (df_new['High'] - df_new['Low']).mean() * 0.1
                        
                        operacion = self.risk_integration.procesar_senal(
                            senal=señal_info['senal'],
                            precio_actual=señal_info['precio'],
                            timestamp=idx,
                            atr_value=atr_value,
                            rr_ratio=2.0
                        )
                        
                        if operacion:
                            resultados.append({
                                'timestamp': idx,
                                'operacion': operacion,
                                'tipo': 'APERTURA'
                            })
                            
                            self.log(f"APERTURA: {operacion} | Estrategia: {señal_info['estrategia']}", color='green')
                            operaciones_abiertas += 1

                # Actualizar contador de operaciones activas en cada iteración
                ops_activas = self.risk_manager.get_operaciones_activas_count()
                if ops_activas != operaciones_abiertas:
                    operaciones_abiertas = ops_activas
                    if operaciones_abiertas > 0:
                        self.log(f"Operaciones activas: {operaciones_abiertas}/{max_orders}", color='blue')

            # Cerrar cualquier operación pendiente al final del periodo
            precio_cierre_final = df_new['Close'].iloc[-1]
            if np.isnan(precio_cierre_final):
                # Buscar último precio válido
                precios_validos = df_new['Close'].dropna()
                precio_cierre_final = precios_validos.iloc[-1] if not precios_validos.empty else None
            
            if precio_cierre_final is not None:
                for op in self.risk_manager.operaciones_activas[:]:  # Copia de la lista para iterar seguro
                    if op.estado == 'ACTIVA':
                        profit = op.cerrar(precio_cierre_final, df_new.index[-1])
                        
                        # Validar profit
                        if np.isnan(profit) or np.isinf(profit):
                            profit = 0.0
                        
                        # Acumular en beneficios o pérdidas
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
                        self.log(f"CIERRE FINAL: {op} | Profit: ${profit:+.2f}", color=color)
                        
                        # Mover a cerradas
                        self.risk_manager.operaciones_cerradas.append(op)
                        self.risk_manager.operaciones_activas.remove(op)


            # Mostrar estadísticas finales
            self.log("="*60, color='white')
            self.log("ESTADÍSTICAS FINALES DEL RISK MANAGER", color='yellow')
            self.log("="*60, color='white')
            
            stats = self.risk_manager.get_estadisticas()
            
            # Validar valores estadísticos
            capital_final = stats['capital_actual'] if not np.isnan(stats['capital_actual']) else capital_inicial
            beneficio_total = stats['beneficio_total'] if not np.isnan(stats['beneficio_total']) else 0
            
            self.log(f"Capital final: ${capital_final:,.2f}", color='cyan')
            self.log(f"Beneficio total: ${beneficio_total:,.2f}", color='cyan')
            self.log(f"Operaciones ganadas: {stats['operaciones_ganadas']}", color='green')
            self.log(f"Operaciones perdidas: {stats['operaciones_perdidas']}", color='red')
            
            total_ops = stats['operaciones_ganadas'] + stats['operaciones_perdidas']
            win_rate = (stats['operaciones_ganadas'] / total_ops * 100) if total_ops > 0 else 0
            self.log(f"Win Rate: {win_rate:.1f}%", color='white')
            self.log(f"Slots utilizados: {stats['operaciones_activas']}/{stats['max_operaciones']}", color='blue')

            # ACTUALIZAR LAS ETIQUETAS DE LA INTERFAZ
            self.dinero_ficticio = capital_final
            self.beneficios = beneficios_totales
            self.perdidas = perdidas_totales
            self.actualizar_labels()

            # Mostrar resumen en el log también
            self.log("="*60, color='white')
            self.log("RESUMEN EN INTERFAZ", color='yellow')
            self.log(f"Dinero total: ${capital_final:,.2f}", color='white')
            self.log(f"Beneficios acumulados: ${beneficios_totales:,.2f}", color='green')
            self.log(f"Pérdidas acumuladas: ${perdidas_totales:,.2f}", color='red')
            self.log("="*60, color='white')
        else:
            # Si la simulación está deshabilitada, solo mostrar mensaje
            self.log("="*60, color='white')
            self.log("SIMULACIÓN DESHABILITADA - Solo se muestran detecciones", color='yellow')
            self.log("="*60, color='white')

        # Redibujar gráfico con las señales
        self.grafico_manager.dibujar_csv(df_new)
        self.df_actual = df_new
        
        # Reinstalar TooltipZoomPan
        if self.tooltip_zoom_pan:
            try:
                self.tooltip_zoom_pan.cleanup()
            except Exception:
                pass
        if hasattr(self.grafico_manager, 'canvas') and hasattr(self.grafico_manager, 'grafico'):
            self.tooltip_zoom_pan = TooltipZoomPan(self.root, self.grafico_manager.canvas, self.grafico_manager.grafico)

        # Añadir visualización de operaciones en el gráfico si está disponible
        if hasattr(self.grafico_manager, 'dibujar_operaciones'):
            operaciones_totales = self.risk_manager.operaciones_cerradas + [
                op for op in self.risk_manager.operaciones_activas if op.estado == 'ACTIVA'
            ]
            self.grafico_manager.dibujar_operaciones(operaciones_totales)

    # ---------------- Backtesting (modal de selección) ----------------
    def abrir_modal_backtesting(self):
        if self.df_actual is None:
            messagebox.showwarning("Atención", "Cargue primero un CSV o datos procesados")
            return
        # Estrategias disponibles a partir de la clase ForexStrategies
        estrategias_disponibles = [
            nombre for nombre in dir(ForexStrategies)
            if callable(getattr(ForexStrategies, nombre)) and not nombre.startswith("_")
        ]
        # Reutilizamos el modal de patrones con sección de estrategias
        PatternsModal(
            self.root,
            self.df_actual,
            self.grafico_manager,
            self,
            callback=None,
            include_strategies=True,
            strategies_list=estrategias_disponibles,
            on_accept_backtesting=self._on_backtesting_selected,
        )

    def _on_backtesting_selected(self, patrones_sel, estrategias_sel):
        """Lanza el backtesting con estrategias seleccionadas y detecta (log) los patrones marcados.
        - Detecta patrones y los escribe en el log (no altera señales de backtest).
        - Ejecuta cada estrategia con ForexBacktester.backtest_with_events y loguea BUY/SELL.
        """
        if self.df_actual is None:
            return

        # 1) Detectar patrones seleccionados y loguearlos
        try:
            if patrones_sel:
                patterns = CandlestickPatterns(self.df_actual)
                for p in patrones_sel:
                    try:
                        serie = patterns.__getattribute__(p)()['Signal']
                        for idx, val in serie.items():
                            if val != 0:
                                row = self.df_actual.loc[idx]
                                fecha_str = idx.strftime('%d/%m/%Y') if hasattr(idx, 'strftime') else str(idx)
                                color = 'green' if row['Close'] > row['Open'] else ('red' if row['Close'] < row['Open'] else 'gray')
                                self.log(
                                    f"Patrón: {p} | Fecha: {fecha_str} | Open: {row['Open']:.5f} | Close: {row['Close']:.5f}",
                                    color=color,
                                )
                    except Exception as e:
                        self.log(f"Error detectando patrón {p}: {e}", color='red')
        except Exception as e:
            self.log(f"Error en detección de patrones: {e}", color='red')

        # 2) Ejecutar backtesting por estrategia y loguear BUY/SELL
        if not estrategias_sel:
            messagebox.showinfo("Backtesting", "No se seleccionaron estrategias")
            return
        backtester = ForexBacktester(self.df_actual)
        for nombre in estrategias_sel:
            try:
                metodo = getattr(backtester, nombre, None)
                if not callable(metodo):
                    self.log(f"Estrategia no válida: {nombre}", color='red')
                    continue
                df_sig = metodo()
                if 'Signal' not in df_sig.columns:
                    self.log(f"Estrategia {nombre} no generó columna 'Signal'", color='red')
                    continue
                balance_final, events = backtester.backtest_with_events(df_sig)
                self.log(f"[Backtesting] Estrategia: {nombre}", color='cyan')
                for ev in events:
                    t = ev['time']
                    fecha_str = t.strftime('%d/%m/%Y %H:%M') if hasattr(t, 'strftime') else str(t)
                    tipo = 'COMPRA' if ev['type'] == 'BUY' else 'VENTA'
                    color = 'green' if tipo == 'COMPRA' else 'red'
                    self.log(f"{fecha_str} | {tipo} a {ev['price']:.5f}", color=color)
                self.log(f"Balance final (simulado): ${balance_final:,.2f}", color='white')
            except Exception as e:
                self.log(f"Error en backtesting {nombre}: {e}", color='red')

    # ---------------- Funciones Patrones ----------------
    def abrir_modal_patrones(self):
        if self.df_actual is not None:
            # Pasar callback para reinstalar zoom/hover tras redibujar
            PatternsModal(self.root, self.df_actual, self.grafico_manager, self, callback=self._on_patrones_aplicados)
        else:
            messagebox.showwarning("Atención", "No hay datos cargados para aplicar patrones")

    # ---------------- Funciones RL ----------------
    def entrenar_rl(self):
        if self.df_actual is None:
            messagebox.showwarning("Atención", "Debe cargar un CSV primero")
            return
        self.rl_agent = RLTradingAgent(self.df_actual)
        self.rl_agent.entrenar(timesteps=50_000)
        messagebox.showinfo("RL", "Entrenamiento completado y modelo guardado")

    def cargar_rl(self):
        if self.df_actual is None:
            messagebox.showwarning("Atención", "Debe cargar un CSV primero")
            return
        self.rl_agent = RLTradingAgent(self.df_actual)
        cargado = self.rl_agent.cargar_modelo()
        if cargado:
            messagebox.showinfo("RL", "Modelo cargado correctamente")

    def aplicar_senales_rl(self):
        if self.rl_agent is None or self.df_actual is None:
            messagebox.showwarning("Atención", "Entrene o cargue primero el agente RL")
            return

        self.rl_signals = self.rl_agent.generar_senales()
        self.text_log.configure(state="normal")
        self.text_log.delete("1.0", "end")
        self.text_log.configure(state="disabled")
        self.compra_activa = None

        for i, row in self.df_actual.iterrows():
            mensaje = f"{i.strftime('%Y-%m-%d %H:%M')} | Close: {row['Close']:.5f}"
            signal = self.rl_signals[i] if i < len(self.rl_signals) else 0

            if signal == 1:
                self.compra_activa = (row["Close"], i)
                mensaje += f" | SEÑAL RL: COMPRA a {row['Close']:.5f}"
                self.log(mensaje, color="green")
            elif signal == 2 and self.compra_activa:
                precio_compra, fecha_compra = self.compra_activa
                ganancia = row["Close"] - precio_compra
                if ganancia >= 0:
                    color = "green"
                    msg_gan = f"Ganancia: +{ganancia:.5f}"
                else:
                    color = "red"
                    msg_gan = f"Pérdida: {ganancia:.5f}"
                mensaje += f" | SEÑAL RL: VENTA a {row['Close']:.5f} | {msg_gan}"
                self.log(mensaje, color=color)
                self.compra_activa = None
            else:
                self.log(mensaje, color="white")

        if self.grafico_manager:
            self.grafico_manager.dibujar_senales_rl(self.rl_signals)

    # ---------------- Funciones Gráficos ----------------
    def _dibujar_grafico(self, df):
        self.grafico_manager.dibujar_csv(df)
        self.tooltip_zoom_pan = TooltipZoomPan(self.root, self.grafico_manager.canvas, self.grafico_manager.grafico)

    def reset_zoom(self):
        if self.tooltip_zoom_pan:
            self.tooltip_zoom_pan.reset_zoom()

    def limpiar_grafico(self):
        self.df_actual = None
        if self.tooltip_zoom_pan:
            self.tooltip_zoom_pan.cleanup()
        self.tooltip_zoom_pan = None
        if hasattr(self.grafico_manager, "limpiar"):
            self.grafico_manager.limpiar()
        if hasattr(self.grafico_manager, "canvas") and self.grafico_manager.canvas:
            self.grafico_manager.canvas.get_tk_widget().pack_forget()
            self.grafico_manager.canvas = None

    # ---------------- Función Log ----------------
    def log(self, mensaje, color="white"):
        self.text_log.configure(state="normal")
        self.text_log.insert("end", mensaje + "\n", color)
        self.text_log.tag_configure(color, foreground=color)
        self.text_log.see("end")
        self.text_log.configure(state="disabled")

    # ---------------- Función callback para patrones ----------------
    def _on_patrones_aplicados(self, df_actualizado):
        """Callback desde PatternsModal tras aplicar y dibujar patrones.
        Reasigna df_actual y reinstala los handlers de zoom/hover sobre el nuevo canvas/figura.
        """
        self.df_actual = df_actualizado
        # Si existía un gestor previo de zoom/hover, desconectarlo limpiamente
        if self.tooltip_zoom_pan:
            try:
                self.tooltip_zoom_pan.cleanup()
            except Exception:
                pass
        # Instalar nuevo gestor con el canvas/figura recién creados
        if hasattr(self.grafico_manager, "canvas") and hasattr(self.grafico_manager, "grafico"):
            self.tooltip_zoom_pan = TooltipZoomPan(
                self.root,
                self.grafico_manager.canvas,
                self.grafico_manager.grafico,
            )

    # ---------------- Run ----------------
    def run(self):
        self.root.mainloop()
