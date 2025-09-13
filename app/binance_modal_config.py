# app/binance_modal_config.py

import tkinter as tk
from tkinter import ttk
import re
import os
import json
import threading
from typing import Dict, List, Optional, Any

from strategies.strategy_utils import resolve_strategy_name


class BinanceSimulationConfigModal(tk.Toplevel):
    """Modal para MODIFICAR una configuración de simulación Binance ya en ejecución.

    - Muestra el mismo layout básico que BinanceSimulationModal (selección de estrategias
      Forex y Candle con parámetros, opciones de visualización y campos de configuración)
    - Pre-carga los valores a partir de `current_config`
    - Devuelve un nuevo objeto `config` vía callback cuando el usuario acepta
    """

    def __init__(
        self,
        parent,
        estrategias_fx: List[str],
        estrategias_candle: List[str],
        current_config: Dict[str, Any],
        callback,
    ):
        super().__init__(parent)
        self.parent = parent
        self.callback = callback
        self.title("Configurar simulación Binance")
        self.resizable(False, False)
        self.grab_set()

        # Guardar configuración actual
        self.current_config = current_config or {}

        # Altura fija de la zona scrollable
        list_area_height = 400
        w, h_total = 650, 600
        self.after_idle(lambda: self._center_window(w, h_total))
        self.geometry(f"{w}x{h_total}")

        # Guardar lista de estrategias candle para utilidades de carga
        try:
            self.estrategias_candle = list(estrategias_candle or [])
        except Exception:
            self.estrategias_candle = []

        # Frame principal scrollable
        main_frame = tk.Frame(self)
        main_frame.pack(fill="x", expand=False, padx=10, pady=10)
        main_frame.configure(height=list_area_height)
        main_frame.pack_propagate(False)

        self.canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            main_frame, orient="vertical", style="Logs.Vertical.TScrollbar", command=self.canvas.yview
        )
        self.scrollable_frame = tk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.scrollable_frame.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.scrollable_frame.bind("<Leave>", lambda e: self._unbind_mousewheel())

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set, height=list_area_height)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Controles por estrategia
        self.controls: Dict[str, Dict[str, Any]] = {}

        # Column expand
        try:
            self.scrollable_frame.grid_columnconfigure(4, weight=1)
        except Exception:
            pass

        # ---------------- SECCIÓN FOREX STRATEGIES ----------------
        if estrategias_fx:
            ttk.Label(self.scrollable_frame, text="Forex Strategies", font=("Arial", 10, "bold"), anchor="w").grid(
                row=0, column=0, columnspan=4, sticky="w", pady=(0, 10)
            )

            btn_fx_frame = tk.Frame(self.scrollable_frame)
            btn_fx_frame.grid(row=1, column=0, columnspan=7, pady=(0, 5))
            ttk.Button(btn_fx_frame, text="Seleccionar todos", command=lambda: self._set_group("forex", 1), width=18).pack(
                side="left", padx=5
            )
            ttk.Button(
                btn_fx_frame, text="Deseleccionar todos", command=lambda: self._set_group("forex", 0), width=20
            ).pack(side="left", padx=5)

            ttk.Label(self.scrollable_frame, text="Estrategia", width=20, anchor="w").grid(row=2, column=0, padx=5)
            ttk.Label(self.scrollable_frame, text="Riesgo (%)", width=10).grid(row=2, column=1, padx=5)
            ttk.Label(self.scrollable_frame, text="RR Ratio", width=10).grid(row=2, column=2, padx=5)
            ttk.Label(self.scrollable_frame, text="", width=10).grid(row=2, column=3, padx=5)

            vcmd_riesgo = (self.register(self._validate_two_decimals), '%P')

            # Mapa para pre-selección desde current_config
            current_fx_by_name = {
                (item.get('name') if isinstance(item, dict) else str(item)): item for item in self.current_config.get('forex_strategies', [])
            }

            risk_levels = {
                # Alto
                "breakout": ("Alto", "red"),
                "scalping_1m_strategy": ("Alto", "red"),
                "news_trading_strategy": ("Alto", "red"),
                "grid_trading_strategy": ("Alto", "red"),
                "mean_reversion": ("Alto", "red"),
                "mean_reversion_strategy": ("Alto", "red"),
                "mean_reversion_overlay": ("Alto", "red"),
                # Medio
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
                # Bajo
                "rsi_strategy": ("Bajo", "green"),
                "moving_average_crossover": ("Bajo", "green"),
                "bollinger_bands_strategy": ("Bajo", "green"),
                "support_resistance_strategy": ("Bajo", "green"),
                "supply_demand_zones": ("Bajo", "green"),
                "trendline_strategy": ("Bajo", "green"),
                "range_trading_strategy": ("Bajo", "green"),
            }

            for idx, nombre in enumerate(estrategias_fx, start=3):
                var_check = tk.IntVar()
                display_name = nombre.replace('_', ' ').capitalize()
                tk.Checkbutton(self.scrollable_frame, text=display_name, variable=var_check, anchor="w", width=20).grid(
                    row=idx, column=0, sticky="w", padx=5, pady=2
                )

                # Etiqueta riesgo
                real_name = resolve_strategy_name(nombre, "forex")
                if real_name in risk_levels:
                    level, color = risk_levels[real_name]
                    ttk.Label(
                        self.scrollable_frame, text=f"[Riesgo {level}]", foreground=color, font=("Arial", 8, "bold")
                    ).grid(row=idx, column=4, padx=5, sticky="w")

                # Entradas riesgo / rr
                var_riesgo = tk.StringVar(value="1.00")
                entry_riesgo = tk.Entry(
                    self.scrollable_frame, textvariable=var_riesgo, width=8, validate="key", validatecommand=vcmd_riesgo
                )
                entry_riesgo.grid(row=idx, column=1, padx=5)

                var_rr = tk.StringVar(value="2")
                tk.Entry(self.scrollable_frame, textvariable=var_rr, width=8).grid(row=idx, column=2, padx=5)

                # Pre-pop desde config
                if nombre in current_fx_by_name:
                    var_check.set(1)
                    try:
                        item = current_fx_by_name[nombre]
                        if isinstance(item, dict):
                            r = float(item.get('risk', 0.01)) * 100.0
                            rr = float(item.get('rr_ratio', 2.0))
                            var_riesgo.set(f"{r:.2f}")
                            var_rr.set(str(rr))
                        else:
                            # Si viniese como string, mantenemos defaults
                            pass
                    except Exception:
                        pass

                self.controls[nombre] = {
                    "selected": var_check,
                    "riesgo": var_riesgo,
                    "rr": var_rr,
                    "tipo": "forex",
                }

        # ---------------- SECCIÓN CANDLE STRATEGIES ----------------
        if estrategias_candle:
            base_row = (3 + len(estrategias_fx)) if estrategias_fx else 0
            ttk.Label(self.scrollable_frame, text="Candle Strategies", font=("Arial", 10, "bold"), anchor="w").grid(
                row=base_row, column=0, columnspan=3, sticky="w", pady=(20, 10)
            )

            btn_candle_frame = tk.Frame(self.scrollable_frame)
            btn_candle_frame.grid(row=base_row + 1, column=0, columnspan=7, pady=(0, 5))
            ttk.Button(
                btn_candle_frame, text="Seleccionar todos", command=lambda: self._set_group("candle", 1), width=18
            ).pack(side="left", padx=5)
            ttk.Button(
                btn_candle_frame, text="Deseleccionar todos", command=lambda: self._set_group("candle", 0), width=20
            ).pack(side="left", padx=5)
            # Botón para cargar configuraciones guardadas y aplicarlas (pasa a Custom)
            ttk.Button(
                btn_candle_frame, text="Cargar configuraciones", command=self._load_all_candle_configs_async, width=25
            ).pack(side="left", padx=5)

            # Checkbox Aplicar solo detección + botón de configuración global (placeholder no-op)
            detection_frame = tk.Frame(self.scrollable_frame)
            detection_frame.grid(row=base_row + 2, column=0, columnspan=7, pady=(5, 10))
            self.aplicar_solo_deteccion = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                detection_frame, 
                text="Aplicar solo detección", 
                variable=self.aplicar_solo_deteccion,
                command=self._on_aplicar_solo_deteccion_change
            ).pack(side="left", padx=5)
            ttk.Button(
                detection_frame, text="Configurar detección", command=self._open_pattern_detection_config, width=20
            ).pack(side="left", padx=5)

            ttk.Label(self.scrollable_frame, text="Estrategia", width=20, anchor="w").grid(row=base_row + 3, column=0, padx=5)
            ttk.Label(self.scrollable_frame, text="Configuración", width=15).grid(row=base_row + 3, column=1, padx=5)
            ttk.Label(self.scrollable_frame, text="", width=15).grid(row=base_row + 3, column=2, padx=5)

            # Pre-map candle seleccionadas
            current_candle_by_name = {}
            for item in self.current_config.get('candle_strategies', []) or []:
                if isinstance(item, dict) and 'name' in item:
                    current_candle_by_name[item['name']] = item
                elif isinstance(item, str):
                    current_candle_by_name[item] = {"name": item, "config": None}

            for idx, nombre in enumerate(estrategias_candle, start=base_row + 4):
                var_check = tk.IntVar()
                display_name = nombre.replace('_', ' ').capitalize()
                tk.Checkbutton(self.scrollable_frame, text=display_name, variable=var_check, anchor="w", width=20).grid(
                    row=idx, column=0, sticky="w", padx=5, pady=2
                )

                var_config_type = tk.StringVar(value="Default")
                combo = ttk.Combobox(
                    self.scrollable_frame, textvariable=var_config_type, values=["Default", "Custom"], state="readonly", width=12
                )
                combo.grid(row=idx, column=1, padx=5)

                btn_cfg = ttk.Button(self.scrollable_frame, text="Configuración", command=lambda n=nombre: self._open_candle_config(n), state="disabled", width=14)
                btn_cfg.grid(row=idx, column=2, padx=5, sticky="w")

                # Pre-pop si estaba seleccionada
                if nombre in current_candle_by_name:
                    var_check.set(1)
                    item = current_candle_by_name[nombre]
                    cfg = item.get('config') if isinstance(item, dict) else None
                    if cfg is not None:
                        var_config_type.set("Custom")
                        btn_cfg.config(state="normal")

                def on_combo_change(event, n=nombre):
                    ctrl = self.controls.get(n)
                    if not ctrl:
                        return
                    if ctrl["config_type"].get() == "Custom":
                        ctrl["config_button"].config(state="normal")
                        if ctrl.get("custom_config") is None:
                            ctrl["custom_config"] = {}
                    else:
                        ctrl["config_button"].config(state="disabled")

                combo.bind('<<ComboboxSelected>>', on_combo_change)

                self.controls[nombre] = {
                    "selected": var_check,
                    "tipo": "candle",
                    "config_type": var_config_type,
                    "config_button": btn_cfg,
                    "custom_config": current_candle_by_name.get(nombre, {}).get('config'),
                }

        # ---------------- CHECKBOXES DE OPCIONES ----------------
        base_row = 0
        if estrategias_fx:
            base_row = max(base_row, 3 + len(estrategias_fx))
        if estrategias_candle:
            base_row = max(base_row, (len(estrategias_fx) + 3 if estrategias_fx else 0) + 3 + len(estrategias_candle))
        options_row = base_row + 2

        self.var_mostrar_deteccion = tk.IntVar(value=1 if self.current_config.get('show_detection', True) else 0)
        tk.Checkbutton(
            self.scrollable_frame, text="Mostrar detección de patrones", variable=self.var_mostrar_deteccion, anchor="w"
        ).grid(row=options_row, column=0, columnspan=3, sticky="w", padx=5, pady=(20, 5))

        self.var_mostrar_simulacion = tk.IntVar(value=1 if self.current_config.get('show_simulation', True) else 0)
        tk.Checkbutton(
            self.scrollable_frame, text="Mostrar simulación con Risk Manager", variable=self.var_mostrar_simulacion, anchor="w"
        ).grid(row=options_row + 1, column=0, columnspan=3, sticky="w", padx=5, pady=5)

        # ---------------- CAMPOS DE CONFIGURACIÓN ----------------
        frame_config = tk.Frame(self)
        frame_config.pack(pady=5, fill='x')

        config_fields = tk.Frame(frame_config)
        config_fields.pack(pady=0, expand=True)

        # Operaciones forex/velas máximas
        frame_operations = tk.Frame(config_fields)
        frame_operations.pack(pady=2)
        ttk.Label(frame_operations, text="Operaciones forex máximas:").pack(side="left", padx=6)
        self.max_forex_var = tk.StringVar(value=str(self.current_config.get('max_forex_operations', 0)))
        vcmd_int = (self.register(self._validate_int), '%P')
        tk.Entry(frame_operations, textvariable=self.max_forex_var, width=5, validate="key", validatecommand=vcmd_int).pack(
            side="left", padx=2
        )
        ttk.Label(frame_operations, text="Operaciones velas máximas:").pack(side="left", padx=6)
        self.max_candle_var = tk.StringVar(value=str(self.current_config.get('max_candle_operations', 0)))
        tk.Entry(frame_operations, textvariable=self.max_candle_var, width=5, validate="key", validatecommand=vcmd_int).pack(
            side="left", padx=2
        )

        # Velas a esperar
        frame_wait = tk.Frame(config_fields)
        frame_wait.pack(pady=2)
        ttk.Label(frame_wait, text="Velas a esperar:").pack(side="left", padx=6)
        self.wait_candles_var = tk.StringVar(value=str(self.current_config.get('wait_candles', 20)))
        tk.Entry(frame_wait, textvariable=self.wait_candles_var, width=5, validate="key", validatecommand=vcmd_int).pack(
            side="left", padx=2
        )

        # Máx. órdenes
        frame_max = tk.Frame(config_fields)
        frame_max.pack(pady=2)
        ttk.Label(frame_max, text="Máx. órdenes:").pack(side="left", padx=6)
        self.max_orders_var = tk.StringVar(value=str(self.current_config.get('max_orders', 5)))
        tk.Entry(frame_max, textvariable=self.max_orders_var, width=5, validate="key", validatecommand=vcmd_int).pack(
            side="left", padx=2
        )

        # Botonera
        frame_btn = tk.Frame(self)
        frame_btn.pack(pady=10)
        ttk.Button(frame_btn, text="Cancelar", command=self.destroy).pack(side="left", padx=10)
        ttk.Button(frame_btn, text="Aplicar", command=self._aceptar).pack(side="left", padx=10)

    # ---------------- Utilidades/UI ----------------
    def _center_window(self, width: int, height: int):
        try:
            self.update_idletasks()
            x = self.winfo_screenwidth() // 2 - width // 2
            y = self.winfo_screenheight() // 2 - height // 2
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _bind_mousewheel(self):
        try:
            self.bind_all("<MouseWheel>", self._on_mousewheel)
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
        try:
            if proposed == "":
                return True
            return re.fullmatch(r"\d*(?:\.|\,)?\d{0,2}", proposed) is not None
        except Exception:
            return False

    def _validate_int(self, value: str) -> bool:
        if value == "":
            return True
        try:
            return int(value) >= 0
        except ValueError:
            return False

    def _set_group(self, tipo: str, value: int):
        try:
            for ctrl in self.controls.values():
                if ctrl.get("tipo") == tipo:
                    ctrl["selected"].set(1 if value else 0)
        except Exception:
            pass

    def _open_candle_config(self, strategy_name: str):
        # Placeholder para futuro modal de configuración por-estrategia
        pass

    def _on_aplicar_solo_deteccion_change(self):
        """Maneja el cambio del checkbox 'Aplicar solo detección'."""
        try:
            if self.aplicar_solo_deteccion.get():
                # Cambiar todos los dropdowns de candle strategies a 'Default'
                for name, ctrl in self.controls.items():
                    if ctrl.get("tipo") == "candle":
                        if ctrl.get("config_type"):
                            ctrl["config_type"].set("Default")
                        if ctrl.get("config_button"):
                            ctrl["config_button"].config(state="disabled")
        except Exception as e:
            print(f"Error en _on_aplicar_solo_deteccion_change: {e}")

    def _open_pattern_detection_config(self):
        """Abre modal de configuración global para detección de patrones."""
        try:
            # Posicionar a la derecha del modal principal
            self.update_idletasks()
            x = self.winfo_rootx() + self.winfo_width() + 10
            y = self.winfo_rooty()

            # Obtener configuración actual global o usar defaults
            current_config = getattr(self, 'global_pattern_config', None) or self._get_default_pattern_detection_config()

            def on_save(config_dict):
                try:
                    # Guardar configuración global
                    self.global_pattern_config = config_dict
                    print(f"Configuración de detección guardada: {len(config_dict)} parámetros")
                except Exception as e:
                    print(f"Error guardando configuración: {e}")

            # Importar el modal desde binance_modal.py
            from .binance_modal import PatternDetectionModal
            PatternDetectionModal(self, current_config, on_save, x, y)
        except Exception as e:
            print(f"Error opening pattern detection modal: {e}")

    def _get_default_pattern_detection_config(self) -> dict:
        """Devuelve configuración por defecto para detección de patrones."""
        return {
            # Parámetros de detección de patrones
            "doji_threshold": 0.05,
            "tweezer_tolerance": 0.001,
            "min_confidence": 0.6,
            "partial_factor": 0.5,
            "hammer_body_ratio": 1.5,
            "shooting_star_ratio": 2.0,
            "spinning_top_ratio": 0.3,
            "marubozu_ratio": 0.8,
            
            # Parámetros de indicadores técnicos
            "atr_period": 14,           # ✅ Estándar, OK
            "trend_period": 20,         # ✅ Estándar, OK  
            "volatility_period": 20,    # ✅ Estándar, OK
            
            # Parámetros adicionales de patrones
            "engulfing_min_body_ratio": 1.05,       # 5% más grande (era 1.2)
            "harami_max_body_ratio": 0.9,           # 90% del tamaño (era 0.8)
            "star_gap_threshold": 0.005,             # 0.5% gap (era 0.001)
            "three_methods_trend_strength": 0.5      # 50% fuerza (era 0.7)
        }

    # ---------------- Carga masiva de configuraciones Candle ----------------
    def _load_all_candle_configs_async(self):
        """Carga configuraciones desde /config en background y las aplica al UI."""
        def load_configs():
            try:
                configs = self._load_all_candle_configs_sync()
                self.after(0, lambda: self._apply_loaded_configs(configs))
            except Exception as e:
                print(f"Error loading configs in background: {e}")

        thread = threading.Thread(target=load_configs, daemon=True)
        thread.start()

    def _load_all_candle_configs_sync(self) -> Dict[str, dict]:
        """Lee archivos JSON 'candle_<estrategia>.json' de la carpeta config/."""
        configs: Dict[str, dict] = {}
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(project_root, 'config')
        except Exception:
            return configs

        if not config_dir or not os.path.isdir(config_dir):
            return configs

        for name in (self.estrategias_candle or []):
            try:
                resolved = resolve_strategy_name(name, "candle") if name else ""
                cfg_path = os.path.join(config_dir, f"candle_{resolved}.json")
                if not os.path.exists(cfg_path):
                    continue
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    configs[name] = cfg
            except Exception:
                continue
        return configs

    def _apply_loaded_configs(self, configs: Dict[str, dict]):
        """Aplica al UI: setea combo en 'Custom', habilita botón y asigna custom_config."""
        loaded_count = 0
        for name, cfg in (configs or {}).items():
            try:
                ctrl = self.controls.get(name)
                if not ctrl or ctrl.get("tipo") != "candle":
                    continue
                ctrl["custom_config"] = cfg
                if ctrl.get("config_type"):
                    ctrl["config_type"].set("Custom")
                if ctrl.get("config_button"):
                    ctrl["config_button"].config(state="normal")
                loaded_count += 1
            except Exception:
                continue
        print(f"Cargar configuraciones: {loaded_count} estrategia(s) actualizada(s).")

    # ---------------- Aceptar ----------------
    def _aceptar(self):
        try:
            selected_forex = []
            selected_candle = []

            # Recolectar FOREX
            for name, ctrl in self.controls.items():
                if ctrl.get("tipo") != "forex":
                    continue
                if ctrl["selected"].get() == 1:
                    risk_value = ctrl["riesgo"].get()
                    rr_value = ctrl["rr"].get()
                    if not risk_value or not rr_value:
                        tk.messagebox.showerror(
                            "Error de Validación",
                            f"La estrategia forex '{name}' debe tener los campos 'Riesgo %' y 'RR' completados.",
                        )
                        return
                    try:
                        risk = float(risk_value)
                        rr = float(rr_value)
                        if risk <= 0 or rr <= 0:
                            tk.messagebox.showerror(
                                "Error de Validación",
                                f"La estrategia forex '{name}' debe tener valores positivos en 'Riesgo %' y 'RR'.",
                            )
                            return
                    except ValueError:
                        tk.messagebox.showerror(
                            "Error de Validación",
                            f"La estrategia forex '{name}' debe tener valores numéricos válidos en 'Riesgo %' y 'RR'.",
                        )
                        return
                    selected_forex.append({"name": name, "risk": risk / 100.0, "rr_ratio": rr})

            # Recolectar CANDLE
            for name, ctrl in self.controls.items():
                if ctrl.get("tipo") != "candle":
                    continue
                if ctrl["selected"].get() == 1:
                    config = None
                    try:
                        if getattr(self, 'aplicar_solo_deteccion', None) and self.aplicar_solo_deteccion.get():
                            # Usar config global si existiese en el futuro; por ahora None mantiene defaults
                            config = ctrl.get("custom_config") or None
                        else:
                            if ctrl.get("config_type") and ctrl["config_type"].get() == "Custom":
                                config = ctrl.get("custom_config") or {}
                            else:
                                config = None
                    except Exception:
                        config = None
                    selected_candle.append({"name": name, "config": config})

            if not selected_forex and not selected_candle:
                tk.messagebox.showerror(
                    "Error de Validación",
                    "Debe seleccionar al menos una estrategia (forex o candle).",
                )
                return

            # Campos numéricos de la parte inferior
            try:
                wait_candles = int(self.wait_candles_var.get() or 0)
                if wait_candles <= 0:
                    tk.messagebox.showerror("Error de Validación", "El campo 'Velas a esperar' debe ser mayor que 0.")
                    return
            except Exception:
                tk.messagebox.showerror("Error de Validación", "'Velas a esperar' inválido.")
                return

            try:
                max_orders = int(self.max_orders_var.get() or 0)
                if max_orders <= 0:
                    tk.messagebox.showerror("Error de Validación", "'Máx. órdenes' debe ser mayor que 0.")
                    return
            except Exception:
                tk.messagebox.showerror("Error de Validación", "'Máx. órdenes' inválido.")
                return

            try:
                max_forex = int(self.max_forex_var.get() or 0)
                max_candle = int(self.max_candle_var.get() or 0)
                if max_forex < 0 or max_candle < 0:
                    tk.messagebox.showerror(
                        "Error de Validación", "Las operaciones forex y velas máximas deben ser números positivos o cero."
                    )
                    return
                if max_forex + max_candle != max_orders:
                    tk.messagebox.showerror(
                        "Error de Validación",
                        f"La suma de operaciones forex máximas ({max_forex}) y operaciones velas máximas ({max_candle}) debe ser igual al máximo de órdenes ({max_orders}).",
                    )
                    return
            except Exception:
                tk.messagebox.showerror("Error de Validación", "Operaciones máximas inválidas.")
                return

            show_detection = bool(self.var_mostrar_deteccion.get())
            show_simulation = bool(self.var_mostrar_simulacion.get())

            new_config = {
                'forex_strategies': selected_forex,
                'candle_strategies': selected_candle,
                'patterns': [],
                'wait_candles': wait_candles,
                'max_orders': max_orders,
                'max_forex_operations': max_forex,
                'max_candle_operations': max_candle,
                'show_detection': show_detection,
                'show_simulation': show_simulation,
                # Mantener contadores externos en el llamador
            }

            if callable(self.callback):
                self.callback(new_config)
        finally:
            self.destroy()