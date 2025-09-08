# trading_view/binance_modal.py

import tkinter as tk
from tkinter import ttk
import re
import os
import json
import inspect
import pandas as pd
from strategies.strategy_utils import resolve_strategy_name
from strategies.candle_strategies import CandleStrategies

class BinanceSimulationModal(tk.Toplevel):
    def __init__(self, parent, estrategias_fx, estrategias_candle, callback, patrones_list=None):
        super().__init__(parent)
        self.parent = parent
        self.callback = callback
        self.title("Seleccionar Estrategias Candle Streamer")
        self.resizable(False, False)
        self.grab_set()  # modal

        # Altura fija de la zona de estrategias (scrollable)
        list_area_height = 400

        # Centrar ventana sobre el padre
        self.update_idletasks()
        w = 600
        # Altura total del modal: área de lista (400) + controles inferiores
        h_total = 550
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h_total) // 2
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

        # Descubrir dinámicamente estrategias Candle y fusionar con las recibidas
        try:
            discovered_candle = self._discover_candle_strategies()
        except Exception:
            discovered_candle = []
        try:
            provided_candle = list(estrategias_candle or [])
        except Exception:
            provided_candle = []
        # Unir y ordenar únicas
        self.estrategias_candle = sorted(set(provided_candle + discovered_candle))

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
                
                # Aplicar etiqueta de riesgo según el método real
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
            # Botón para cargar configuraciones guardadas y aplicar a las estrategias
            btn_candle_cargar = ttk.Button(
                btn_candle_frame,
                text="Cargar configuraciones",
                command=self._load_all_candle_configs,
                width=22
            )
            btn_candle_cargar.pack(side="left", padx=5)

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

        # ---------------- CHECKBOXES DE OPCIONES ----------------
        # Calcular la fila donde colocar los checkboxes
        base_row = 0
        if estrategias_fx:
            # Filas usadas por Forex: título(0), botones(1), header(2), items(3..len+2)
            base_row = max(base_row, 3 + len(estrategias_fx))
        if self.estrategias_candle:
            # Inicio Candle en len_fx+3, usa: título, botones, header, items
            base_row = max(base_row, (len(estrategias_fx) + 3 if estrategias_fx else 0) + 3 + len(self.estrategias_candle))
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

        # ---------------- CAMPOS DE CONFIGURACIÓN ----------------
        frame_config = tk.Frame(self)
        frame_config.pack(pady=5, fill='x')
        
        # Frame para agrupar los campos de configuración verticalmente (centrado)
        config_fields = tk.Frame(frame_config)
        config_fields.pack(pady=0, expand=True)
        
        # Frame para velas de espera
        frame_wait = tk.Frame(config_fields)
        frame_wait.pack(pady=2)
        ttk.Label(frame_wait, text="Velas a esperar:").pack(side="left", padx=6)
        self.wait_candles_var = tk.StringVar(value="20")
        vcmd = (self.register(self._validate_int), '%P')
        self.entry_wait_candles = tk.Entry(frame_wait, textvariable=self.wait_candles_var, width=5, 
                                         validate="key", validatecommand=vcmd)
        self.entry_wait_candles.pack(side="left", padx=2)
        
        # Frame para máximo de órdenes
        frame_max = tk.Frame(config_fields)
        frame_max.pack(pady=2)
        ttk.Label(frame_max, text="Máx. órdenes:").pack(side="left", padx=6)
        self.max_orders_var = tk.StringVar(value="5")
        self.entry_max_orders = tk.Entry(frame_max, textvariable=self.max_orders_var, width=5, 
                                       validate="key", validatecommand=vcmd)
        self.entry_max_orders.pack(side="left", padx=2)

        # Botones Cancelar y Aceptar
        frame_btn = tk.Frame(self)
        frame_btn.pack(pady=10)
        btn_cancelar = ttk.Button(frame_btn, text="Cancelar", command=self.destroy)
        btn_cancelar.pack(side="left", padx=10)
        btn_aceptar = ttk.Button(frame_btn, text="Aceptar", command=self._aceptar)
        btn_aceptar.pack(side="left", padx=10)

    def _validate_int(self, value: str) -> bool:
        """Valida que el valor sea un número entero positivo o vacío."""
        if value == "":
            return True
        try:
            return int(value) >= 0
        except ValueError:
            return False
            
    def _aceptar(self):
        try:
            # Get selected strategies and patterns
            selected_forex = []
            selected_candle = []
            
            for name, ctrl in self.controls.items():
                if ctrl["selected"].get() == 1:
                    if ctrl["tipo"] == "forex":
                        # Validate forex strategy has required textboxes filled
                        risk_value = ctrl["riesgo"].get()
                        rr_value = ctrl["rr"].get()
                        
                        if not risk_value or not rr_value:
                            tk.messagebox.showerror(
                                "Error de Validación",
                                f"La estrategia forex '{name}' debe tener los campos 'Riesgo %' y 'RR' completados."
                            )
                            return
                        
                        try:
                            risk = float(risk_value)
                            rr = float(rr_value)
                            if risk <= 0 or rr <= 0:
                                tk.messagebox.showerror(
                                    "Error de Validación",
                                    f"La estrategia forex '{name}' debe tener valores positivos en 'Riesgo %' y 'RR'."
                                )
                                return
                        except ValueError:
                            tk.messagebox.showerror(
                                "Error de Validación",
                                f"La estrategia forex '{name}' debe tener valores numéricos válidos en 'Riesgo %' y 'RR'."
                            )
                            return
                        
                        selected_forex.append({
                            'name': name,
                            'risk': risk / 100.0,  # Convert percentage to decimal
                            'rr_ratio': rr
                        })
                    elif ctrl["tipo"] == "candle":
                        # Handle custom configuration for candle strategies
                        config = None
                        try:
                            if ctrl.get("config_type") and ctrl["config_type"].get() == "Custom":
                                # Use custom config if available, else preset for that strategy
                                config = ctrl.get("custom_config") or self._get_default_candle_config(name)
                            else:
                                config = None  # Default => None
                        except Exception:
                            config = None
                        
                        selected_candle.append({
                            'name': name,
                            'config': config
                        })
            
            # Validate at least one strategy is selected
            if not selected_forex and not selected_candle:
                tk.messagebox.showerror(
                    "Error de Validación",
                    "Debe seleccionar al menos una estrategia (forex o candle) para iniciar la simulación."
                )
                return
            
            # Get wait candles and max orders
            try:
                wait_candles = int(self.wait_candles_var.get() or 0)
                if wait_candles <= 0:
                    tk.messagebox.showerror(
                        "Error de Validación",
                        "El campo 'Velas a esperar' debe ser mayor que 0."
                    )
                    return
            except (ValueError, AttributeError):
                tk.messagebox.showerror(
                    "Error de Validación",
                    "El campo 'Velas a esperar' debe contener un número válido mayor que 0."
                )
                return
                
            try:
                max_orders = int(self.max_orders_var.get() or 0)
                if max_orders <= 0:
                    tk.messagebox.showerror(
                        "Error de Validación",
                        "El campo 'Máximo de órdenes' debe ser mayor que 0."
                    )
                    return
            except (ValueError, AttributeError):
                tk.messagebox.showerror(
                    "Error de Validación",
                    "El campo 'Máximo de órdenes' debe contener un número válido mayor que 0."
                )
                return
            
            # Get display options
            show_detection = bool(self.var_mostrar_deteccion.get())
            show_simulation = bool(self.var_mostrar_simulacion.get())
            
            # Prepare simulation config
            config = {
                'forex_strategies': selected_forex,
                'candle_strategies': selected_candle,
                'patterns': [],  # Patterns are now handled by CandleStrategies
                'wait_candles': wait_candles,
                'max_orders': max_orders,
                'show_detection': show_detection,
                'show_simulation': show_simulation,
                'candles_elapsed': 0,  # Track number of candles processed
                'active_orders': []     # Track active orders
            }
            
            # Pass config back to parent and close modal
            if self.callback:
                self.callback(config)
                
        except Exception as e:
            print(f"Error starting simulation: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.destroy()
        
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

    def _validate_float(self, proposed: str) -> bool:
        """Valida float con punto. Permite vacío."""
        try:
            if proposed == "":
                return True
            return re.fullmatch(r"^-?\d*(?:\.\d*)?$", proposed) is not None
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
                except Exception:
                    pass

            CandleConfigModal(self, strategy_name, current, on_save, x, y)
        except Exception as e:
            print(f"Error opening candle config modal for {strategy_name}: {e}")

    def _load_all_candle_configs(self):
        """Carga los archivos de configuración existentes para estrategias Candle y
        cambia el combo de cada estrategia a 'Custom'."""
        try:
            # Localizar carpeta config a nivel de proyecto
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(project_root, 'config')
        except Exception:
            config_dir = None

        if not config_dir or not os.path.isdir(config_dir):
            return

        loaded_count = 0
        for name in self.estrategias_candle:
            try:
                resolved = resolve_strategy_name(name, "candle") if name else ""

                cfg_path = os.path.join(config_dir, f"candle_{resolved}.json")
                if not os.path.exists(cfg_path):
                    continue

                # Leer JSON de configuración
                try:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                except Exception:
                    continue

                ctrl = self.controls.get(name)
                if not ctrl or ctrl.get("tipo") != "candle":
                    continue

                try:
                    ctrl["custom_config"] = cfg
                    # Cambiar el combo a 'Custom' y habilitar botón de configuración
                    if ctrl.get("config_type"):
                        ctrl["config_type"].set("Custom")
                    if ctrl.get("config_button"):
                        ctrl["config_button"].config(state="normal")
                    loaded_count += 1
                except Exception:
                    continue
            except Exception:
                # Si algo falla al procesar una estrategia, continuar con la siguiente
                continue
        # Opcional: imprimir resumen en consola
        try:
            print(f"Cargar configuraciones: {loaded_count} estrategia(s) actualizada(s).")
        except Exception:
            pass

    def _get_default_candle_config(self, strategy_name: str) -> dict:
        """Devuelve preset por tipo de estrategia según recomendaciones."""
        name = resolve_strategy_name(strategy_name, "candle") if strategy_name else ""

        # Categorías
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
            "morning_star_swing"
        }
        trend = {
            "three_white_soldiers_strategy",
            "three_black_crows_strategy",
            "marubozu_trend",
            "filter_with_trend",
            "three_black_crows",
            "three_white_soldiers"
        }
        scalping = {"scalping_reversal", "scalping_reversal_strategy"}
        swing_cons = {"conservative_swing_strategy"}
        sltp = {"stop_loss_take_profit"}
        combined = {"multi_pattern_strategy", "swing_trading", "swing_trading_strategy"}

        # Presets
        def cfg(use_ts, sl, tp, ts_mult=None, use_sc=True, use_sl=True, use_tp=True, use_pr=False):
            d = {
                "use_signal_change": use_sc,
                "use_stop_loss": use_sl,
                "use_take_profit": use_tp,
                "use_trailing_stop": use_ts,
                "use_pattern_reversal": use_pr,
                "atr_sl_multiplier": sl,
                "atr_tp_multiplier": tp,
                "atr_trailing_multiplier": ts_mult if ts_mult is not None else 1.5
            }
            return d

        if name in reversal:
            # Reversión: trailing opcional; por defecto desactivado
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

        # Default fallback
        return cfg(use_ts=False, sl=1.5, tp=3.0, ts_mult=1.5)

    def _discover_candle_strategies(self):
        """Descubre estrategias públicas de CandleStrategies con parámetro 'config'."""
        try:
            # Instancia dummy para inspección (sin datos reales)
            df_dummy = pd.DataFrame({
                'Open': [], 'High': [], 'Low': [], 'Close': []
            })
            temp = CandleStrategies(df_dummy)
        except Exception:
            temp = None

        strategies = []
        target = temp if temp is not None else CandleStrategies
        for name in dir(target):
            if name.startswith('_'):
                continue
            if name in ['data', 'patterns', 'add_indicators']:
                continue
            try:
                member = getattr(target, name)
            except Exception:
                continue
            if callable(member):
                # Filtrar por métodos que acepten 'config'
                try:
                    sig = inspect.signature(member)
                    if 'config' in sig.parameters:
                        strategies.append(name)
                except Exception:
                    # Si no se puede inspeccionar, incluirlo por si es estrategia
                    strategies.append(name)
        return sorted(set(strategies))


