# app/strategies_modal.py

import tkinter as tk
from tkinter import ttk, messagebox
import re
import os
import json

import threading
import pandas as pd
import inspect
from strategies.strategy_utils import resolve_strategy_name
from strategies.strategies import ForexStrategies
from strategies.candle_strategies import CandleStrategies
from strategies.risk_manager import RiskManager, RiskManagerIntegration
from .binance_modal import CandleConfigModal
from ia_strategies.chatgpt_strategies import SuperheroStrategies
from ia_strategies.deep_seek_strategies import QuantumStrategies

class EstrategiasModal(tk.Toplevel):
    def __init__(self, parent, estrategias_fx, estrategias_candle, callback, patrones_list=None):
        # Si parent es GUIPrincipal, usar su root como parent de Tkinter
        if hasattr(parent, 'root'):
            super().__init__(parent.root)
            self.gui_parent = parent  # Referencia a GUIPrincipal para acceder a datos
        else:
            super().__init__(parent)
            self.gui_parent = parent
        self.parent = parent
        self.callback = callback
        self.title("Seleccionar Estrategias Forex y Candle")
        self.resizable(False, False)
        self.grab_set()  # modal

        # Altura fija de la zona de estrategias (scrollable)
        list_area_height = 400

        # Centrar ventana sobre el padre
        self.update_idletasks()
        w = 600
        # Altura total del modal: área de lista (400) + controles inferiores
        h_total = 500
        # Usar gui_parent.root para obtener coordenadas si es necesario
        parent_widget = self.gui_parent.root if hasattr(self.gui_parent, 'root') else self.gui_parent
        x = parent_widget.winfo_rootx() + (parent_widget.winfo_width() - w) // 2
        y = parent_widget.winfo_rooty() + (parent_widget.winfo_height() - h_total) // 2
        self.geometry(f"{w}x{h_total}+{x}+{y}")

        # Frame principal con scrollbar
        main_frame = tk.Frame(self)
        main_frame.pack(fill="x", expand=False, padx=10, pady=10)
        # Fijar altura visible de la lista a 400 y evitar que se expanda
        main_frame.configure(height=list_area_height)
        main_frame.pack_propagate(False)

        # Canvas y scrollbar para estrategias
        self.canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            main_frame,
            orient="vertical",
            style="Logs.Vertical.TScrollbar",
            command=self.canvas.yview,
        )
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        # Activar/desactivar scroll con rueda al entrar/salir
        self.scrollable_frame.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.scrollable_frame.bind("<Leave>", lambda e: self._unbind_mousewheel())

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set, height=list_area_height)

        # Pack canvas y scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Diccionario de controles
        self.controls = {}

        # Configurar una columna expansible para alinear botones a la derecha
        # Usaremos la columna 4 como expansor y colocaremos los botones en la 5
        try:
            self.scrollable_frame.grid_columnconfigure(4, weight=1)
        except Exception:
            pass

        # ---------------- SECCIÓN FOREX STRATEGIES ----------------
        if estrategias_fx:
            lbl_fx = ttk.Label(self.scrollable_frame, text="Forex Strategies", 
                               font=("Arial", 10, "bold"), anchor="w")
            lbl_fx.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

            # Botones para seleccionar/deseleccionar todas las Forex (centrados)
            btn_fx_frame = tk.Frame(self.scrollable_frame)
            btn_fx_frame.grid(row=1, column=0, columnspan=7, pady=(0, 5))
            btn_fx_sel = ttk.Button(
                btn_fx_frame,
                text="Seleccionar todos",
                command=lambda: self._set_group("forex", 1),
                width=18
            )
            btn_fx_desel = ttk.Button(
                btn_fx_frame,
                text="Deseleccionar todos",
                command=lambda: self._set_group("forex", 0),
                width=20
            )
            btn_fx_sel.pack(side="left", padx=5)
            btn_fx_desel.pack(side="left", padx=5)

            # Encabezado para Forex Strategies
            ttk.Label(self.scrollable_frame, text="Estrategia", width=20, anchor="w").grid(row=2, column=0, padx=5)
            ttk.Label(self.scrollable_frame, text="Riesgo (%)", width=10).grid(row=2, column=1, padx=5)
            ttk.Label(self.scrollable_frame, text="RR Ratio", width=10).grid(row=2, column=2, padx=5)
            ttk.Label(self.scrollable_frame, text="", width=10).grid(row=2, column=3, padx=5)

            # Validación: permitir hasta 2 decimales en Riesgo (%)
            vcmd_riesgo = (self.register(self._validate_two_decimals), '%P')

            # Estrategias Forex con parámetros
            for idx, nombre in enumerate(estrategias_fx, start=3):
                var_check = tk.IntVar()
                display_name = nombre.replace('_', ' ').capitalize()
                chk = tk.Checkbutton(self.scrollable_frame, text=display_name, variable=var_check, 
                                    anchor="w", width=20)
                chk.grid(row=idx, column=0, sticky="w", padx=5, pady=2)
                
                # Definir niveles de riesgo para cada estrategia
                risk_levels = {
                    # Alto riesgo
                    "breakout": ("Alto", "red"),
                    "scalping_1m_strategy": ("Alto", "red"),
                    "news_trading_strategy": ("Alto", "red"),
                    "grid_trading_strategy": ("Alto", "red"),
                    "mean_reversion": ("Alto", "red"),
                    "mean_reversion_strategy": ("Alto", "red"),
                    "mean_reversion_overlay": ("Alto", "red"),
                    # Medio riesgo
                    "adx_strategy": ("Medio", "orange"),
                    "trend_following": ("Medio", "orange"),
                    "macd_strategy": ("Medio", "orange"),
                    "ichimoku_cloud_strategy": ("Medio", "orange"),
                    "carry_trade_strategy": ("Medio", "orange"),
                    "hedging_overlay": ("Medio", "orange"),
                    "martingale_overlay": ("Medio", "orange"),
                    "price_action_patterns": ("Medio", "orange"),
                    "stochastic_strategy": ("Medio", "orange"),
                    "stochastic_oscillator_strategy": ("Medio", "orange"),
                    # Bajo riesgo
                    "rsi_strategy": ("Bajo", "green"),
                    "moving_average_crossover": ("Bajo", "green"),
                    "bollinger_bands_strategy": ("Bajo", "green"),
                    "support_resistance_strategy": ("Bajo", "green"),
                    "supply_demand_zones": ("Bajo", "green"),
                    "trendline_strategy": ("Bajo", "green"),
                    "range_trading_strategy": ("Bajo", "green")
                }
                
                # Aplicar etiqueta de riesgo en función del método real
                real_name = resolve_strategy_name(nombre, "forex")
                if real_name in risk_levels:
                    level, color = risk_levels[real_name]
                    ttk.Label(
                        self.scrollable_frame, 
                        text=f"[Riesgo {level}]", 
                        foreground=color,
                        font=('Arial', 8, 'bold')
                    ).grid(row=idx, column=4, padx=5, sticky="w")

                var_riesgo = tk.StringVar(value="1.00")  # % por defecto
                entry_riesgo = tk.Entry(
                    self.scrollable_frame,
                    textvariable=var_riesgo,
                    width=8,
                    validate="key",
                    validatecommand=vcmd_riesgo,
                )
                entry_riesgo.grid(row=idx, column=1, padx=5)

                var_rr = tk.StringVar(value="2")  # ratio por defecto
                entry_rr = tk.Entry(self.scrollable_frame, textvariable=var_rr, width=8)
                entry_rr.grid(row=idx, column=2, padx=5)

                # Añadir etiqueta de versión al lado del último textbox (solo Forex)
                if real_name in {"adx_strategy", "trend_following", "breakout", "rsi_strategy"}:
                    version_text = "(versión 1.0)"
                else:
                    version_text = "(versión 2.0)"
                ttk.Label(self.scrollable_frame, text=version_text, anchor="w").grid(row=idx, column=3, padx=5, sticky="w")

                self.controls[nombre] = {
                    "selected": var_check,
                    "riesgo": var_riesgo,
                    "rr": var_rr,
                    "tipo": "forex"
                }

        # ---------------- SECCIÓN CANDLE STRATEGIES ----------------
        # Descubrir dinámicamente estrategias Candle y fusionar con las recibidas
        try:
            discovered_candle = self._discover_candle_strategies()
        except Exception:
            discovered_candle = []
        try:
            provided_candle = list(estrategias_candle or [])
        except Exception:
            provided_candle = []
        self.estrategias_candle = sorted(set(provided_candle + discovered_candle))

        if self.estrategias_candle:
            start_row = len(estrategias_fx) + 3 if estrategias_fx else 0
            
            lbl_candle = ttk.Label(self.scrollable_frame, text="Candle Strategies", 
                                   font=("Arial", 10, "bold"), anchor="w")
            lbl_candle.grid(row=start_row, column=0, columnspan=3, sticky="w", pady=(20, 10))

            # Botones para seleccionar/deseleccionar todas las Candle (centrados)
            btn_candle_frame = tk.Frame(self.scrollable_frame)
            btn_candle_frame.grid(row=start_row + 1, column=0, columnspan=7, pady=(0, 5))
            btn_candle_sel = ttk.Button(
                btn_candle_frame,
                text="Seleccionar todos",
                command=lambda: self._set_group("candle", 1),
                width=18
            )
            btn_candle_desel = ttk.Button(
                btn_candle_frame,
                text="Deseleccionar todos",
                command=lambda: self._set_group("candle", 0),
                width=20
            )
            btn_candle_sel.pack(side="left", padx=5)
            btn_candle_desel.pack(side="left", padx=5)

            # Botón para cargar configuraciones desde carpeta config/
            try:
                all_exist = self._can_load_all_candle_configs(self.estrategias_candle)
            except Exception:
                all_exist = False
            self.btn_load_candle_configs = ttk.Button(
                btn_candle_frame,
                text="Cargar configuraciones",
                command=self._load_all_candle_configs,
                width=23,
                state=("normal" if all_exist else "disabled")
            )
            self.btn_load_candle_configs.pack(side="left", padx=5)

            # Encabezado para Candle Strategies (con configuración personalizada)
            ttk.Label(self.scrollable_frame, text="Estrategia", width=20, anchor="w").grid(row=start_row+2, column=0, padx=5)
            ttk.Label(self.scrollable_frame, text="Configuración", width=15).grid(row=start_row+2, column=1, padx=5)
            ttk.Label(self.scrollable_frame, text="", width=15).grid(row=start_row+2, column=2, padx=5)

            # Estrategias Candle (con configuración personalizada)
            for idx, nombre in enumerate(self.estrategias_candle, start=start_row+3):
                var_check = tk.IntVar()
                display_name = nombre.replace('_', ' ').capitalize()
                chk = tk.Checkbutton(self.scrollable_frame, text=display_name, variable=var_check, 
                                    anchor="w", width=20)
                chk.grid(row=idx, column=0, sticky="w", padx=5, pady=2)

                # Combobox para seleccionar configuración
                var_config = tk.StringVar(value="Default")
                config_combo = ttk.Combobox(
                    self.scrollable_frame,
                    textvariable=var_config,
                    values=["Default", "Custom"],
                    state="readonly",
                    width=12
                )
                config_combo.grid(row=idx, column=1, padx=5)

                # Botón para abrir modal de configuración (inicialmente deshabilitado)
                btn_config = ttk.Button(
                    self.scrollable_frame,
                    text="Configuración",
                    command=lambda n=nombre: self._open_candle_config(n),
                    state="disabled",
                    width=14
                )
                btn_config.grid(row=idx, column=2, padx=5, sticky="w")

                # Cambiar estado del botón según selección del combo
                def on_combo_change(event, n=nombre):
                    try:
                        ctrl = self.controls.get(n)
                        if not ctrl:
                            return
                        if ctrl["config_type"].get() == "Custom":
                            ctrl["config_button"].config(state="normal")
                            # Inicializar config si no existe con preset por estrategia
                            if ctrl.get("custom_config") is None:
                                ctrl["custom_config"] = self._get_default_candle_config(n)
                        else:
                            ctrl["config_button"].config(state="disabled")
                    except Exception:
                        pass

                config_combo.bind('<<ComboboxSelected>>', on_combo_change)

                # Definir niveles de riesgo para cada estrategia
                risk_levels = {
                    # Alto riesgo
                    "breakout": ("Alto", "red"),
                    "scalping_1m_strategy": ("Alto", "red"),
                    "news_trading_strategy": ("Alto", "red"),
                    "grid_trading_strategy": ("Alto", "red"),
                    "mean_reversion": ("Alto", "red"),
                    "mean_reversion_strategy": ("Alto", "red"),
                    "mean_reversion_overlay": ("Alto", "red"),
                    # Medio riesgo
                    "adx_strategy": ("Medio", "orange"),
                    "trend_following": ("Medio", "orange"),
                    "macd_strategy": ("Medio", "orange"),
                    "ichimoku_cloud_strategy": ("Medio", "orange"),
                    "carry_trade_strategy": ("Medio", "orange"),
                    "hedging_overlay": ("Medio", "orange"),
                    "martingale_overlay": ("Medio", "orange"),
                    "price_action_patterns": ("Medio", "orange"),
                    "stochastic_strategy": ("Medio", "orange"),
                    "stochastic_oscillator_strategy": ("Medio", "orange"),
                    # Bajo riesgo
                    "rsi_strategy": ("Bajo", "green"),
                    "moving_average_crossover": ("Bajo", "green"),
                    "bollinger_bands_strategy": ("Bajo", "green"),
                    "support_resistance_strategy": ("Bajo", "green"),
                    "supply_demand_zones": ("Bajo", "green"),
                    "trendline_strategy": ("Bajo", "green"),
                    "range_trading_strategy": ("Bajo", "green")
                }

                # Aplicar etiqueta de riesgo si la estrategia está en el diccionario
                if nombre in risk_levels:
                    level, color = risk_levels[nombre]
                    ttk.Label(
                        self.scrollable_frame,
                        text=f"[Riesgo {level}]",
                        foreground=color,
                        font=('Arial', 8, 'bold')
                    ).grid(row=idx, column=4, padx=5, sticky="w")

                self.controls[nombre] = {
                    "selected": var_check,
                    "tipo": "candle",
                    "config_type": var_config,
                    "config_button": btn_config,
                    "custom_config": None
                }

        # ---------------- SECCIÓN RAPIÑAIRE STRATEGIES ----------------
        # Descubrir estrategias desde SuperheroStrategies y QuantumStrategies
        try:
            discovered_rapinaire, providers_map = self._discover_rapinaire_strategies()
        except Exception:
            discovered_rapinaire, providers_map = [], {}
        self.estrategias_rapinaire = sorted(set(discovered_rapinaire))
        self.rapinaire_providers = providers_map  # nombre -> 'superhero' | 'quantum'

        if self.estrategias_rapinaire:
            # Calcular fila de inicio tras Candle Strategies
            base_after_fx = (len(estrategias_fx) + 3) if estrategias_fx else 0
            base_after_candle = base_after_fx
            if self.estrategias_candle:
                base_after_candle = base_after_fx + 3 + len(self.estrategias_candle)

            start_row_r = base_after_candle

            lbl_rap = ttk.Label(self.scrollable_frame, text="Rapiñaire Strategies",
                                 font=("Arial", 10, "bold"), anchor="w")
            lbl_rap.grid(row=start_row_r, column=0, columnspan=3, sticky="w", pady=(20, 10))

            # Botones seleccionar/deseleccionar (centrados)
            btn_rap_frame = tk.Frame(self.scrollable_frame)
            btn_rap_frame.grid(row=start_row_r + 1, column=0, columnspan=7, pady=(0, 5))
            btn_rap_sel = ttk.Button(
                btn_rap_frame,
                text="Seleccionar todos",
                command=lambda: self._set_group("rapinaire", 1),
                width=18
            )
            btn_rap_desel = ttk.Button(
                btn_rap_frame,
                text="Deseleccionar todos",
                command=lambda: self._set_group("rapinaire", 0),
                width=20
            )
            btn_rap_sel.pack(side="left", padx=5)
            btn_rap_desel.pack(side="left", padx=5)

            # Encabezado
            ttk.Label(self.scrollable_frame, text="Estrategia", width=20, anchor="w").grid(row=start_row_r+2, column=0, padx=5)
            ttk.Label(self.scrollable_frame, text="Origen", width=15, anchor="w").grid(row=start_row_r+2, column=1, padx=5)

            # Listado de estrategias Rapiñaire
            for idx, nombre in enumerate(self.estrategias_rapinaire, start=start_row_r+3):
                var_check = tk.IntVar()
                display_name = nombre.replace('_', ' ').capitalize()
                chk = tk.Checkbutton(self.scrollable_frame, text=display_name, variable=var_check,
                                     anchor="w", width=20)
                chk.grid(row=idx, column=0, sticky="w", padx=5, pady=2)

                origen = 'Superhero' if self.rapinaire_providers.get(nombre) == 'superhero' else 'Quantum'
                ttk.Label(self.scrollable_frame, text=origen, anchor="w").grid(row=idx, column=1, padx=5, sticky="w")

                self.controls[nombre] = {
                    "selected": var_check,
                    "tipo": "rapinaire",
                    "provider": self.rapinaire_providers.get(nombre)
                }

        # ---------------- CHECKBOXES DE OPCIONES ----------------
        # Calcular la fila donde colocar los checkboxes
        base_row = 0
        if estrategias_fx:
            # Filas usadas por Forex: título(0), botones(1), header(2), items(3..len+2)
            base_row = max(base_row, 3 + len(estrategias_fx))
        if self.estrategias_candle:
            # Inicio Candle en len_fx+3, usa: título, botones, header, items
            base_row = max(base_row, (len(estrategias_fx) + 3 if estrategias_fx else 0) + 3 + len(self.estrategias_candle))
        if getattr(self, 'estrategias_rapinaire', None):
            # Inicio Rapiñaire tras Candle, usa: título, botones, header, items
            base_after_fx = (len(estrategias_fx) + 3) if estrategias_fx else 0
            base_after_candle = base_after_fx + (3 + len(self.estrategias_candle)) if self.estrategias_candle else base_after_fx
            base_row = max(base_row, base_after_candle + 3 + len(self.estrategias_rapinaire))

        options_row = base_row + 2
        
        # Checkbox para mostrar detección de patrones
        self.var_mostrar_deteccion = tk.IntVar(value=1)  # Habilitado por defecto
        chk_deteccion = tk.Checkbutton(
            self.scrollable_frame, 
            text="Mostrar detección de patrones", 
            variable=self.var_mostrar_deteccion,
            anchor="w"
        )
        chk_deteccion.grid(row=options_row, column=0, columnspan=3, sticky="w", padx=5, pady=(20, 5))
        
        # Checkbox para mostrar simulación
        self.var_mostrar_simulacion = tk.IntVar(value=1)  # Habilitado por defecto
        chk_simulacion = tk.Checkbutton(
            self.scrollable_frame, 
            text="Mostrar simulación con Risk Manager", 
            variable=self.var_mostrar_simulacion,
            anchor="w"
        )
        chk_simulacion.grid(row=options_row + 1, column=0, columnspan=3, sticky="w", padx=5, pady=5)

        # ---------------- CAMPO MAX ORDENES ----------------
        frame_max = tk.Frame(self)
        frame_max.pack(pady=5)
        ttk.Label(frame_max, text="Número máximo de órdenes:").pack(side="left", padx=5)
        self.max_orders_var = tk.StringVar(value="5")
        self.entry_max_orders = tk.Entry(frame_max, textvariable=self.max_orders_var, width=5)
        self.entry_max_orders.pack(side="left")

        # Barra de progreso (inicialmente oculta)
        self.progress_frame = tk.Frame(self, bg="white", relief="solid", bd=1)
        
        # Título de la barra de progreso
        self.progress_title = ttk.Label(self.progress_frame, text="Progreso de Simulación", 
                                       font=("Arial", 10, "bold"))
        self.progress_title.pack(pady=(10, 5))
        
        # Barra de progreso más visible
        self.progress = ttk.Progressbar(self.progress_frame, orient="horizontal", 
                                       mode="determinate", length=450, style="TProgressbar")
        self.progress.pack(fill="x", padx=15, pady=5)
        
        # Etiqueta de porcentaje más prominente
        self.progress_label = ttk.Label(self.progress_frame, text="0%", 
                                       font=("Arial", 11, "bold"))
        self.progress_label.pack(pady=(5, 10))
        
        # Botones Cancelar y Aceptar
        self.frame_btn = tk.Frame(self)
        self.frame_btn.pack(pady=10)
        self.btn_cancelar = ttk.Button(self.frame_btn, text="Cancelar", command=self.destroy)
        self.btn_cancelar.pack(side="left", padx=10)
        self.btn_aceptar = ttk.Button(self.frame_btn, text="Aceptar", command=self._aceptar)
        self.btn_aceptar.pack(side="left", padx=10)
        
        # Variables para el threading
        self.simulation_thread = None
        self.is_running = False

    def _aceptar(self):
        """Iniciar simulación continua de estrategias"""
        seleccion = {}
        for nombre, ctrl in self.controls.items():
            if ctrl["selected"].get():
                if ctrl["tipo"] == "forex":
                    # Para Forex Strategies: incluir parámetros de riesgo
                    try:
                        riesgo = float(ctrl["riesgo"].get()) / 100  # convertir % a fracción
                        rr = float(ctrl["rr"].get())
                    except ValueError:
                        continue
                    seleccion[nombre] = {"riesgo": riesgo, "rr": rr, "tipo": "forex"}
                else:
                    # Para Candle Strategies: incluir configuración si es Custom
                    if ctrl["tipo"] == "candle":
                        try:
                            if ctrl.get("config_type") and ctrl["config_type"].get() == "Custom":
                                config = ctrl.get("custom_config") or self._get_default_candle_config(nombre)
                                def on_save(config_dict):
                                    try:
                                        ctrl["custom_config"] = config_dict
                                        # Log de verificación de guardado
                                        self._log_to_parent(f"Configuración guardada para {nombre}: {list(config_dict.keys())}", 'white')
                                    except Exception:
                                        pass
                        except Exception:
                            config = None
                        seleccion[nombre] = {"tipo": "candle", "config": config}
                    elif ctrl["tipo"] == "rapinaire":
                        # Para Rapiñaire Strategies no hay configuración adicional por ahora
                        seleccion[nombre] = {"tipo": "rapinaire", "provider": ctrl.get("provider")}
        
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione al menos una estrategia")
            return
        
        # Obtener datos del gui_parent
        if not hasattr(self.gui_parent, 'df_actual'):
            messagebox.showerror("Error", "La GUI principal no tiene atributo df_actual")
            return
        
        if self.gui_parent.df_actual is None:
            messagebox.showerror("Error", "No hay datos cargados para simular. Cargue primero un archivo CSV.")
            return
        
        if len(self.gui_parent.df_actual) == 0:
            messagebox.showerror("Error", "Los datos están vacíos. Cargue un archivo CSV válido.")
            return
        
        # Añadir max_orders y opciones de visualización al resultado
        try:
            max_orders = int(self.max_orders_var.get())
        except ValueError:
            max_orders = 5  # valor por defecto en caso de error

        opciones = {
            "mostrar_deteccion": bool(self.var_mostrar_deteccion.get()),
            "mostrar_simulacion": bool(self.var_mostrar_simulacion.get())
        }

        # Mostrar barra de progreso ANTES de los botones para mejor visibilidad
        self.progress_frame.pack(before=self.frame_btn, pady=15, padx=10, fill="x")
        self.progress.config(maximum=100, value=0)
        self.progress_label.config(text="Iniciando simulación... (0.0%)", foreground="blue")
        
        # Deshabilitar botones
        self.btn_aceptar.config(state="disabled")
        self.btn_cancelar.config(text="Cancelar", command=self._cancel_simulation)
        
        # Forzar múltiples actualizaciones para garantizar visibilidad
        self.progress_frame.update_idletasks()
        self.progress_frame.update()
        self.update_idletasks()
        self.update()
        
        # Redimensionar ventana si es necesario
        self.geometry("")
        
        # Pausa más larga para asegurar visibilidad completa
        import time
        time.sleep(0.2)
        
        # Iniciar simulación en hilo separado
        self.is_running = True
        self.simulation_thread = threading.Thread(
            target=self._run_continuous_simulation,
            args=(seleccion, max_orders, opciones),
            daemon=True
        )
        self.simulation_thread.start()

    def _cancel_simulation(self):
        """Cancelar la simulación en curso"""
        self.is_running = False
        if self.simulation_thread and self.simulation_thread.is_alive():
            # Esperar un poco para que el hilo termine
            self.after(100, self._check_thread_finished)
        else:
            self.destroy()

    def _check_thread_finished(self):
        """Verificar si el hilo ha terminado"""
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.after(100, self._check_thread_finished)
        else:
            self.destroy()

    def _update_progress(self, value, text=""):
        """Actualizar la barra de progreso desde el hilo de simulación"""
        def update():
            try:
                if hasattr(self, 'progress') and self.progress.winfo_exists():
                    # Asegurar que el frame esté visible
                    if not self.progress_frame.winfo_viewable():
                        self.progress_frame.pack(before=self.frame_btn, pady=15, padx=10, fill="x")
                    
                    self.progress['value'] = value
                    
                    # Formatear el texto con porcentaje más visible
                    if text:
                        display_text = f"{text} ({value:.1f}%)"
                    else:
                        display_text = f"Progreso: {value:.1f}%"
                    
                    # Cambiar color según el progreso
                    if value < 30:
                        color = "blue"
                    elif value < 70:
                        color = "orange"
                    else:
                        color = "green"
                    
                    self.progress_label.config(text=display_text, foreground=color)
                    
                    # Forzar actualización visual agresiva
                    try:
                        self.progress_frame.update_idletasks()
                        self.progress_frame.update()
                        self.update_idletasks()
                        self.update()
                        # Forzar repaint de la ventana
                        self.wm_attributes('-topmost', True)
                        self.wm_attributes('-topmost', False)
                    except Exception:
                        pass
            except Exception:
                pass
        
        self.after(0, update)

    def _run_continuous_simulation(self, seleccion, max_orders, opciones):
        """Ejecutar simulación continua de estrategias en hilo separado"""
        try:
            # Obtener datos
            df = self.gui_parent.df_actual.copy()
            
            # Configurar Risk Manager
            capital_inicial = getattr(self.gui_parent, 'dinero_ficticio', 10000)
            try:
                capital_inicial = float(capital_inicial)
            except (ValueError, TypeError):
                capital_inicial = 10000
            
            if capital_inicial <= 100:
                capital_inicial = 10000
            
            risk_manager = RiskManager(capital_inicial=capital_inicial, max_operaciones_activas=max_orders)
            risk_integration = RiskManagerIntegration(risk_manager)
            risk_manager.reset()

            # Log inicio
            self._log_to_parent("============================================================", 'cyan')
            self._log_to_parent("INICIANDO SIMULACIÓN CONTINUA DE ESTRATEGIAS", 'cyan')
            self._log_to_parent("============================================================", 'cyan')
            self._log_to_parent(f"Capital inicial: ${capital_inicial:,.2f}", 'white')
            self._log_to_parent(f"Estrategias seleccionadas: {len(seleccion)}", 'white')
            self._log_to_parent(f"Máximo de operaciones simultáneas: {max_orders}", 'white')

            # Mostrar progreso inicial inmediatamente
            self._update_progress(5, "Iniciando simulación...")
            
            # Pre-calcular todas las estrategias
            self._update_progress(10, "Pre-calculando estrategias...")
            
            forex_signals = {}
            candle_signals = {}
            rapinaire_signals = {}
            
            # Pre-calcular estrategias Forex
            forex_strategies = ForexStrategies(df)
            for i, (nombre, config) in enumerate([item for item in seleccion.items() if item[1]["tipo"] == "forex"]):
                if not self.is_running:
                    return
                    
                try:
                    strategy_method = getattr(forex_strategies, nombre, None)
                    if strategy_method and callable(strategy_method):
                        df_result = strategy_method()
                        if 'ExecSignal' in df_result.columns:
                            forex_signals[nombre] = {
                                'signals': df_result['ExecSignal'].fillna(0),
                                'config': config
                            }
                        
                        progress = 10 + (i + 1) / len([item for item in seleccion.items() if item[1]["tipo"] == "forex"]) * 10
                        self._update_progress(progress, f"Pre-calculando Forex: {nombre}")
                        
                except Exception as e:
                    self._log_to_parent(f"Error pre-calculando {nombre}: {str(e)}", 'red')
                    continue

            # Pre-calcular estrategias Candle
            candle_strategies = CandleStrategies(df)
            for i, (nombre, config) in enumerate([item for item in seleccion.items() if item[1]["tipo"] == "candle"]):
                if not self.is_running:
                    return
                    
                try:
                    strategy_method = getattr(candle_strategies, nombre, None)
                    if strategy_method and callable(strategy_method):
                        # Intentar pasar configuración si el método lo acepta
                        try:
                            df_result = strategy_method(config=config.get("config"))
                        except TypeError:
                            df_result = strategy_method()
                        if 'ExecSignal' in df_result.columns:
                            candle_signals[nombre] = {
                                'signals': df_result['ExecSignal'].fillna(0),
                                'config': config
                            }
                        
                        progress = 20 + (i + 1) / len([item for item in seleccion.items() if item[1]["tipo"] == "candle"]) * 10
                        self._update_progress(progress, f"Pre-calculando Candle: {nombre}")
                        
                except Exception as e:
                    self._log_to_parent(f"Error pre-calculando {nombre}: {str(e)}", 'red')
                    continue

            # Pre-calcular estrategias Rapiñaire (Superhero + Quantum)
            if any(cfg.get("tipo") == "rapinaire" for _, cfg in seleccion.items()):
                try:
                    super_strats = SuperheroStrategies(df)
                except Exception:
                    super_strats = None
                try:
                    quantum_strats = QuantumStrategies(df)
                except Exception:
                    quantum_strats = None

                rap_items = [item for item in seleccion.items() if item[1]["tipo"] == "rapinaire"]
                total_rap = len(rap_items) if rap_items else 1
                for i, (nombre, cfg) in enumerate(rap_items):
                    if not self.is_running:
                        return
                    try:
                        provider = cfg.get('provider') or self.rapinaire_providers.get(nombre)
                        target = super_strats if provider == 'superhero' else quantum_strats
                        strategy_method = getattr(target, nombre, None) if target is not None else None
                        if strategy_method and callable(strategy_method):
                            try:
                                df_result = strategy_method()
                            except TypeError:
                                df_result = strategy_method()
                            if 'ExecSignal' in df_result.columns:
                                rapinaire_signals[nombre] = {
                                    'signals': df_result['ExecSignal'].fillna(0),
                                    'config': cfg
                                }
                            progress = 30 + (i + 1) / total_rap * 5  # 30-35%
                            self._update_progress(progress, f"Pre-calculando Rapiñaire: {nombre}")
                    except Exception as e:
                        self._log_to_parent(f"Error pre-calculando {nombre}: {str(e)}", 'red')
                        continue

            self._update_progress(30, "Iniciando análisis de velas...")

            # Procesar cada vela
            total_rows = len(df)
            processed_rows = 0
            
            # Calcular ATR una sola vez
            if 'High' in df.columns and 'Low' in df.columns:
                atr_series = df['High'] - df['Low']
            else:
                atr_series = pd.Series([0.001] * len(df), index=df.index)
            
            for idx, row in df.iterrows():
                if not self.is_running:
                    return
                    
                processed_rows += 1
                current_price = float(row['Close'])
                current_atr = atr_series.loc[idx] if idx in atr_series.index else 0.001
                
                # Actualizar progreso cada 10 velas para máxima visibilidad
                if processed_rows % 10 == 0 or processed_rows == 1:
                    progress = 30 + (processed_rows / total_rows) * 65  # 30-95%
                    self._update_progress(progress, f"Procesando vela {processed_rows}/{total_rows}")
                
                # Actualizar progreso adicional cada 50 velas para mostrar actividad
                elif processed_rows % 50 == 0:
                    progress = 30 + (processed_rows / total_rows) * 65
                    self._update_progress(progress, f"Analizando estrategias... {processed_rows}/{total_rows}")
                
                # Verificar cierres automáticos (SL/TP)
                operaciones_cerradas = risk_manager.verificar_cierre_operaciones(current_price, idx)
                for op_cerrada in operaciones_cerradas:
                    # Calcular el beneficio numérico de la operación cerrada
                    if op_cerrada.tipo == 'BUY':
                        beneficio = (op_cerrada.precio_cierre - op_cerrada.precio_apertura) * op_cerrada.lote_size
                    else:  # SELL
                        beneficio = (op_cerrada.precio_apertura - op_cerrada.precio_cierre) * op_cerrada.lote_size
                    
                    if beneficio > 0:
                        self._log_to_parent(f"CIERRE AUTOMÁTICO (TP): +${beneficio:.2f} | {op_cerrada.estrategia}", 'green')
                    else:
                        self._log_to_parent(f"CIERRE AUTOMÁTICO (SL): ${beneficio:.2f} | {op_cerrada.estrategia}", 'red')

                # Evaluar señales de estrategias Forex
                for strategy_name, strategy_data in forex_signals.items():
                    if idx not in strategy_data['signals'].index:
                        continue
                        
                    signal = strategy_data['signals'].loc[idx]
                    config = strategy_data['config']
                    
                    if signal == 1 and risk_manager.puede_abrir_operacion():
                        # Calcular SL y TP basado en configuración
                        rr_ratio = config.get('rr', 2)
                        sl_distance = current_atr * 1.5
                        tp_distance = sl_distance * rr_ratio
                        
                        operacion = risk_manager.abrir_operacion(
                            tipo='BUY',
                            precio=current_price,
                            timestamp=idx,
                            stop_loss=current_price - sl_distance,
                            take_profit=current_price + tp_distance,
                            riesgo_por_operacion=config.get('riesgo', 0.01),
                            estrategia=strategy_name
                        )
                        if operacion:
                            self._log_to_parent(f"FOREX BUY: ${current_price:.5f} | {strategy_name} | RR:{rr_ratio}", 'green')
                    
                    elif signal == -1 and risk_manager.puede_abrir_operacion():
                        rr_ratio = config.get('rr', 2)
                        sl_distance = current_atr * 1.5
                        tp_distance = sl_distance * rr_ratio
                        
                        operacion = risk_manager.abrir_operacion(
                            tipo='SELL',
                            precio=current_price,
                            timestamp=idx,
                            stop_loss=current_price + sl_distance,
                            take_profit=current_price - tp_distance,
                            riesgo_por_operacion=config.get('riesgo', 0.01),
                            estrategia=strategy_name
                        )
                        if operacion:
                            self._log_to_parent(f"FOREX SELL: ${current_price:.5f} | {strategy_name} | RR:{rr_ratio}", 'red')

                # Evaluar señales de estrategias Candle
                for strategy_name, strategy_data in candle_signals.items():
                    if idx not in strategy_data['signals'].index:
                        continue
                    
                    signal = strategy_data['signals'].loc[idx]
                    
                    if signal == 1 and risk_manager.puede_abrir_operacion():
                        operacion = risk_manager.abrir_operacion(
                            tipo='BUY',
                            precio=current_price,
                            timestamp=idx,
                            stop_loss=current_price - (current_atr * 1.5),
                            take_profit=current_price + (current_atr * 3.0),
                            riesgo_por_operacion=0.01,
                            estrategia=strategy_name
                        )
                        if operacion:
                            self._log_to_parent(f"CANDLE BUY: ${current_price:.5f} | {strategy_name}", 'green')
                    
                    elif signal == -1 and risk_manager.puede_abrir_operacion():
                        operacion = risk_manager.abrir_operacion(
                            tipo='SELL',
                            precio=current_price,
                            timestamp=idx,
                            stop_loss=current_price + (current_atr * 1.5),
                            take_profit=current_price - (current_atr * 3.0),
                            riesgo_por_operacion=0.01,
                            estrategia=strategy_name
                        )
                        if operacion:
                            self._log_to_parent(f"CANDLE SELL: ${current_price:.5f} | {strategy_name}", 'red')

                # Evaluar señales de estrategias Rapiñaire
                for strategy_name, strategy_data in rapinaire_signals.items():
                    if idx not in strategy_data['signals'].index:
                        continue
                    signal = strategy_data['signals'].loc[idx]
                    if signal == 1 and risk_manager.puede_abrir_operacion():
                        operacion = risk_manager.abrir_operacion(
                            tipo='BUY',
                            precio=current_price,
                            timestamp=idx,
                            stop_loss=current_price - (current_atr * 1.5),
                            take_profit=current_price + (current_atr * 3.0),
                            riesgo_por_operacion=0.01,
                            estrategia=strategy_name
                        )
                        if operacion:
                            self._log_to_parent(f"RAPIÑAIRE BUY: ${current_price:.5f} | {strategy_name}", 'green')
                    elif signal == -1 and risk_manager.puede_abrir_operacion():
                        operacion = risk_manager.abrir_operacion(
                            tipo='SELL',
                            precio=current_price,
                            timestamp=idx,
                            stop_loss=current_price + (current_atr * 1.5),
                            take_profit=current_price - (current_atr * 3.0),
                            riesgo_por_operacion=0.01,
                            estrategia=strategy_name
                        )
                        if operacion:
                            self._log_to_parent(f"RAPIÑAIRE SELL: ${current_price:.5f} | {strategy_name}", 'red')


            self._update_progress(95, "Cerrando operaciones finales...")

            # Cerrar operaciones restantes
            final_price = df.iloc[-1]['Close']
            for operacion in risk_manager.operaciones_activas[:]:
                if operacion.estado == 'ACTIVA':
                    beneficio = operacion.cerrar(final_price, len(df) - 1)
                    if beneficio > 0:
                        self._log_to_parent(f"CIERRE FINAL: +${beneficio:.2f} | {operacion.estrategia}", 'green')
                    else:
                        self._log_to_parent(f"CIERRE FINAL: ${beneficio:.2f} | {operacion.estrategia}", 'red')

                    risk_manager.operaciones_cerradas.append(operacion)
                    risk_manager.operaciones_activas.remove(operacion)

                    if beneficio > 0:
                        risk_manager.operaciones_ganadas += 1
                        risk_manager.ganancia_ganadoras_total += beneficio
                    else:
                        risk_manager.operaciones_perdidas += 1
                        risk_manager.perdida_perdedoras_total += abs(beneficio)

                    risk_manager.capital += beneficio

            # Mostrar estadísticas finales
            self._show_final_stats(risk_manager)

            # Actualizar interfaz principal
            self._update_parent_interface(risk_manager)

            self._update_progress(100, "Simulación completada")

            # Mostrar progreso completado por más tiempo
            self._update_progress(100, "¡Simulación completada exitosamente!")

            # Cerrar modal después de un delay más largo para ver el resultado
            self.after(3000, self.destroy)

        except Exception as e:
            self._log_to_parent(f"Error en simulación: {str(e)}", 'red')
            self._update_progress(100, f"Error: {str(e)}")
            self.after(3000, self.destroy)

    def _log_to_parent(self, message, color='white'):
        """Enviar log al gui_parent de forma thread-safe"""
        def log():
            if hasattr(self.gui_parent, 'log'):
                self.gui_parent.log(message, color=color)

        self.after(0, log)

    def _show_final_stats(self, risk_manager):
        """Mostrar estadísticas finales"""
        stats = risk_manager.obtener_estadisticas()

        self._log_to_parent("============================================================", 'cyan')
        self._log_to_parent("ESTADÍSTICAS FINALES DE SIMULACIÓN CONTINUA", 'cyan')
        self._log_to_parent("============================================================", 'cyan')
        self._log_to_parent(f"Capital final: ${stats['capital_final']:,.2f}", 'white')
        self._log_to_parent(f"Beneficio total: ${stats['beneficio_total']:,.2f}", 'green' if stats['beneficio_total'] > 0 else 'red')
        self._log_to_parent(f"Operaciones ganadas: {stats['operaciones_ganadas']} [${stats['ganancia_ganadoras_total']:,.2f}]", 'green')
        self._log_to_parent(f"Operaciones perdidas: {stats['operaciones_perdidas']} [${stats['perdida_perdedoras_total']:,.2f}]", 'red')
        self._log_to_parent(f"Win Rate: {stats['win_rate']:.1f}%", 'white')
        self._log_to_parent("============================================================", 'cyan')

    def _update_parent_interface(self, risk_manager):
        """Actualizar la interfaz del gui_parent con los resultados"""
        def update():
            if hasattr(self.gui_parent, 'dinero_ficticio'):
                self.gui_parent.dinero_ficticio = risk_manager.capital
            if hasattr(self.gui_parent, 'beneficios'):
                self.gui_parent.beneficios += risk_manager.ganancia_ganadoras_total
            if hasattr(self.gui_parent, 'perdidas'):
                self.gui_parent.perdidas += abs(risk_manager.perdida_perdedoras_total)

    # --- Mouse wheel support for scrolling ---
    def _bind_mousewheel(self):
        try:
            # Windows and MacOS
            self.bind_all("<MouseWheel>", self._on_mousewheel)
            # Linux (X11)
            self.bind_all("<Button-4>", self._on_mousewheel)
            self.bind_all("<Button-5>", self._on_mousewheel)
        except Exception:
            pass

    def _unbind_mousewheel(self):
        try:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        except Exception:
            pass

    def _on_mousewheel(self, event):
        try:
            if getattr(event, 'num', None) == 4 or getattr(event, 'delta', 0) > 0:
                self.canvas.yview_scroll(-1, "units")
            elif getattr(event, 'num', None) == 5 or getattr(event, 'delta', 0) < 0:
                self.canvas.yview_scroll(1, "units")
        except Exception:
            pass

    def _validate_two_decimals(self, proposed: str) -> bool:
        """Permitir vacío, dígitos enteros o decimales con hasta 2 lugares."""
        try:
            if proposed == "":
                return True
            # Permitir formato tipo: 0, 1, 10, 1., 1.0, 1.23
            return re.fullmatch(r"\d*(?:\.|\,)?\d{0,2}", proposed) is not None
        except Exception:
            return False

    def _toggle_group(self, tipo: str):
        """Selecciona todas o deselecciona todas las estrategias de un grupo.
        Si hay alguna desmarcada, selecciona todas. Si todas están seleccionadas, desmarca todas.
        """
        try:
            estados = [
                ctrl["selected"].get()
                for ctrl in self.controls.values()
                if ctrl.get("tipo") == tipo
            ]
            if not estados:
                return
            target = 1 if any(v == 0 for v in estados) else 0
            for ctrl in self.controls.values():
                if ctrl.get("tipo") == tipo:
                    ctrl["selected"].set(target)
        except Exception:
            pass

    def _set_group(self, tipo: str, value: int):
        """Marca (1) o desmarca (0) todas las estrategias de un grupo."""
        try:
            for ctrl in self.controls.values():
                if ctrl.get("tipo") == tipo:
                    ctrl["selected"].set(1 if value else 0)
        except Exception:
            pass

    # ---------- Helpers de configuración Candle ----------
    def _config_dir(self) -> str:
        try:
            return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        except Exception:
            return 'config'

    def _strategy_config_paths(self, strategy_name: str) -> list[str]:
        """Posibles rutas de archivo JSON para una estrategia Candle.
        Intenta con alias visible y con nombre real resuelto.
        """
        try:
            resolved = resolve_strategy_name(strategy_name, 'candle')
        except Exception:
            resolved = strategy_name
        fname_alias = f"candle_{strategy_name}.json"
        fname_resolved = f"candle_{resolved}.json"
        cfg_dir = self._config_dir()
        return [os.path.join(cfg_dir, fname_alias), os.path.join(cfg_dir, fname_resolved)]

    def _config_exists_for_strategy(self, strategy_name: str) -> bool:
        for p in self._strategy_config_paths(strategy_name):
            try:
                if os.path.isfile(p):
                    return True
            except Exception:
                continue
        return False

    def _can_load_all_candle_configs(self, strategies: list[str]) -> bool:
        try:
            return all(self._config_exists_for_strategy(n) for n in strategies)
        except Exception:
            return False

    def _load_config_from_file(self, strategy_name: str) -> dict | None:
        for p in self._strategy_config_paths(strategy_name):
            try:
                if os.path.isfile(p):
                    with open(p, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            return data
            except Exception:
                continue
        return None

    def _load_all_candle_configs(self):
        """Carga todas las configuraciones de config/ y pone los combos en Custom.
        Si alguna falta, no hace nada y deja el botón deshabilitado.
        """
        try:
            if not self._can_load_all_candle_configs(self.estrategias_candle):
                # Revalidar estado del botón
                try:
                    self.btn_load_candle_configs.config(state='disabled')
                except Exception:
                    pass
                self._log_to_parent("No se pueden cargar todas las configuraciones: faltan archivos.", 'yellow')
                return

            loaded_count = 0
            for nombre in self.estrategias_candle:
                ctrl = self.controls.get(nombre)
                if not ctrl:
                    continue
                cfg = self._load_config_from_file(nombre)
                if cfg is None:
                    continue
                # Asignar y cambiar a Custom
                ctrl['custom_config'] = cfg
                if ctrl.get('config_type') is not None:
                    ctrl['config_type'].set('Custom')
                if ctrl.get('config_button') is not None:
                    ctrl['config_button'].config(state='normal')
                loaded_count += 1

            # Log y feedback
            self._log_to_parent(f"Configuraciones cargadas: {loaded_count}/{len(self.estrategias_candle)}", 'white')
        except Exception as e:
            self._log_to_parent(f"Error cargando configuraciones: {e}", 'red')

    def _open_candle_config(self, strategy_name: str):
        """Abre modal de configuración personalizada para una estrategia de velas."""
        try:
            ctrl = self.controls.get(strategy_name)
            if not ctrl:
                return

            # Posicionar a la derecha del modal principal
            self.update_idletasks()
            x = self.winfo_rootx() + self.winfo_width() + 10
            y = self.winfo_rooty()

            current = ctrl.get("custom_config") or self._get_default_candle_config(strategy_name)

            def on_save(config_dict):
                try:
                    ctrl["custom_config"] = config_dict
                    # Log opcional de confirmación
                    if isinstance(config_dict, dict):
                        self._log_to_parent(f"Configuración guardada para {strategy_name}: {list(config_dict.keys())}")
                except Exception:
                    pass

            CandleConfigModal(self, strategy_name, current, on_save, x, y)
        except Exception as e:
            print(f"Error opening candle config modal for {strategy_name}: {e}")

    def _get_default_candle_config(self, strategy_name: str) -> dict:
        """Devuelve preset por tipo de estrategia según recomendaciones (igual que en Binance)."""
        try:
            name = resolve_strategy_name(strategy_name, "candle") if strategy_name else ""
        except Exception:
            name = strategy_name or ""

        reversal = {
            "hammer_reversal_strategy",
            "bullish_engulfing_strategy",
            "bearish_engulfing_strategy",
            "morning_star_strategy",
            "evening_star_strategy",
            "doji_reversal_strategy",
            "hanging_man_strategy",
            "bearish_engulfing_reversal",
            "bullish_engulfing_reversal",
            "doji_indecision",
            "evening_star_swing",
            "hammer_reversal",
            "hanging_man_reversal",
            "morning_star_swing",
        }
        trend = {
            "three_white_soldiers_strategy",
            "three_black_crows_strategy",
            "marubozu_trend",
            "filter_with_trend",
            "three_black_crows",
            "three_white_soldiers",
        }
        scalping = {"scalping_reversal", "scalping_reversal_strategy"}
        swing_cons = {"conservative_swing_strategy"}
        sltp = {"stop_loss_take_profit"}
        combined = {"multi_pattern_strategy", "swing_trading", "swing_trading_strategy"}

        def cfg(use_ts, sl, tp, ts_mult=None, use_sc=True, use_sl=True, use_tp=True, use_pr=False):
            return {
                "use_signal_change": use_sc,
                "use_stop_loss": use_sl,
                "use_take_profit": use_tp,
                "use_trailing_stop": use_ts,
                "use_pattern_reversal": use_pr,
                "atr_sl_multiplier": sl,
                "atr_tp_multiplier": tp,
                "atr_trailing_multiplier": ts_mult if ts_mult is not None else 1.5,
            }

        if name in reversal:
            return cfg(use_ts=False, sl=1.5, tp=3.0, ts_mult=1.5)
        if name in trend:
            return cfg(use_ts=True, sl=2.0, tp=4.0, ts_mult=2.0)
        if name in scalping:
            return cfg(use_ts=True, sl=1.0, tp=2.0, ts_mult=1.5)
        if name in swing_cons:
            return cfg(use_ts=False, sl=2.5, tp=4.0, ts_mult=2.0)
        if name in sltp:
            return cfg(use_ts=False, sl=1.5, tp=3.0, ts_mult=1.5, use_sc=True)
        if name in combined:
            return cfg(use_ts=False, sl=1.5, tp=3.0, ts_mult=1.5)

        return cfg(use_ts=False, sl=1.5, tp=3.0, ts_mult=1.5)

    def _discover_candle_strategies(self):
        """Descubre TODAS las estrategias públicas de CandleStrategies (métodos callables)."""
        try:
            df_dummy = pd.DataFrame({'Open': [], 'High': [], 'Low': [], 'Close': []})
            temp = CandleStrategies(df_dummy)
        except Exception:
            temp = None

        strategies = []
        target = temp if temp is not None else CandleStrategies
        for name in dir(target):
            if name.startswith('_'):
                continue
            if name in ['data', 'patterns', 'add_indicators', '_apply_exit_logic', '_safe_join']:
                continue
            try:
                member = getattr(target, name)
            except Exception:
                continue
            if callable(member):
                strategies.append(name)
        try:
            self._log_to_parent(f"[DEBUG] Descubiertas Candle: {len(set(strategies))}", 'cyan')
        except Exception:
            pass
        return sorted(set(strategies))

    def _discover_rapinaire_strategies(self):
        """Descubre estrategias públicas de SuperheroStrategies y QuantumStrategies."""
        strategies = []
        providers = {}
        try:
            df_dummy = pd.DataFrame({'Open': [], 'High': [], 'Low': [], 'Close': [], 'Volume': []})
        except Exception:
            df_dummy = pd.DataFrame({'Open': [], 'High': [], 'Low': [], 'Close': []})

        # SuperheroStrategies
        try:
            super_inst = SuperheroStrategies(df_dummy)
        except Exception:
            super_inst = None
        target = super_inst if super_inst is not None else SuperheroStrategies
        for name in dir(target):
            if name.startswith('_'):
                continue
            if name in ['data', '_calculate_indicators', '_apply_quantum_exit_logic']:
                continue
            try:
                member = getattr(target, name)
            except Exception:
                continue
            if callable(member):
                strategies.append(name)
                providers[name] = 'superhero'

        # QuantumStrategies
        try:
            quant_inst = QuantumStrategies(df_dummy)
        except Exception:
            quant_inst = None
        target = quant_inst if quant_inst is not None else QuantumStrategies
        for name in dir(target):
            if name.startswith('_'):
                continue
            if name in ['data', '_calculate_indicators', '_apply_quantum_exit_logic', 'test_quantum_strategies']:
                continue
            try:
                member = getattr(target, name)
            except Exception:
                continue
            if callable(member):
                strategies.append(name)
                providers[name] = 'quantum'

        # Resolver duplicados manteniendo primer proveedor encontrado
        unique_strats = []
        seen = set()
        for n in strategies:
            if n not in seen:
                unique_strats.append(n)
                seen.add(n)
        try:
            self._log_to_parent(f"[DEBUG] Descubiertas Rapiñaire: {len(unique_strats)}", 'cyan')
        except Exception:
            pass
        return unique_strats, providers