# app/gui_main.py

import os
import time
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np  
import pandas as pd  
import asyncio
import importlib.util
from datetime import datetime
import sys
from stable_baselines3 import PPO

from .csv_manager import CSVManager
from .grafico_manager import GraficoManager
from .tooltip_zoom_pan import TooltipZoomPan
from .csv_loader_modal import CSVLoaderModal
from .patterns_modal import PatternsModal
from .strategies_modal import EstrategiasModal
from .ai_training_modal import AITrainingModal
from .rl_training_modal import RLTrainingModal
from .csv_to_pkl_modal import CSVToPKLModal
from .ai_trainer import AITrainer
from .processed_loader_modal import ProcessedDataModal

from patterns.candlestickpatterns import CandlestickPatterns

# Imports externos
from strategies import ForexStrategies, CandleStrategies
from backtesting.backtester import ForexBacktester
from rl.rl_agent import RLTradingAgent
from strategies.risk_manager import RiskManager, RiskManagerIntegration, Operacion  

class GUIPrincipal:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Bot - Forex Market")
        self.root.geometry("1500x950")
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
        # Soporte multi-posición para RL
        self.posiciones_activas = []  # lista de dicts {'precio','fecha','indice'}
        self.operaciones = []  # tracking de operaciones RL (aperturas y cierres)
        self._pattern_signals = None  # Serie con confirmación de patrones (+1/-1/0)

        self.risk_manager = RiskManager(max_operaciones_activas=5)
        self.risk_integration = RiskManagerIntegration(self.risk_manager, None)

        # Frames principales
        self.frame_controls = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_controls.pack(fill="x", padx=20, pady=10)

        # Contenedor central: gráfico (izquierda) + panel Telegram (derecha)
        self.frame_middle = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_middle.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.frame_grafico = tk.Frame(self.frame_middle, bg="#FFFFFF", relief="sunken", bd=1)
        self.frame_grafico.pack(side="left", fill="both", expand=True)
        self.grafico_manager.frame = self.frame_grafico

        # Header del área de gráfico con botón Reset Zoom en la esquina superior derecha
        self.frame_grafico_header = tk.Frame(self.frame_grafico, bg="#FFFFFF")
        self.frame_grafico_header.pack(fill="x", padx=8, pady=(6, 0))
        self.btn_reset_zoom = ttk.Button(self.frame_grafico_header, text="Reset Zoom", command=self.reset_zoom)
        self.btn_reset_zoom.pack(side="right")

        # Panel lateral de Telegram
        self.frame_telegram_panel = tk.Frame(self.frame_middle, bg="#F8F8F8", relief="sunken", bd=1, width=360)
        self.frame_telegram_panel.pack(side="right", fill="y")
        self.frame_telegram_panel.pack_propagate(False)

        # Cabecera panel telegram
        tk.Label(self.frame_telegram_panel, text="Telegram", bg="#F8F8F8", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10,5))
        
        # Estado de conexión
        self.telegram_status_frame = tk.Frame(self.frame_telegram_panel, bg="#F8F8F8")
        self.telegram_status_frame.pack(fill="x", padx=10, pady=(0, 5))
        tk.Label(self.telegram_status_frame, text="Estado:", bg="#F8F8F8").pack(side="left")
        self.lbl_telegram_status = tk.Label(self.telegram_status_frame, text="Desconectado", fg="red", bg="#F8F8F8")
        self.lbl_telegram_status.pack(side="left", padx=5)
        
        self.btn_telegram_connect = ttk.Button(self.frame_telegram_panel, text="Conectar y crear canal", command=self.conectar_telegram, state="disabled")
        self.btn_telegram_connect.pack(fill="x", padx=10)

        # Link de invitación + copiar
        link_frame = tk.Frame(self.frame_telegram_panel, bg="#F8F8F8")
        link_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(link_frame, text="Enlace de invitación:", bg="#F8F8F8").pack(anchor="w")
        self.var_invite = tk.StringVar(value="(sin conectar)")
        self.lbl_invite = tk.Label(link_frame, textvariable=self.var_invite, bg="#F8F8F8", fg="#0066CC", wraplength=320, justify="left")
        self.lbl_invite.pack(fill="x")
        self.btn_copy_link = ttk.Button(link_frame, text="Copiar enlace", command=self._copy_invite_link, state="disabled")
        self.btn_copy_link.pack(anchor="e", pady=(4, 0))

        # Área de mensajes tipo canal
        tk.Label(self.frame_telegram_panel, text="Mensajes del canal:", bg="#F8F8F8").pack(anchor="w", padx=10, pady=(10,0))
        self.text_telegram = tk.Text(self.frame_telegram_panel, height=10, bg="black", fg="white", state="disabled", font=("Consolas", 10))
        self.scroll_telegram = ttk.Scrollbar(self.frame_telegram_panel, orient="vertical", style="Logs.Vertical.TScrollbar", command=self.text_telegram.yview)
        self.text_telegram.configure(yscrollcommand=self.scroll_telegram.set)
        # Layout del área de mensajes
        msg_frame = tk.Frame(self.frame_telegram_panel, bg="#F8F8F8")
        msg_frame.pack(fill="both", expand=True, padx=10, pady=(5,10))
        self.text_telegram.pack(in_=msg_frame, side="left", fill="both", expand=True)
        self.scroll_telegram.pack(in_=msg_frame, side="right", fill="y")

        self.frame_log = tk.Frame(self.root, bg="#F8F8F8", relief="sunken", bd=1)
        self.frame_log.pack(fill="both", expand=False, padx=20, pady=(0, 20), ipady=120)
        # Altura fija del área de log
        self.frame_log.configure(height=50)
        self.frame_log.pack_propagate(False)
        # Flag: altura del log ya bloqueada
        self._log_height_locked = True

        # Header del área de logs con botón en la esquina superior derecha
        self.frame_log_header = tk.Frame(self.frame_log, bg="#F8F8F8")
        self.frame_log_header.pack(fill="x", padx=8, pady=(6, 0))
        self.btn_clear_log = ttk.Button(self.frame_log_header, text="Limpiar Log", command=self._limpiar_log)
        self.btn_clear_log.pack(side="right")

        # Barra de progreso compacta en el header (a la izquierda de "Limpiar Log")
        self.progress_var = tk.IntVar(value=0)
        self.header_progress_frame = tk.Frame(self.frame_log_header, bg="#F8F8F8")
        # Empaquetamos a la derecha para quedar a la izquierda del botón (que también está a la derecha)
        # Inicialmente NO visible; se mostrará sólo durante entrenamiento IA
        # Widgets internos: Progressbar + etiqueta superpuesta con porcentaje
        self.header_progressbar = ttk.Progressbar(
            self.header_progress_frame,
            orient='horizontal',
            mode='determinate',
            maximum=100,
            variable=self.progress_var,
            length=220,
        )
        self.header_progressbar.pack(side="left", padx=(0, 6))
        # Etiqueta sobre la barra para mostrar el %
        self.header_progress_label = tk.Label(
            self.header_progress_frame,
            text="0%",
            bg=self.frame_log_header.cget("bg"),  # mismo fondo que el header, evita caja blanca
            fg="black",
            bd=0,
            highlightthickness=0,
        )
        # Usamos place para centrar el texto encima de la barra
        def _place_header_progress_text():
            try:
                x = self.header_progressbar.winfo_x()
                y = self.header_progressbar.winfo_y()
                w = self.header_progressbar.winfo_width()
                h = self.header_progressbar.winfo_height()
                # Centrar el texto en la barra
                self.header_progress_label.place(x=x + w//2, y=y + h//2, anchor="center")
            except Exception:
                pass
        # Ajustar posición tras dibujar
        self.header_progressbar.bind("<Configure>", lambda e: _place_header_progress_text())
        # No mostrar aún
        # self.header_progress_frame.pack(side="right", padx=(0, 8))  # se packea dinámicamente en _show_progress_bar

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

        # (Obsoleto) Barra de progreso inferior: dejamos la infra pero oculta por defecto
        self.frame_progress = tk.Frame(self.root, bg="#F0F0F0")
        # Mantener variables de info por compatibilidad (no visibles)
        self.progress_info_var = tk.StringVar(value="0/0 (0%) ETA --:--")
        self.progress_info_label = ttk.Label(self.frame_progress, textvariable=self.progress_info_var, background="#F0F0F0")
        self.btn_stop_training = ttk.Button(self.frame_progress, text="Detener", command=lambda: self._stop_training(), state="disabled")
        # No empaquetamos este frame para mantenerlo oculto

        # Contenedores de botones
        self.frame_left = tk.Frame(self.frame_controls, bg="#F0F0F0")
        self.frame_left.pack(side="left", anchor="w")

        self.frame_center = tk.Frame(self.frame_controls, bg="#F0F0F0")
        self.frame_center.pack(side="left", expand=True)

        self.frame_right = tk.Frame(self.frame_controls, bg="#F0F0F0")
        self.frame_right.pack(side="right", anchor="e")

        # ---------------- Menú desplegable Procesar datos (agrupa botones de la izquierda) ----------------
        self.btn_procesar_datos = ttk.Menubutton(self.frame_left, text="Procesar datos")
        self.btn_procesar_datos.pack(side="left", padx=5)
        self.menu_procesar_datos = tk.Menu(self.btn_procesar_datos, tearoff=0)
        self.btn_procesar_datos.configure(menu=self.menu_procesar_datos)

        # Entradas del menú
        self.menu_procesar_datos.add_command(label="Cargar CSV", command=self.cargar_csv)
        self.menu_procesar_datos.add_command(label="Cargar datos procesados", command=self.cargar_procesados)
        self.menu_procesar_datos.add_separator()
        self.menu_procesar_datos.add_command(label="Guardar datos procesados", command=self.guardar_procesados)
        self.menu_procesar_datos.add_command(label="Procesar CSV a PKL", command=self.abrir_modal_csv_a_pkl)

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
        # Entry y botón para cargar dinero ficticio (NO dentro de Opciones)
        self.entry_dinero = ttk.Entry(self.frame_right, width=12)
        self.entry_dinero.pack(side="left", padx=5)
        self.btn_add_dinero = ttk.Button(self.frame_right, text="Añadir", command=self.add_dinero)
        self.btn_add_dinero.pack(side="left", padx=5)

        # ---------------- Menú desplegable Opciones ----------------
        # Usar ttk.Menubutton para que coincida el estilo con los demás botones
        self.btn_opciones = ttk.Menubutton(self.frame_right, text="Opciones", state="disabled")
        self.btn_opciones.pack(side="left", padx=5)
        self.menu_opciones = tk.Menu(self.btn_opciones, tearoff=0)
        self.btn_opciones.configure(menu=self.menu_opciones)

        # Etiquetas para controlar el estado por nombre
        self._menu_label_estrategias = "Mostrar Estrategias"
        self._menu_label_patrones = "Aplicar Patrones"
        self._menu_label_backtesting = "Iniciar Backtesting"
        self._menu_label_entrenar_ia = "Entrenar IA"
        self._menu_label_detener_ia = "Detener IA"

        # Entradas del menú Opciones (inicialmente deshabilitadas)
        self.menu_opciones.add_command(
            label=self._menu_label_estrategias, command=self.cargar_estrategias, state="disabled"
        )
        self.menu_opciones.add_command(
            label=self._menu_label_patrones, command=self.abrir_modal_patrones, state="disabled"
        )
        self.menu_opciones.add_command(
            label=self._menu_label_backtesting, command=self.abrir_modal_backtesting, state="disabled"
        )
        self.menu_opciones.add_separator()
        self.menu_opciones.add_command(
            label=self._menu_label_entrenar_ia, command=self.entrenar_ia, state="disabled"
        )
        self.menu_opciones.add_command(
            label=self._menu_label_detener_ia, command=self.detener_entrenamiento_ia, state="disabled"
        )

        # ---------------- Menú desplegable Modelo IA (agrupa RL) ----------------
        self._ia_label_crear_rl = "Crear Modelo RL"
        self._ia_label_cargar_rl = "Cargar Modelo RL"
        self._ia_label_aplicar_rl = "Aplicar Señales RL"

        self.btn_modelo_ia = ttk.Menubutton(self.frame_right, text="Modelo IA", state="disabled")
        self.btn_modelo_ia.pack(side="left", padx=5)
        self.menu_modelo_ia = tk.Menu(self.btn_modelo_ia, tearoff=0)
        self.btn_modelo_ia.configure(menu=self.menu_modelo_ia)
        self.menu_modelo_ia.add_command(label=self._ia_label_crear_rl, command=self.entrenar_rl, state="disabled")
        self.menu_modelo_ia.add_command(label=self._ia_label_cargar_rl, command=self.cargar_rl, state="disabled")
        self.menu_modelo_ia.add_command(label=self._ia_label_aplicar_rl, command=self.aplicar_senales_rl, state="disabled")

        # ---------------- Botones TELEGRAM ----------------
        self.btn_telegram = ttk.Button(
            self.frame_right, text="Telegram", command=self.abrir_modal_telegram, state="disabled"
        )
        self.btn_telegram.pack(side="left", padx=5)

        # Botón Reiniciar (reinicia completamente la app como si se relanzara `python -m app.main`)
        self.btn_reiniciar = ttk.Button(
            self.frame_right, text="Reiniciar", command=self.reiniciar_app
        )
        self.btn_reiniciar.pack(side="left", padx=5)

    # Fin de __init__

    def _on_csv_cargado(self, df_seleccion):
        self.df_actual = df_seleccion
        self._dibujar_grafico(df_seleccion)
        # Tras dibujar el primer gráfico, fijar la altura actual del área de logs
        self._fix_log_height_once()
        # Tras seleccionar CSV, actualizar estados por si ya hay dinero ficticio
        try:
            self._update_btn_aplicar_patrones()
            self._update_btn_cargar_estrategias()
        except Exception:
            pass

    def _fix_log_height_once(self):
        """Fija la altura del área de logs a la altura actual (una sola vez)
        para que se mantenga constante el resto de la sesión.
        """
        try:
            if self._log_height_locked:
                return
            # Asegurar que los tamaños actuales están calculados
            self.root.update_idletasks()
            current_h = self.frame_log.winfo_height()
            # Si por cualquier motivo no hay altura aún, usar un valor razonable
            if not current_h or current_h <= 0:
                current_h = 240
            # Fijar altura y evitar que el contenido la cambie
            self.frame_log.configure(height=current_h)
            self.frame_log.pack_propagate(False)
            self._log_height_locked = True
        except Exception:
            pass

    def cargar_procesados(self):
        """Abre el nuevo modal para cargar datos procesados (Parquet/PKL) con opciones de rango."""
        try:
            def _on_loaded(df):
                try:
                    # Reutilizamos la misma ruta de pintado y habilitación de botones
                    self._on_csv_cargado(df)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo cargar los datos: {e}")

            ProcessedDataModal(self.root, on_loaded_df=_on_loaded)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el modal: {e}")

    def guardar_procesados(self):
        self.csv_manager.df_cache = self.df_actual
        self.csv_manager.guardar_procesados()

    def abrir_modal_csv_a_pkl(self):
        """Abre el modal para convertir un CSV en un archivo PKL."""
        try:
            CSVToPKLModal(self.root)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el modal: {e}")

    # ---------------- Funciones Dinero ----------------
    def add_dinero(self):
        try:
            cantidad = float(self.entry_dinero.get())
            self.dinero_ficticio += cantidad
            self.actualizar_labels()
            self._update_btn_aplicar_patrones()
            self._update_btn_cargar_estrategias()
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

        # Obtener métodos públicos de patrones de velas
        pattern_methods = [
            nombre for nombre in dir(CandlestickPatterns)
            if callable(getattr(CandlestickPatterns, nombre)) and not nombre.startswith("_")
        ]

        # Abrir modal con las estrategias y patrones
        EstrategiasModal(
            self.root,
            estrategias_fx=sorted(fx_methods),
            estrategias_candle=sorted(candle_methods),
            callback=self._on_estrategias_seleccionadas,
            patrones_list=sorted(pattern_methods),
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
        self.risk_integration = RiskManagerIntegration(self.risk_manager, None)
        self.risk_manager.reset()

        # Asegurar que las instancias existen
        if not hasattr(self, 'strategies_fx'):
            self.strategies_fx = ForexStrategies(self.df_actual)
        if not hasattr(self, 'strategies_candle'):
            self.strategies_candle = CandleStrategies(self.df_actual)

        df_new = self.df_actual.copy()
        patterns_instance = None

        for nombre, params in seleccion.items():
            try:
                tipo_sel = params.get("tipo")
                if tipo_sel == "forex":
                    metodo = getattr(self.strategies_fx, nombre, None)
                    if not callable(metodo):
                        self.log(f"Estrategia Forex no encontrada: {nombre}", color='red')
                        continue

                    risk_kwargs = {
                        'risk_per_trade': params.get('riesgo', 0.01),
                        'rr_ratio': params.get('rr', 2.0),
                    }

                    # Argumentos por defecto
                    if nombre == "carry_trade_strategy":
                        if 'rate_diff' not in params:
                            if 'InterestRate_Base' in df_new.columns and 'InterestRate_Quote' in df_new.columns:
                                params['rate_diff'] = (df_new['InterestRate_Base'] - df_new['InterestRate_Quote']) / 100
                            else:
                                params['rate_diff'] = pd.Series(0, index=df_new.index)
                        df_res = metodo(rate_diff=params['rate_diff'], **risk_kwargs)

                    elif nombre in {"hedging_overlay", "martingale_overlay"}:
                        if 'base_signal' not in params:
                            if 'TrendSignal' in df_new.columns:
                                params['base_signal'] = df_new['TrendSignal'].fillna(0)
                            else:
                                params['base_signal'] = pd.Series(0, index=df_new.index)
                        df_res = metodo(base_signal=params['base_signal'], **risk_kwargs)

                    else:
                        df_res = metodo(**risk_kwargs)

                elif tipo_sel == "candle":
                    metodo = getattr(self.strategies_candle, nombre, None)
                    if not callable(metodo):
                        self.log(f"Estrategia Candle no encontrada: {nombre}", color='red')
                        continue
                    df_res = metodo()

                elif tipo_sel == "pattern":
                    if patterns_instance is None:
                        patterns_instance = CandlestickPatterns(self.df_actual)
                    metodo = getattr(patterns_instance, nombre, None)
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
                    profit = (op.precio_cierre - op.precio_apertura) * op.lote_size if op.tipo == 'BUY' else (op.precio_apertura - op.precio_cierre) * op.lote_size
                    if np.isnan(profit) or np.isinf(profit):
                        profit = 0.0
                    if profit >= 0:
                        beneficios_totales += profit
                    else:
                        perdidas_totales += abs(profit)
                    resultados.append({'timestamp': idx, 'operacion': op, 'resultado': op.resultado, 'profit': profit})
                    color = 'green' if op.resultado == 'GANANCIA' else 'red'
                    self.log(f"CIERRE AUTOMÁTICO: {op} -> {op.resultado} | Profit: ${profit:+.2f}", color=color)

                señales_del_dia = []
                for nombre in seleccion.keys():
                    col_name = f"{nombre}_Signal"
                    if col_name in df_new.columns and not np.isnan(df_new.loc[idx, col_name]) and df_new.loc[idx, col_name] != 0:
                        señales_del_dia.append({'estrategia': nombre, 'senal': df_new.loc[idx, col_name], 'precio': row['Close']})

                for señal_info in señales_del_dia:
                    if self.risk_manager.puede_abrir_operacion():
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
                            resultados.append({'timestamp': idx, 'operacion': operacion, 'tipo': 'APERTURA'})
                            self.log(f"APERTURA: {operacion} | Estrategia: {señal_info['estrategia']}", color='green')
                            operaciones_abiertas += 1

                ops_activas = self.risk_manager.get_operaciones_activas_count()
                if ops_activas != operaciones_abiertas:
                    operaciones_abiertas = ops_activas
                    if operaciones_abiertas > 0:
                        den = '∞' if (isinstance(max_orders, int) and max_orders <= 0) else str(max_orders)
                        self.log(f"Operaciones activas: {operaciones_abiertas}/{den}", color='blue')

            # Cerrar operaciones pendientes
            precio_cierre_final = df_new['Close'].iloc[-1] if not np.isnan(df_new['Close'].iloc[-1]) else df_new['Close'].dropna().iloc[-1]
            for op in self.risk_manager.operaciones_activas[:]:
                if op.estado == 'ACTIVA':
                    profit = op.cerrar(precio_cierre_final, df_new.index[-1])
                    if np.isnan(profit) or np.isinf(profit):
                        profit = 0.0
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

        if self.tooltip_zoom_pan:
            try:
                self.tooltip_zoom_pan.cleanup()
            except Exception:
                pass
        if hasattr(self.grafico_manager, 'canvas') and hasattr(self.grafico_manager, 'grafico'):
            self.tooltip_zoom_pan = TooltipZoomPan(self.root, self.grafico_manager.canvas, self.grafico_manager.grafico)

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
        - Actualiza el dinero, beneficios y pérdidas en la interfaz.
        """
        if self.df_actual is None:
            return

        # Inicializar contadores para el resumen
        balance_inicial = self.dinero_ficticio if hasattr(self, 'dinero_ficticio') and self.dinero_ficticio > 0 else 10000
        beneficios_totales = self.beneficios if hasattr(self, 'beneficios') else 0
        perdidas_totales = self.perdidas if hasattr(self, 'perdidas') else 0

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
                    
                # Realizar backtesting
                balance_final, events = backtester.backtest_with_events(df_sig)
                
                # Calcular beneficios y pérdidas de esta estrategia
                beneficio_estrategia = balance_final - balance_inicial
                if beneficio_estrategia >= 0:
                    beneficios_totales += beneficio_estrategia
                else:
                    perdidas_totales += abs(beneficio_estrategia)
                
                # Mostrar resultados en el log
                self.log(f"\n[Backtesting] Estrategia: {nombre}", color='cyan')
                self.log(f"Balance inicial: ${balance_inicial:,.2f}")
                
                for ev in events:
                    t = ev['time']
                    fecha_str = t.strftime('%d/%m/%Y %H:%M') if hasattr(t, 'strftime') else str(t)
                    tipo = 'COMPRA' if ev['type'] == 'BUY' else 'VENTA'
                    color = 'green' if tipo == 'COMPRA' else 'red'
                    self.log(f"{fecha_str} | {tipo} a {ev['price']:.5f}", color=color)
                
                self.log(f"Balance final (simulado): ${balance_final:,.2f}", color='white')
                self.log(f"Beneficio/Perdida: ${(balance_final - balance_inicial):+,.2f}", 
                        color='green' if (balance_final - balance_inicial) >= 0 else 'red')
                
                # Actualizar el balance para la próxima estrategia
                balance_inicial = balance_final
                
            except Exception as e:
                self.log(f"Error en backtesting {nombre}: {e}", color='red')
        
        # Actualizar la interfaz con los totales
        self.dinero_ficticio = balance_final
        self.beneficios = beneficios_totales
        self.perdidas = perdidas_totales
        self.actualizar_labels()
        
        # Mostrar resumen final
        self.log("\n" + "="*60, color='white')
        self.log("RESUMEN FINAL DEL BACKTESTING", color='yellow')
        self.log("="*60, color='white')
        self.log(f"Dinero total: ${balance_final:,.2f}", color='white')
        self.log(f"Beneficios totales: ${beneficios_totales:,.2f}", color='green')
        self.log(f"Pérdidas totales: ${perdidas_totales:,.2f}", color='red')
        self.log("="*60, color='white')

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
        # Mostrar modal de entrenamiento
        def _start_training(iterations: int, on_complete, on_progress=None):
            try:
                # Logger thread-safe hacia el log inferior
                def _log_ts(msg: str, color='white'):
                    try:
                        self.root.after(0, lambda: self.log(str(msg), color=color))
                    except Exception:
                        pass
                self.rl_agent = RLTradingAgent(
                    self.df_actual,
                    estrategias_fx={},
                    estrategias_candle=[],
                    patrones=[],
                    log_fn=lambda m: _log_ts(m, 'cyan')
                )
                self.rl_agent.entrenar(timesteps=iterations, progress_cb=on_progress)
                # Avisar al modal que el entrenamiento terminó OK
                on_complete(success=True)
                # Aviso visual de fin de entrenamiento
                try:
                    self.root.after(0, lambda: messagebox.showinfo("IA", "Entrenamiento completado y modelo guardado"))
                except Exception:
                    pass
                # Tras finalizar el entrenamiento, aplicar automáticamente las señales RL
                # para calcular y reflejar Beneficios/Pérdidas en la barra superior.
                try:
                    self.root.after(0, lambda: (
                        self.log("Aplicando señales RL post-entrenamiento...", color='yellow'),
                        self.aplicar_senales_rl()
                    ))
                except Exception:
                    pass
            except Exception as e:
                on_complete(success=False, error_msg=str(e))

        RLTrainingModal(self.root, start_training_callback=_start_training)

    def cargar_rl(self):
        if self.df_actual is None:
            messagebox.showwarning("Atención", "Debe cargar un CSV primero")
            return
        self.rl_agent = RLTradingAgent(
            self.df_actual,
            estrategias_fx={},
            estrategias_candle=[],
            patrones=[]
        )
        cargado = self.rl_agent.cargar_modelo()
        if cargado:
            messagebox.showinfo("RL", "Modelo cargado correctamente")

    def aplicar_senales_rl(self):
        """Aplica señales de compra/venta generadas por el agente RL"""
        # Validación más robusta
        if self.rl_agent is None:
            messagebox.showwarning("Atención", "No hay agente RL cargado. Entrene o cargue primero el agente.")
            return
        
        if self.df_actual is None or self.df_actual.empty:
            messagebox.showwarning("Atención", "No hay datos para procesar. Cargue primero los datos.")
            return

        try:
            # Generar señales
            self.rl_signals = self.rl_agent.generar_senales()
            
            # Validar que las señales coincidan con los datos
            if len(self.rl_signals) != len(self.df_actual):
                messagebox.showwarning("Advertencia", 
                                     f"El número de señales ({len(self.rl_signals)}) no coincide con los datos ({len(self.df_actual)}). "
                                     "Se truncará o completará con ceros.")
                # Ajustar señales si es necesario
                if len(self.rl_signals) > len(self.df_actual):
                    self.rl_signals = self.rl_signals[:len(self.df_actual)]
                else:
                    self.rl_signals = np.pad(self.rl_signals, 
                                           (0, len(self.df_actual) - len(self.rl_signals)), 
                                           'constant')

            # Precalcular confirmación por patrones de velas
            try:
                patterns = CandlestickPatterns(self.df_actual)
                df_patterns = patterns.combined_signal_optimized()
                # Alinear por índice
                self._pattern_signals = df_patterns['Final_Signal'].reindex(self.df_actual.index).fillna(0)
            except Exception:
                self._pattern_signals = None

            # Limpiar interfaz/estado
            self._limpiar_log()
            self.posiciones_activas = []
            self.operaciones = []  # Para tracking de operaciones

            # Procesar cada señal
            for idx, (timestamp, row) in enumerate(self.df_actual.iterrows()):
                self._procesar_senal_rl(idx, timestamp, row)

            # Actualizar gráfico
            if self.grafico_manager:
                self.grafico_manager.dibujar_senales_rl(self.rl_signals)
                
            # Mostrar resumen
            self._mostrar_resumen_operaciones_rl()

        except Exception as e:
            messagebox.showerror("Error", f"Error al aplicar señales RL: {str(e)}")
            self.log(f"Error: {str(e)}", color="red")

    def _limpiar_log(self):
        """Limpia el área de log"""
        self.text_log.configure(state="normal")
        self.text_log.delete("1.0", "end")
        self.text_log.configure(state="disabled")

    def _procesar_senal_rl(self, idx, timestamp, row):
        """Procesa una señal individual RL"""
        signal = self.rl_signals[idx] if idx < len(self.rl_signals) else 0
        mensaje = f"{timestamp.strftime('%Y-%m-%d %H:%M')} | Close: {row['Close']:.5f}"

        if signal == 1:  # Señal de COMPRA
            self._procesar_compra_rl(idx, row, timestamp, mensaje)
        elif signal == 2:  # Señal de VENTA
            self._procesar_venta_rl(idx, row, timestamp, mensaje)
        else:  # Sin señal
            self.log(mensaje, color="white")

    def _procesar_compra_rl(self, idx, row, timestamp, mensaje_base):
        """Procesa una señal de compra RL"""
        # Confirmación por patrones (si disponible): solo comprar si Final_Signal == 1
        if self._pattern_signals is not None:
            patt = int(self._pattern_signals.iloc[idx])
            if patt != 1:
                mensaje = mensaje_base + " | SEÑAL RL: COMPRA NO CONFIRMADA POR PATRONES"
                self.log(mensaje, color="gray")
                return

        # Abrir nueva posición (multi-posición permitida)
        pos = {
            'precio': float(row["Close"]),
            'fecha': timestamp,
            'indice': len(self.operaciones)
        }
        self.posiciones_activas.append(pos)

        mensaje = mensaje_base + f" | SEÑAL RL: COMPRA a {row['Close']:.5f} (posiciones activas: {len(self.posiciones_activas)})"
        self.log(mensaje, color="green")

        # Registrar operación (apertura)
        self.operaciones.append({
            'tipo': 'compra',
            'precio': float(row["Close"]),
            'fecha': timestamp,
            'signal_idx': idx
        })

    def _procesar_venta_rl(self, idx, row, timestamp, mensaje_base):
        """Procesa una señal de venta RL"""
        if not self.posiciones_activas:
            mensaje = mensaje_base + " | SEÑAL RL: VENTA IGNORADA (no hay posiciones activas)"
            self.log(mensaje, color="orange")
            return

        # Confirmación por patrones (si disponible): solo vender si Final_Signal == -1
        if self._pattern_signals is not None:
            patt = int(self._pattern_signals.iloc[idx])
            if patt != -1:
                mensaje = mensaje_base + " | SEÑAL RL: VENTA NO CONFIRMADA POR PATRONES"
                self.log(mensaje, color="gray")
                return

        precio_venta = float(row["Close"])
        # Cerrar todas las posiciones activas al precio actual
        cerradas = 0
        for pos in list(self.posiciones_activas):
            precio_compra = float(pos['precio'])
            ganancia = precio_venta - precio_compra
            porcentaje_ganancia = (ganancia / precio_compra) * 100 if precio_compra != 0 else 0.0

            color, msg_gan = self._formatear_resultado_rl(ganancia, porcentaje_ganancia)
            msg = (f"{mensaje_base} | SEÑAL RL: VENTA a {precio_venta:.5f} | "
                   f"Compra: {precio_compra:.5f} | {msg_gan}")
            self.log(msg, color=color)

            # Actualizar operación correspondiente a esta compra (por indice)
            if pos['indice'] < len(self.operaciones):
                self.operaciones[pos['indice']].update({
                    'venta_precio': precio_venta,
                    'venta_fecha': timestamp,
                    'ganancia': ganancia,
                    'porcentaje_ganancia': porcentaje_ganancia
                })

            self.posiciones_activas.remove(pos)
            cerradas += 1

        if cerradas > 0:
            self.log(f"Cerradas {cerradas} posiciones", color="blue")

    def _formatear_resultado_rl(self, ganancia, porcentaje):
        """Formatea el resultado de la operación RL"""
        if ganancia >= 0:
            return "green", f"Ganancia: +{ganancia:.5f} (+{porcentaje:.2f}%)"
        else:
            return "red", f"Pérdida: {ganancia:.5f} ({porcentaje:.2f}%)"

    def _mostrar_resumen_operaciones_rl(self):
        """Muestra un resumen de las operaciones RL realizadas"""
        if not hasattr(self, 'operaciones') or not self.operaciones:
            return
            
        operaciones_completas = [op for op in self.operaciones if 'ganancia' in op]
        
        if operaciones_completas:
            ganancias = [op['ganancia'] for op in operaciones_completas]
            ganancia_total = sum(ganancias)
            porcentaje_total = sum(op['porcentaje_ganancia'] for op in operaciones_completas)
            
            self.log(f"\nRESUMEN RL: {len(operaciones_completas)} operaciones | "
                    f"Ganancia total: {ganancia_total:.5f} | "
                    f"Rendimiento: {porcentaje_total:.2f}%", 
                    color="blue" if ganancia_total >= 0 else "red")

            # Resumen monetario con el dinero base introducido
            try:
                capital_inicial = float(self.entry_dinero.get()) if self.entry_dinero.get() else float(self.dinero_ficticio)
            except Exception:
                capital_inicial = float(self.dinero_ficticio)

            beneficios_totales = sum(g for g in ganancias if g >= 0)
            perdidas_totales = sum(-g for g in ganancias if g < 0)
            ganancia_neta = beneficios_totales - perdidas_totales
            capital_final = capital_inicial + ganancia_neta

            self.log("="*60, color='white')
            self.log("RESUMEN MONETARIO RL", color='yellow')
            self.log(f"Capital inicial: ${capital_inicial:,.2f}", color='white')
            self.log(f"Beneficios: ${beneficios_totales:,.2f}", color='green')
            self.log(f"Pérdidas: ${perdidas_totales:,.2f}", color='red')
            self.log(f"Resultado neto: ${ganancia_neta:+,.2f}", color='cyan' if ganancia_neta >= 0 else 'orange')
            self.log(f"Capital final: ${capital_final:,.2f}", color='cyan')
            self.log("="*60, color='white')

            # Actualizar etiquetas de la interfaz
            self.dinero_ficticio = capital_final
            self.beneficios = beneficios_totales
            self.perdidas = perdidas_totales
            self.actualizar_labels()

    # ---------------- Funciones Gráficos ----------------
    def _dibujar_grafico(self, df):
        self.grafico_manager.dibujar_csv(df)
        self.tooltip_zoom_pan = TooltipZoomPan(self.root, self.grafico_manager.canvas, self.grafico_manager.grafico)

    def reset_zoom(self):
        if self.tooltip_zoom_pan:
            self.tooltip_zoom_pan.reset_zoom()

    def reiniciar_app(self):
        """Reinicia la aplicación reemplazando el proceso actual por `python -m app.main`."""
        confirmar = messagebox.askyesno(
            "Reiniciar",
            "¿Seguro que quieres reiniciar la aplicación? Se perderá el estado actual.",
        )
        if not confirmar:
            return
        python = sys.executable
        # Reemplaza el proceso: no regresa
        os.execl(python, python, "-m", "app.main")

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

    def _append_telegram_panel(self, mensaje, color="white"):
        self.text_telegram.configure(state="normal")
        self.text_telegram.insert("end", mensaje + "\n", color)
        self.text_telegram.tag_configure(color, foreground=color)
        self.text_telegram.see("end")
        self.text_telegram.configure(state="disabled")

    def _copy_invite_link(self):
        link = self.var_invite.get()
        if link and link != "(sin conectar)":
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(link)
                self.root.update()
                messagebox.showinfo("Telegram", "Enlace copiado al portapapeles")
            except Exception as e:
                messagebox.showerror("Telegram", f"No se pudo copiar: {e}")

    def conectar_telegram(self):
        """Inicia la conexión con Telegram"""
        title = getattr(self, "telegram_title", None)
        description = getattr(self, "telegram_description", None)
        if not title:
            messagebox.showwarning("Telegram", "Configure primero el título y la descripción")
            return
        # Asegurar instancia
        try:
            if not hasattr(self, "telegram_notifier") or self.telegram_notifier is None:
                base_dir = os.path.dirname(os.path.dirname(__file__))
                module_path = os.path.join(base_dir, "telegram", "telegram-notifier.py")
                spec = importlib.util.spec_from_file_location("telegram_notifier", module_path)
                if spec is None or spec.loader is None:
                    raise ImportError("No se pudo cargar el módulo telegram-notifier.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                self.telegram_notifier = mod.TelegramNotifier()
        except Exception as e:
            messagebox.showerror("Telegram", f"Error cargando TelegramNotifier: {e}")
            return

        # Iniciar conexión en hilo y manejar callback
        self.btn_telegram_connect.config(state="disabled")
        self.var_invite.set("Conectando y creando canal...")
        self._actualizar_estado_telegram(conectando=True)

        def cb(invite_link, error):
            # Asegurar ejecución en hilo de Tk
            def _ui_update():
                if error:
                    messagebox.showerror("Telegram", f"Error: {error}")
                    self.btn_telegram_connect.config(state="normal")
                    self.var_invite.set("(sin conectar)")
                    self._actualizar_estado_telegram(conectado=False)
                else:
                    self.var_invite.set(invite_link or "(sin enlace)")
                    self.btn_copy_link.config(state="normal")
                    self._actualizar_estado_telegram(conectado=True)
                    messagebox.showinfo("Telegram", "Canal creado y enlace listo")
            self.root.after(0, _ui_update)

        try:
            self.telegram_notifier.init_telegram(title, description, callback=cb)
        except Exception as e:
            messagebox.showerror("Telegram", f"Error iniciando Telegram: {e}")
            self.btn_telegram_connect.config(state="normal")
            self._actualizar_estado_telegram(conectado=False)

    def _actualizar_estado_telegram(self, conectado=None, conectando=False):
        """Actualiza el estado de conexión de Telegram en la UI"""
        if conectando:
            self.lbl_telegram_status.config(text="Conectando...", fg="orange")
        elif conectado is True:
            self.lbl_telegram_status.config(text="Conectado", fg="green")
        else:
            self.lbl_telegram_status.config(text="Desconectado", fg="red")

    def _enviar_telegram_y_reflejar(self, mensaje, color="white"):
        # Reflejar en panel
        self._append_telegram_panel(mensaje, color="white")
        # Enviar a Telegram si está conectado
        notifier = getattr(self, "telegram_notifier", None)
        try:
            if notifier and hasattr(notifier, "send_message"):
                notifier.send_message(mensaje, is_trade_operation=False, trade_id=None)
            else:
                self._append_telegram_panel("(No conectado a Telegram)", color="yellow")
        except Exception as e:
            self._append_telegram_panel(f"Error enviando a Telegram: {e}", color="red")

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

    # ---------------- Funciones CSV ----------------
    def cargar_csv(self):
        """Carga un CSV usando CSVManager y abre un modal para seleccionar filas a cargar."""
        df = self.csv_manager.cargar_csv()
        if df is not None:
            # Abre modal para seleccionar el subconjunto a cargar y luego llama a _on_csv_cargado
            try:
                CSVLoaderModal(self.root, df, callback=self._on_csv_cargado)
            except Exception:
                # Fallback directo si el modal falla
                self._on_csv_cargado(df)

    # ---------------- Funciones de habilitación de botones ----------------
    def _update_btn_aplicar_patrones(self):
        """Habilita 'Mostrar Patrones' solo si se han cargado procesados y se ha añadido dinero ficticio (> 0)."""
        habilitar = self.df_actual is not None and (self.dinero_ficticio > 0)
        if hasattr(self, "btn_backtesting"):
            self.btn_backtesting.config(state="normal" if habilitar else "disabled")
        if hasattr(self, "btn_telegram"):
            self.btn_telegram.config(state="normal" if habilitar else "disabled")
        # Sincronizar menú 'Modelo IA'
        state = "normal" if habilitar else "disabled"
        if hasattr(self, "btn_modelo_ia"):
            self.btn_modelo_ia.config(state=state)
            try:
                if state == "normal":
                    self.btn_modelo_ia.state(["!disabled"])
                else:
                    self.btn_modelo_ia.state(["disabled"])
            except Exception:
                pass
        if hasattr(self, "menu_modelo_ia"):
            try:
                self.menu_modelo_ia.entryconfig(self._ia_label_crear_rl, state=state)
                self.menu_modelo_ia.entryconfig(self._ia_label_cargar_rl, state=state)
                self.menu_modelo_ia.entryconfig(self._ia_label_aplicar_rl, state=state)
            except Exception:
                pass

        # Sincronizar menú 'Opciones'
        state = "normal" if habilitar else "disabled"
        if hasattr(self, "btn_opciones"):
            self.btn_opciones.config(state=state)
            try:
                if state == "normal":
                    self.btn_opciones.state(["!disabled"])
                else:
                    self.btn_opciones.state(["disabled"])
            except Exception:
                pass
        if hasattr(self, "menu_opciones"):
            try:
                self.menu_opciones.entryconfig(self._menu_label_estrategias, state=state)
                self.menu_opciones.entryconfig(self._menu_label_patrones, state=state)
                self.menu_opciones.entryconfig(self._menu_label_backtesting, state=state)
                self.menu_opciones.entryconfig(self._menu_label_entrenar_ia, state=state)
            except Exception:
                pass

    def _update_btn_cargar_estrategias(self):
        """Habilita 'Mostrar Estrategias' solo si se han cargado procesados y se ha añadido dinero ficticio (> 0)."""
        habilitar = self.df_actual is not None and (self.dinero_ficticio > 0)
        if hasattr(self, "btn_cargar_estrategias"):
            self.btn_cargar_estrategias.config(state="normal" if habilitar else "disabled")
        if hasattr(self, "btn_backtesting"):
            self.btn_backtesting.config(state="normal" if habilitar else "disabled")
        if hasattr(self, "btn_telegram"):
            self.btn_telegram.config(state="normal" if habilitar else "disabled")
        # Sincronizar menú 'Modelo IA'
        state = "normal" if habilitar else "disabled"
        if hasattr(self, "btn_modelo_ia"):
            self.btn_modelo_ia.config(state=state)
            try:
                if state == "normal":
                    self.btn_modelo_ia.state(["!disabled"])
                else:
                    self.btn_modelo_ia.state(["disabled"])
            except Exception:
                pass
        if hasattr(self, "menu_modelo_ia"):
            try:
                self.menu_modelo_ia.entryconfig(self._ia_label_crear_rl, state=state)
                self.menu_modelo_ia.entryconfig(self._ia_label_cargar_rl, state=state)
                self.menu_modelo_ia.entryconfig(self._ia_label_aplicar_rl, state=state)
            except Exception:
                pass

        # Sincronizar menú 'Opciones'
        state = "normal" if habilitar else "disabled"
        if hasattr(self, "btn_opciones"):
            self.btn_opciones.config(state=state)
            # Asegurar compatibilidad con ttk.Menubutton
            try:
                if state == "normal":
                    self.btn_opciones.state(["!disabled"])
                else:
                    self.btn_opciones.state(["disabled"])
            except Exception:
                pass
        if hasattr(self, "menu_opciones"):
            # Asegura que las entradas del menú reflejen el mismo estado
            try:
                self.menu_opciones.entryconfig(self._menu_label_estrategias, state=state)
                self.menu_opciones.entryconfig(self._menu_label_patrones, state=state)
                self.menu_opciones.entryconfig(self._menu_label_backtesting, state=state)
                self.menu_opciones.entryconfig(self._menu_label_entrenar_ia, state=state)
            except Exception:
                pass

    # ---------------- Telegram ----------------
    def abrir_modal_telegram(self):
        """Abre el modal de Telegram"""
        # Crear ventana modal
        top = tk.Toplevel(self.root)
        top.title("Configurar Telegram")
        top.transient(self.root)
        top.grab_set()
        top.configure(bg="#F0F0F0")

        # Contenedor
        frame = tk.Frame(top, bg="#F0F0F0", padx=15, pady=15)
        frame.pack(fill="both", expand=True)

        # Título
        tk.Label(frame, text="Título del canal:", bg="#F0F0F0").grid(row=0, column=0, sticky="w")
        entry_title = ttk.Entry(frame, width=40)
        entry_title.grid(row=1, column=0, sticky="we", pady=(2, 10))

        # Descripción
        tk.Label(frame, text="Descripción:", bg="#F0F0F0").grid(row=2, column=0, sticky="w")
        text_desc = tk.Text(frame, height=5, width=40)
        text_desc.grid(row=3, column=0, sticky="we", pady=(2, 10))

        # Prefill con valores por defecto o los últimos guardados
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            module_path = os.path.join(base_dir, "telegram", "telegram-notifier.py")
            spec = importlib.util.spec_from_file_location("telegram_notifier", module_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                default_title = getattr(self, "telegram_title", None) or getattr(mod, "DEFAULT_TITLE", "")
                default_desc = getattr(self, "telegram_description", None) or getattr(mod, "DEFAULT_DESCRIPTION", "")
            else:
                default_title = getattr(self, "telegram_title", "")
                default_desc = getattr(self, "telegram_description", "")
        except Exception:
            default_title = getattr(self, "telegram_title", "")
            default_desc = getattr(self, "telegram_description", "")

        if default_title:
            entry_title.insert(0, default_title)
        if default_desc:
            text_desc.insert("1.0", default_desc)

        frame.columnconfigure(0, weight=1)

        # Acciones
        btns = tk.Frame(frame, bg="#F0F0F0")
        btns.grid(row=4, column=0, sticky="e")

        def on_cancel():
            top.destroy()

        def on_accept():
            title = entry_title.get().strip()
            description = text_desc.get("1.0", "end").strip()
            if not title:
                messagebox.showwarning("Telegram", "El título no puede estar vacío")
                return

            # Cargar dinámicamente TelegramNotifier desde telegram/telegram-notifier.py
            try:
                base_dir = os.path.dirname(os.path.dirname(__file__))
                module_path = os.path.join(base_dir, "telegram", "telegram-notifier.py")
                spec = importlib.util.spec_from_file_location("telegram_notifier", module_path)
                if spec is None or spec.loader is None:
                    raise ImportError("No se pudo cargar el módulo telegram-notifier.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                # Instanciar (cachear en self para reuso)
                if not hasattr(self, "telegram_notifier") or self.telegram_notifier is None:
                    self.telegram_notifier = mod.TelegramNotifier()

                # Guardar título y descripción (método async)
                try:
                    asyncio.run(self.telegram_notifier.save_title_and_description(title, description))
                    # Guardar también en GUI para usar al conectar
                    self.telegram_title = title
                    self.telegram_description = description
                    # Habilitar botón conectar
                    self.btn_telegram_connect.config(state="normal")
                    messagebox.showinfo("Telegram", "Título y descripción guardados")
                    top.destroy()
                except Exception as e:
                    messagebox.showerror("Telegram", f"Error guardando datos: {e}")
            except Exception as e:
                messagebox.showerror("Telegram", f"Error cargando TelegramNotifier: {e}")

        ttk.Button(btns, text="Cancelar", command=on_cancel).pack(side="right", padx=5)
        ttk.Button(btns, text="Aceptar", command=on_accept).pack(side="right")

        # Centrar el modal respecto a la ventana padre
        try:
            top.update_idletasks()
            pw, ph = self.root.winfo_width(), self.root.winfo_height()
            px, py = self.root.winfo_rootx(), self.root.winfo_rooty()
            ww, wh = top.winfo_width(), top.winfo_height()
            x = px + max(0, (pw - ww) // 2)
            y = py + max(0, (ph - wh) // 2)
            top.geometry(f"+{x}+{y}")
        except Exception:
            pass

    # ---------------- IA ----------------
    def entrenar_ia(self):
        """Muestra el modal de entrenamiento de IA"""
        def on_accept(
            seleccion_fx=None,
            seleccion_patterns=None,
            seleccion_candle=None,
            max_orders=5,
            use_winrate=False,
            winrate=0.0,
            selected_model_path=None,
            save_best=True,
            timesteps_per_attempt=3000,
        ):
            """Recibe selecciones del modal e inicia el entrenador en hilo de fondo."""
            seleccion_fx = seleccion_fx or {}
            seleccion_patterns = seleccion_patterns or []
            seleccion_candle = seleccion_candle or []

            # Mostrar barra de progreso
            try:
                self._show_progress_bar()
                self.progress_var.set(0)
                self.progress_info_var.set("0/0 (0%) ETA --:--")
                self._train_start_ts = time.time()
                self._train_total = 0
                self.btn_stop_training.config(state="normal")
            except Exception:
                pass

            # Preparar archivo de log por sesión
            try:
                project_root = os.path.dirname(os.path.dirname(__file__))
                logs_dir = os.path.join(project_root, 'logs')
                os.makedirs(logs_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                self._training_log_path = os.path.join(logs_dir, f'log_{timestamp}.txt')
            except Exception:
                self._training_log_path = None

            def _file_log(line: str):
                try:
                    if not getattr(self, '_training_log_path', None):
                        return
                    ts = datetime.now().strftime('%H:%M:%S')
                    with open(self._training_log_path, 'a', encoding='utf-8') as f:
                        f.write(f"[{ts}] {line}\n")
                except Exception:
                    pass

            # Obtener capital del entry
            try:
                capital_inicial = float(self.entry_dinero.get())
                if capital_inicial <= 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Entrenamiento IA", "Ingrese un capital válido en 'Dinero ficticio'")
                return

            # Callbacks seguros para UI
            def ui_log(msg: str, color: str = 'white'):
                try:
                    text = str(msg)
                    self.root.after(0, lambda: self.log(text, color))
                    _file_log(text)

                    # Sincronizar barra de progreso con logs de inicio/fin de entrenamiento RL
                    if "INICIANDO ENTRENAMIENTO RL CON ESTRATEGIAS" in text:
                        # Reset a 0%
                        def _reset_progress():
                            try:
                                self.progress_var.set(0)
                                self.header_progress_label.config(text="0%")
                                # asegurar que el label quede por encima
                                self.header_progress_label.lift()
                            except Exception:
                                pass
                        self.root.after(0, _reset_progress)

                    if "ENTRENAMIENTO RL COMPLETADO" in text:
                        # Completar al 100%
                        def _finish_progress():
                            try:
                                self.progress_var.set(100)
                                self.header_progress_label.config(text="100%")
                                self.header_progress_label.lift()
                            except Exception:
                                pass
                        self.root.after(0, _finish_progress)
                except Exception:
                    pass

            def ui_progress(cur: int, total: int):
                try:
                    pct = int((cur / max(1, total)) * 100)
                    self.root.after(0, lambda: self.progress_var.set(min(max(pct, 0), 100)))
                    self.root.after(0, lambda: self.header_progress_label.config(text=f"{min(max(pct, 0), 100)}%"))
                    # Detectar cambio de fase (cambio de total): reiniciar cronómetro y barra
                    if getattr(self, '_train_total', 0) != total:
                        self._train_total = total
                        # Reiniciar cronómetro para ETA y barra al 0%
                        self._train_start_ts = time.time()
                        self.root.after(0, lambda: self.progress_var.set(0))
                        self.root.after(0, lambda: self.header_progress_label.config(text="0%"))
                    def _fmt_eta():
                        try:
                            start = getattr(self, '_train_start_ts', None)
                            if not start:
                                return "--:--"
                            elapsed = max(0.0, time.time() - start)
                            rate = (cur / elapsed) if elapsed > 0 else 0.0
                            remaining = ((total - cur) / rate) if rate > 0 else 0.0
                            m = int(remaining // 60)
                            s = int(remaining % 60)
                            return f"{m:02d}:{s:02d}"
                        except Exception:
                            return "--:--"
                    eta_str = _fmt_eta()
                    self.root.after(0, lambda: self.progress_info_var.set(f"{cur}/{total} ({pct}%) ETA {eta_str}"))
                except Exception:
                    pass

            def ui_finish(stats: dict):
                try:
                    err = stats.get('error')
                    if err:
                        self.root.after(0, lambda: ui_log(f"Entrenamiento detenido: {err}", 'red'))
                        self.root.after(0, self._hide_progress_bar)
                        return
                except Exception:
                    pass

                try:
                    capital_final = float(stats.get('capital_final', self.dinero_ficticio))
                    beneficio_total = float(stats.get('beneficio_total', 0.0))
                    dinero_ganado = float(stats.get('dinero_ganado', 0.0))
                    dinero_perdido = float(stats.get('dinero_perdido', 0.0))
                    self.dinero_ficticio = capital_final
                    self.beneficios = max(0.0, dinero_ganado)
                    self.perdidas = abs(dinero_perdido)
                    self.actualizar_labels()
                except Exception:
                    pass

                try:
                    ops_g = int(stats.get('operaciones_ganadas', 0))
                    ops_p = int(stats.get('operaciones_perdidas', 0))
                    ops_a = int(stats.get('operaciones_activas', 0))
                    max_ops = int(stats.get('max_operaciones', 0))
                    winrate = float(stats.get('winrate', 0.0))
                    self.root.after(0, lambda: ui_log("="*60, 'white'))
                    self.root.after(0, lambda: ui_log("RESUMEN ENTRENAMIENTO IA", 'yellow'))
                    self.root.after(0, lambda: ui_log(f"Capital final: ${capital_final:,.2f}", 'cyan'))
                    self.root.after(0, lambda: ui_log(f"Beneficio total: ${beneficio_total:,.2f}", 'cyan'))
                    self.root.after(0, lambda: ui_log(f"Operaciones ganadas: {ops_g}", 'green'))
                    self.root.after(0, lambda: ui_log(f"Operaciones perdidas: {ops_p}", 'red'))
                    self.root.after(0, lambda: ui_log(f"Dinero ganado en operaciones ganadoras: ${float(stats.get('dinero_ganado', 0.0)):,.2f}", 'green'))
                    self.root.after(0, lambda: ui_log(f"Dinero perdido en operaciones perdedoras: -${abs(float(stats.get('dinero_perdido', 0.0))):,.2f}", 'red'))
                    
                    try:
                        fx_cfg = stats.get('fx_config') or {}
                        candle_cfg = stats.get('candle_config') or []
                        patterns_cfg = stats.get('patterns_config') or []
                        
                        if fx_cfg:
                            self.root.after(0, lambda: ui_log("Configuración FX utilizada:", 'white'))
                            for k, v in fx_cfg.items():
                                try:
                                    riesgo = float(v.get('riesgo', 0.01))
                                    rr = float(v.get('rr', 2.0))
                                except Exception:
                                    riesgo, rr = 0.01, 2.0
                                line = f" - {k}: riesgo={riesgo:.3f}, rr={rr:.2f}"
                                self.root.after(0, lambda l=line: ui_log(l, 'white'))
                        
                        if candle_cfg:
                            self.root.after(0, lambda: ui_log(f"Estrategias Candle: {', '.join(candle_cfg)}", 'white'))
                        
                        if patterns_cfg:
                            self.root.after(0, lambda: ui_log(f"Patrones: {', '.join(patterns_cfg)}", 'white'))
                            
                    except Exception:
                        pass
                        
                    self.root.after(0, lambda: ui_log(f"Win Rate: {winrate:.1f}%", 'white'))
                    self.root.after(0, lambda: ui_log(f"Slots usados: {ops_a}/{max_ops}", 'blue'))
                    
                    try:
                        best_stats = stats.get('best', {})
                        if best_stats:
                            self.root.after(0, lambda: ui_log("="*60, 'white'))
                            self.root.after(0, lambda: ui_log("MEJOR CONFIGURACIÓN ENCONTRADA", 'yellow'))
                            self.root.after(0, lambda: ui_log(f"WinRate: {best_stats.get('stats', {}).get('winrate', 0):.1f}%", 'cyan'))
                            self.root.after(0, lambda: ui_log(f"Intento: {best_stats.get('stats', {}).get('attempt', 0)}", 'white'))
                    except Exception:
                        pass
                        
                    self.root.after(0, lambda: ui_log("="*60, 'white'))
                except Exception:
                    pass

                try:
                    # Aviso visual al finalizar entrenamiento IA (modal avanzado)
                    self.root.after(0, lambda: messagebox.showinfo("IA", "Entrenamiento IA completado y modelo guardado"))
                except Exception:
                    pass

                # Aplicar señales RL automáticamente al finalizar el entrenamiento IA
                try:
                    self.root.after(0, lambda: (
                        self.log("Aplicando señales RL post-entrenamiento...", color='yellow'),
                        self.aplicar_senales_rl()
                    ))
                except Exception:
                    pass

                try:
                    self.root.after(0, lambda: self.progress_var.set(100))
                    self.root.after(0, lambda: self.header_progress_label.config(text="100%"))
                    self.root.after(1200, self._hide_progress_bar)
                except Exception:
                    pass

            # SOLUCIÓN OPCIÓN 1 - Preparar agente RL con verificación de compatibilidad
            try:
                if selected_model_path:
                    model_dir, fname = os.path.split(selected_model_path)
                    base, ext = os.path.splitext(fname)
                    model_name = base
                    if not model_dir:
                        model_dir = 'models_rl'
                    
                    model_full_path = os.path.join(model_dir, model_name + ".zip")
                    if os.path.exists(model_full_path):
                        try:
                            temp_model = PPO.load(model_full_path)
                            old_dims = temp_model.policy.observation_space.shape[0]
                            
                            temp_agent = RLTradingAgent(
                                self.df_actual,
                                estrategias_fx=seleccion_fx,
                                estrategias_candle=seleccion_candle,
                                patrones=seleccion_patterns,
                                log_fn=lambda m: ui_log(m, 'cyan'),
                            )
                            new_dims = temp_agent.env.observation_space.shape[0]
                            
                            if old_dims != new_dims:
                                ui_log(f"⚠️ Modelo incompatible ({old_dims} vs {new_dims}). Eliminando y creando nuevo...", 'yellow')
                                os.remove(model_full_path)
                                self.rl_agent = RLTradingAgent(
                                    self.df_actual,
                                    estrategias_fx=seleccion_fx,
                                    estrategias_candle=seleccion_candle,
                                    patrones=seleccion_patterns,
                                    model_dir=model_dir,
                                    model_name=model_name,
                                    log_fn=lambda m: ui_log(m, 'cyan'),
                                )
                                ui_log("🆕 Nuevo modelo creado con dimensiones correctas", 'green')
                            else:
                                self.rl_agent = RLTradingAgent(
                                    self.df_actual,
                                    estrategias_fx=seleccion_fx,
                                    estrategias_candle=seleccion_candle,
                                    patrones=seleccion_patterns,
                                    model_dir=model_dir,
                                    model_name=model_name,
                                    log_fn=lambda m: ui_log(m, 'cyan'),
                                )
                                self.rl_agent.cargar_modelo()
                                
                        except Exception as e:
                            ui_log(f"❌ Error verificando modelo: {e}. Creando nuevo...", 'red')
                            if os.path.exists(model_full_path):
                                os.remove(model_full_path)
                            self.rl_agent = RLTradingAgent(
                                self.df_actual,
                                estrategias_fx=seleccion_fx,
                                estrategias_candle=seleccion_candle,
                                patrones=seleccion_patterns,
                                model_dir=model_dir,
                                model_name=model_name,
                                log_fn=lambda m: ui_log(m, 'cyan'),
                            )
                    else:
                        self.rl_agent = RLTradingAgent(
                            self.df_actual,
                            estrategias_fx=seleccion_fx,
                            estrategias_candle=seleccion_candle,
                            patrones=seleccion_patterns,
                            model_dir=model_dir,
                            model_name=model_name,
                            log_fn=lambda m: ui_log(m, 'cyan'),
                        )
                else:
                    if not hasattr(self, 'rl_agent') or self.rl_agent is None:
                        self.rl_agent = RLTradingAgent(
                            self.df_actual,
                            estrategias_fx=seleccion_fx,
                            estrategias_candle=seleccion_candle,
                            patrones=seleccion_patterns,
                            log_fn=lambda m: ui_log(m, 'cyan')
                        )
            except Exception as e:
                ui_log(f"No se pudo preparar el agente RL: {e}", 'red')
                return

            # Iniciar entrenador
            trainer = AITrainer(
                df=self.df_actual,
                seleccion_fx=seleccion_fx,
                seleccion_patterns=seleccion_patterns,
                seleccion_candle=seleccion_candle,
                max_orders=max_orders,
                capital_inicial=capital_inicial,
                use_winrate=use_winrate,
                winrate_target=winrate,
                save_best=save_best,
                timesteps_per_attempt=timesteps_per_attempt,
                on_log=ui_log,
                on_progress=ui_progress,
                on_finish=ui_finish,
            )
            
            self._ai_trainer = trainer

            # Habilitar opción "Detener IA" y deshabilitar "Entrenar IA" durante el entrenamiento
            try:
                if hasattr(self, 'menu_opciones'):
                    self.menu_opciones.entryconfig(self._menu_label_detener_ia, state="normal")
                    self.menu_opciones.entryconfig(self._menu_label_entrenar_ia, state="disabled")
            except Exception:
                pass

            # Escribir cabecera de sesión
            try:
                ui_log("="*60, 'white')
                ui_log("INICIO SESIÓN ENTRENAMIENTO IA", 'yellow')
                ui_log(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'white')
                ui_log(f"Max órdenes: {max_orders}", 'white')
                stop_desc = f"WinRate objetivo: {winrate:.1f}%" if use_winrate else "Sin condición explícita"
                ui_log(f"Parada: {stop_desc}", 'white')
                
                if selected_model_path:
                    ui_log(f"Modelo RL: {selected_model_path}", 'white')
                if seleccion_fx:
                    ui_log(f"Estrategias FX: {', '.join(seleccion_fx.keys())}", 'white')
                if seleccion_candle:
                    ui_log(f"Estrategias Candle: {', '.join(seleccion_candle)}", 'white')
                if seleccion_patterns:
                    ui_log(f"Patrones: {', '.join(seleccion_patterns)}", 'white')
                ui_log("="*60, 'white')
            except Exception:
                pass
            
            trainer.start()

        if self.df_actual is None:
            messagebox.showwarning("Datos requeridos", "Por favor, carga los datos primero.")
            return

        modal = AITrainingModal(self.root, on_accept_callback=on_accept)
        modal.show()

    def detener_entrenamiento_ia(self):
        """Detiene el entrenamiento de IA en curso si existe."""
        try:
            if hasattr(self, "_ai_trainer") and self._ai_trainer:
                trainer = self._ai_trainer
                trainer.stop()
                # Evitar múltiples solicitudes de parada
                try:
                    if hasattr(self, 'menu_opciones'):
                        self.menu_opciones.entryconfig(self._menu_label_detener_ia, state="disabled")
                except Exception:
                    pass
                self.log("Solicitud de detener entrenamiento enviada.", "yellow")
                if hasattr(self, "lbl_ai_status"):
                    self.lbl_ai_status.config(text="Listo para entrenar", fg="blue")

                self._ai_trainer = None
            else:
                self.log("⚠️ No hay entrenamiento en curso para detener.", "orange")
        except Exception as e:
            self.log(f"Error al detener el entrenamiento: {e}", "red")

    # ---- Utilidades barra de progreso ----
    def _show_progress_bar(self):
        try:
            # Mostrar la barra en el header (a la izquierda de "Limpiar Log")
            self.progress_var.set(0)
            self.header_progress_label.config(text="0%")
            self.header_progress_frame.pack(side="right", padx=(0, 8))
            # Asegurar que el texto se centra
            self.header_progressbar.update_idletasks()
            self.header_progress_label.lift()
        except Exception:
            pass

    def _hide_progress_bar(self):
        try:
            # Ocultar barra del header
            self.header_progress_frame.pack_forget()
            # Deshabilitar botón Detener cuando no hay entrenamiento (si se usa el inferior)
            self.btn_stop_training.config(state="disabled")
        except Exception:
            pass

    # ---- Utilidades Menú Opciones ----
    def _set_menu_opcion_state(self, label: str, state: str):
        """Cambia el estado ('normal'/'disabled') de una entrada del menú Opciones por su etiqueta."""
        try:
            end_index = self.menu_opciones.index('end')
            if end_index is None:
                return
            for i in range(end_index + 1):
                try:
                    if self.menu_opciones.entrycget(i, 'label') == label:
                        self.menu_opciones.entryconfigure(i, state=state)
                        break
                except Exception:
                    continue
        except Exception:
            pass

    def _stop_training(self):
        """Handler para botón Detener: solicita parada al entrenador en curso."""
        try:
            trainer = getattr(self, '_ai_trainer', None)
            if trainer is not None:
                trainer.stop()
                # Evitar múltiples clics
                self.btn_stop_training.config(state="disabled")
        except Exception:
            pass

    # ---------------- Run ----------------
    def run(self):
        self.root.mainloop()