class CandleConfigModal(tk.Toplevel):
    """Modal de configuración personalizada para una estrategia de velas."""
    def __init__(self, parent, strategy_name: str, current_config: dict, on_save, pos_x: int, pos_y: int):
        super().__init__(parent)
        self.parent = parent
        self.strategy_name = strategy_name
        self.on_save = on_save
        self.title("Configuración personalizada")
        self.resizable(False, False)
        self.grab_set()

        # Posicionar
        self.geometry(f"360x440+{pos_x}+{pos_y}")

        # Título
        ttk.Label(self, text=f"{strategy_name.replace('_',' ').capitalize()}", font=("Arial", 10, "bold")).pack(pady=(8, 4))

        # Área scrollable para el contenido
        scroll_wrap = tk.Frame(self)
        scroll_wrap.pack(fill="both", expand=True, padx=10, pady=4)
        canvas = tk.Canvas(scroll_wrap, highlightthickness=0)
        vscroll = ttk.Scrollbar(scroll_wrap, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas)
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        # Activar/desactivar scroll con rueda al entrar/salir
        content.bind("<Enter>", lambda e: self._bind_mousewheel(canvas))
        content.bind("<Leave>", lambda e: self._unbind_mousewheel())

        # Contenedor centrado: 'inner_container' estará centrado dentro de 'content'
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(2, weight=1)
        inner_container = tk.Frame(content)
        inner_container.grid(row=0, column=1, sticky="n", padx=12, pady=4)

        # Cargar config guardada si existe
        try:
            resolved = resolve_strategy_name(strategy_name, "candle") if strategy_name else strategy_name
        except Exception:
            resolved = strategy_name
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_dir = os.path.join(project_root, 'config')
            os.makedirs(self.config_dir, exist_ok=True)
            self.config_path = os.path.join(self.config_dir, f"candle_{resolved}.json")
        except Exception:
            self.config_dir = None
            self.config_path = None

        # Mezclar current_config con lo guardado previamente
        loaded_config = {}
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
            except Exception:
                loaded_config = {}
        # Merge: prioridad a lo cargado, luego a lo recibido
        base_config = dict(current_config or {})
        base_config.update(loaded_config or {})

        vcmd_float = (self.register(self._validate_float), '%P')

        # Campos booleanos con checkboxes exclusivos
        self.bool_fields = {}
        def add_bool(title, key, help_text=""):
            frame = tk.Frame(inner_container)
            frame.pack(fill="x", pady=4)
            ttk.Label(frame, text=title).pack(anchor="w")
            inner = tk.Frame(frame)
            inner.pack(fill="x")
            var_true = tk.IntVar(value=1 if base_config.get(key, False) else 0)
            var_false = tk.IntVar(value=0 if base_config.get(key, False) else 1)

            def on_true():
                if var_true.get():
                    var_false.set(0)
                else:
                    var_false.set(1)
            def on_false():
                if var_false.get():
                    var_true.set(0)
                else:
                    var_true.set(1)

            tk.Checkbutton(inner, text="True", variable=var_true, command=on_true).pack(side="left")
            tk.Checkbutton(inner, text="False", variable=var_false, command=on_false).pack(side="left", padx=8)
            if help_text:
                ttk.Label(frame, text=help_text, foreground="#666", font=("Arial", 8)).pack(anchor="w")
            self.bool_fields[key] = (var_true, var_false)

        # Campos numéricos
        self.num_fields = {}
        def add_num(title, key, help_text=""):
            frame = tk.Frame(inner_container)
            frame.pack(fill="x", pady=4)
            ttk.Label(frame, text=title).pack(anchor="w")
            inner = tk.Frame(frame)
            inner.pack(fill="x")
            var = tk.StringVar(value=str(base_config.get(key, "")))
            tk.Entry(inner, textvariable=var, width=10, validate="key", validatecommand=vcmd_float).pack(side="left")
            if help_text:
                ttk.Label(frame, text=help_text, foreground="#666", font=("Arial", 8)).pack(anchor="w")
            self.num_fields[key] = var

        # Añadir campos
        add_bool("Cambio de señal (use_signal_change)", "use_signal_change", "True para cerrar cuando aparezca señal opuesta.")
        add_bool("Stop Loss (use_stop_loss)", "use_stop_loss", "True para activar SL por ATR.")
        add_bool("Take Profit (use_take_profit)", "use_take_profit", "True para activar TP por ATR.")
        add_bool("Trailing Stop (use_trailing_stop)", "use_trailing_stop", "True si buscas proteger ganancias.")
        add_bool("Patrón reversión (use_pattern_reversal)", "use_pattern_reversal", "True para cerrar con patrón opuesto.")

        add_num("ATR SL multiplier (atr_sl_multiplier)", "atr_sl_multiplier", "Ej.: 1.5")
        add_num("ATR TP multiplier (atr_tp_multiplier)", "atr_tp_multiplier", "Ej.: 3.0")
        add_num("ATR trailing multiplier (atr_trailing_multiplier)", "atr_trailing_multiplier", "Ej.: 1.5")

        # Fila final: Guardar configuración
        save_row = tk.Frame(inner_container)
        save_row.pack(fill="x", pady=(10, 0))
        self.var_save_config = tk.IntVar(value=1)
        tk.Checkbutton(save_row, variable=self.var_save_config).pack(side="left")
        ttk.Label(save_row, text="Guardar configuración").pack(side="left", padx=6)

        # Botones de presets
        presets_row = tk.Frame(inner_container)
        presets_row.pack(fill="x", pady=(8, 0))
        ttk.Button(presets_row, text="Restaurar preset", command=self._restore_preset).pack(side="left")
        ttk.Button(presets_row, text="Cargar preset", command=self._load_saved_preset).pack(side="left", padx=8)

        # Botones
        btns = tk.Frame(self)
        btns.pack(pady=10)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left", padx=8)
        ttk.Button(btns, text="Aceptar", command=self._accept).pack(side="left", padx=8)

    def _validate_float(self, proposed: str) -> bool:
        try:
            if proposed == "":
                return True
            return re.fullmatch(r"^-?\d*(?:\.\d*)?$", proposed) is not None
        except Exception:
            return False

    # --- Mouse wheel support for scrolling inside config modal ---
    def _bind_mousewheel(self, target_canvas):
        try:
            self.unbind_all("<MouseWheel>")
            self.bind_all("<MouseWheel>", lambda e: target_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
            # Linux
            self.bind_all("<Button-4>", lambda e: target_canvas.yview_scroll(-1, "units"))
            self.bind_all("<Button-5>", lambda e: target_canvas.yview_scroll(1, "units"))
        except Exception:
            pass

    def _unbind_mousewheel(self):
        try:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        except Exception:
            pass

    def _accept(self):
        try:
            cfg = {}
            for key, (v_true, v_false) in self.bool_fields.items():
                cfg[key] = True if v_true.get() == 1 else False
            for key, var in self.num_fields.items():
                txt = var.get().strip()
                cfg[key] = float(txt) if txt not in ("", ".") else 0.0
            if callable(self.on_save):
                self.on_save(cfg)
            # Guardar en disco si corresponde
            try:
                if getattr(self, 'var_save_config', None) and self.var_save_config.get() == 1 and self.config_path:
                    os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                    with open(self.config_path, 'w', encoding='utf-8') as f:
                        json.dump(cfg, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Error saving strategy config to file: {e}")
        except Exception as e:
            print(f"Error saving candle config: {e}")
        finally:
            self.destroy()

    def _restore_preset(self):
        try:
            # Obtener preset recomendado desde el modal padre
            preset = {}
            try:
                if hasattr(self.parent, '_get_default_candle_config'):
                    preset = self.parent._get_default_candle_config(self.strategy_name) or {}
            except Exception:
                preset = {}
            self._apply_config_to_fields(preset)
        except Exception as e:
            print(f"Error restoring preset: {e}")

    def _load_saved_preset(self):
        try:
            if getattr(self, 'config_path', None) and os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._apply_config_to_fields(data)
            else:
                # Si no hay fichero, cargar el preset recomendado
                self._restore_preset()
        except Exception as e:
            print(f"Error loading saved preset: {e}")

    def _apply_config_to_fields(self, cfg: dict):
        try:
            cfg = cfg or {}
            # Booleans
            for key, (v_true, v_false) in self.bool_fields.items():
                val = bool(cfg.get(key, False))
                v_true.set(1 if val else 0)
                v_false.set(0 if val else 1)
            # Numerics
            for key, var in self.num_fields.items():
                if key in cfg and cfg.get(key) is not None:
                    var.set(str(cfg.get(key)))
        except Exception as e:
            print(f"Error applying config to fields: {e}")