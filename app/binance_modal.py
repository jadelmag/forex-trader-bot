# trading_view/binance_modal.py

import tkinter as tk
from tkinter import ttk
import re
from strategies.strategy_utils import resolve_strategy_name

class BinanceSimulationModal(tk.Toplevel):
    def __init__(self, parent, estrategias_fx, estrategias_candle, callback, patrones_list=None):
        super().__init__(parent)
        self.parent = parent
        self.callback = callback
        self.title("Seleccionar Estrategias")
        self.resizable(False, False)
        self.grab_set()  # modal


        # Altura fija de la zona de estrategias (scrollable)
        list_area_height = 400

        # Centrar ventana sobre el padre
        self.update_idletasks()
        w = 550
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
        if estrategias_candle:
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

            # Encabezado para Candle Strategies (sin parámetros de riesgo)
            ttk.Label(self.scrollable_frame, text="Estrategia", width=20, anchor="w").grid(row=start_row+2, column=0, padx=5)
            ttk.Label(self.scrollable_frame, text="Sin parámetros", width=20).grid(row=start_row+2, column=1, columnspan=2, padx=5)

            # Estrategias Candle (sin parámetros de riesgo)
            for idx, nombre in enumerate(estrategias_candle, start=start_row+3):
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
                
                # Aplicar etiqueta de riesgo si la estrategia está en el diccionario
                if nombre in risk_levels:
                    level, color = risk_levels[nombre]
                    ttk.Label(
                        self.scrollable_frame, 
                        text=f"[Riesgo {level}]", 
                        foreground=color,
                        font=('Arial', 8, 'bold')
                    ).grid(row=idx, column=4, padx=5, sticky="w")

                # Espacio vacío para alinear con las forex strategies
                ttk.Label(self.scrollable_frame, text="").grid(row=idx, column=1, padx=5)
                ttk.Label(self.scrollable_frame, text="").grid(row=idx, column=2, padx=5)

                self.controls[nombre] = {
                    "selected": var_check,
                    "tipo": "candle"
                }

        # ---------------- SECCIÓN CANDLESTICK PATTERNS ----------------
        if patrones_list:
            start_row_patterns = (
                (len(estrategias_fx) + 3 if estrategias_fx else 0) +
                (len(estrategias_candle) + 2 if estrategias_candle else 0) + 2
            )

            lbl_patterns = ttk.Label(self.scrollable_frame, text="Candlestick Patterns", 
                                     font=("Arial", 10, "bold"), anchor="w")
            lbl_patterns.grid(row=start_row_patterns, column=0, columnspan=3, sticky="w", pady=(20, 10))

            # Botones para seleccionar/deseleccionar todos los Patterns (centrados)
            btn_patterns_frame = tk.Frame(self.scrollable_frame)
            btn_patterns_frame.grid(row=start_row_patterns + 1, column=0, columnspan=7, pady=(0, 5))
            btn_patterns_sel = ttk.Button(
                btn_patterns_frame,
                text="Seleccionar todos",
                command=lambda: self._set_group("pattern", 1),
                width=18
            )
            btn_patterns_desel = ttk.Button(
                btn_patterns_frame,
                text="Deseleccionar todos",
                command=lambda: self._set_group("pattern", 0),
                width=20
            )
            btn_patterns_sel.pack(side="left", padx=5)
            btn_patterns_desel.pack(side="left", padx=5)

            ttk.Label(self.scrollable_frame, text="Patrón", width=20, anchor="w").grid(row=start_row_patterns+2, column=0, padx=5)
            ttk.Label(self.scrollable_frame, text="Sin parámetros", width=20).grid(row=start_row_patterns+2, column=1, columnspan=2, padx=5)

            for idx, nombre in enumerate(sorted(patrones_list), start=start_row_patterns+3):
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
                
                # Aplicar etiqueta de riesgo si la estrategia está en el diccionario
                if nombre in risk_levels:
                    level, color = risk_levels[nombre]
                    ttk.Label(
                        self.scrollable_frame, 
                        text=f"[Riesgo {level}]", 
                        foreground=color,
                        font=('Arial', 8, 'bold')
                    ).grid(row=idx, column=4, padx=5, sticky="w")
                ttk.Label(self.scrollable_frame, text="").grid(row=idx, column=1, padx=5)
                ttk.Label(self.scrollable_frame, text="").grid(row=idx, column=2, padx=5)

                # IMPORTANTE: evitar colisión de nombres con CandleStrategies
                # Algunos patrones (p.ej., three_white_soldiers, three_black_crows)
                # también existen como estrategias de vela. Para evitar sobreescribir
                # entradas de self.controls, se añade un prefijo de namespace.
                pattern_key = f"pattern::{nombre}"
                self.controls[pattern_key] = {
                    "selected": var_check,
                    "tipo": "pattern"
                }

        # ---------------- CHECKBOXES DE OPCIONES ----------------
        # Calcular la fila donde colocar los checkboxes
        base_row = 0
        if estrategias_fx:
            # Filas usadas por Forex: título(0), botones(1), header(2), items(3..len+2)
            base_row = max(base_row, 3 + len(estrategias_fx))
        if estrategias_candle:
            # Inicio Candle en len_fx+3, usa: título, botones, header, items
            base_row = max(base_row, (len(estrategias_fx) + 3 if estrategias_fx else 0) + 3 + len(estrategias_candle))
        if patrones_list:
            # Inicio Patterns después de Candle, usa: título, botones, header, items
            base_row = max(base_row, (
                (len(estrategias_fx) + 3 if estrategias_fx else 0) +
                (3 + len(estrategias_candle) if estrategias_candle else 0) +
                3 + len(patrones_list)
            ))
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
            selected_patterns = []
            
            for name, ctrl in self.controls.items():
                if ctrl["selected"].get() == 1:
                    if ctrl["tipo"] == "forex":
                        selected_forex.append({
                            'name': name,
                            'risk': float(ctrl["riesgo"].get() or 0) / 100.0,  # Convert percentage to decimal
                            'rr_ratio': float(ctrl["rr"].get() or 2.0)
                        })
                    elif ctrl["tipo"] == "candle":
                        selected_candle.append(name)
                    elif ctrl["tipo"] == "pattern" and name.startswith("pattern::"):
                        selected_patterns.append(name.replace("pattern::", ""))
            
            # Get wait candles and max orders
            try:
                wait_candles = int(self.wait_candles_var.get() or 20)
            except (ValueError, AttributeError):
                wait_candles = 20
                
            try:
                max_orders = int(self.max_orders_var.get() or 5)
            except (ValueError, AttributeError):
                max_orders = 5
            
            # Get display options
            show_detection = bool(self.var_mostrar_deteccion.get())
            show_simulation = bool(self.var_mostrar_simulacion.get())
            
            # Prepare simulation config
            config = {
                'forex_strategies': selected_forex,
                'candle_strategies': selected_candle,
                'patterns': selected_patterns,
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