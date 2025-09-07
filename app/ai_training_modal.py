# app/ai_training_modal.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.font import Font
import os
import shutil
import re

from .progress_modal import centrar_ventana
from strategies.strategy_utils import get_available_strategies, resolve_strategy_name


class AITrainingModal(tk.Toplevel):
    def __init__(self, parent, on_accept_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.on_accept_callback = on_accept_callback
        self.selected_model = None
        self.title("Entrenamiento de IA")
        
        # Tamaño y posición inicial
        self.width = 550
        self.height = 780
        self.geometry(f"{self.width}x{self.height}")
        self.resizable(False, True)  # Permitir redimensionar en altura
        self.grab_set()  # Hace la ventana modal
        
        # Posicionar más cerca del borde de la gráfica
        self.update_idletasks()  # Asegurarse de que los widgets se han creado
        
        # Obtener dimensiones de la pantalla y de la ventana
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calcular posición para estar centrado horizontalmente y pegado al borde superior
        x = (screen_width - self.width) // 2
        y = 50  # Pequeño margen desde el borde superior
        
        # Establecer geometría con posición
        self.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
        # Configurar comportamiento al redimensionar
        self.minsize(self.width, self.height)

        # Título
        title_label = ttk.Label(
            self,
            text="Pasos para entrenar la IA",
            font=("Arial", 12, "bold")
        )
        title_label.pack(pady=(20, 10))

        # Frame principal para los controles
        control_frame = ttk.Frame(self)
        control_frame.pack(pady=10, padx=20, fill="x")

        # Paso 1: Cargar modelo previo
        step1_frame = ttk.Frame(control_frame)
        step1_frame.pack(fill="x", pady=(0, 20))
        
        # Título del paso 1
        step1_label = ttk.Label(
            step1_frame,
            text="Paso 1: Cargar modelo previo (si existe)",
            font=("Arial", 10, "bold")
        )
        step1_label.pack(anchor="w", pady=(0, 5))
        
        # Frame para el botón y estado del paso 1
        load_frame = ttk.Frame(step1_frame)
        load_frame.pack(fill="x", pady=5)

        # Botón Cargar RL (más ancho)
        self.btn_load_rl = ttk.Button(
            load_frame,
            text="Cargar RL",
            command=self._on_load_rl,
            state="disabled",
            width=15
        )
        self.btn_load_rl.pack(side="left", padx=(0, 10))

        # Frame para el estado y mensaje
        status_frame = ttk.Frame(load_frame)
        status_frame.pack(side="left", fill="x", expand=True)

        # Etiqueta de estado (icono)
        self.status_label = ttk.Label(status_frame, text="", width=3)
        self.status_label.pack(side="left", padx=(0, 5))

        # Etiqueta de mensaje
        self.file_label = ttk.Label(
            status_frame,
            text="Ningún archivo seleccionado",
            wraplength=300,
            style='Status.TLabel',
            anchor="w"
        )
        self.file_label.pack(side="left", fill="x", expand=True)

        # Paso 2: Seleccionar estrategias
        step2_frame = ttk.Frame(control_frame)
        step2_frame.pack(fill="x", pady=(0, 10))  # Moved up further by reducing top padding to 0
        
        # Título del paso 2
        step2_label = ttk.Label(
            step2_frame,
            text="Paso 2: Seleccionar estrategias para aplicar al modelo",
            font=("Arial", 10, "bold")
        )
        step2_label.pack(anchor="w", pady=(0, 10))
        
        # Frame principal para el contenido del paso 2
        content_frame = ttk.Frame(step2_frame)
        content_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        # Frame para el área de estrategias con scroll
        strategies_frame = ttk.Frame(content_frame)
        strategies_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        # Crear un canvas con scrollbar
        canvas = tk.Canvas(strategies_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(strategies_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configurar el canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Crear ventana en el canvas para el frame desplazable
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar scrollbar y canvas
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Cargar y mostrar las estrategias
        self._load_strategies(scrollable_frame)
        
        # Configurar desplazamiento con la rueda del ratón (funciona al pasar por encima del contenido)
        def _on_mousewheel(event):
            try:
                # Windows / macOS
                if hasattr(event, 'delta') and event.delta:
                    delta = int(event.delta)
                    canvas.yview_scroll(-1 * int(delta / 120), 'units')
                # Linux (rueda arriba/abajo)
                elif hasattr(event, 'num') and event.num in (4, 5):
                    canvas.yview_scroll(-1 if event.num == 4 else 1, 'units')
            except Exception:
                pass

        def _bind_to_mousewheel(event):
            try:
                canvas.bind_all('<MouseWheel>', _on_mousewheel)
                canvas.bind_all('<Button-4>', _on_mousewheel)
                canvas.bind_all('<Button-5>', _on_mousewheel)
            except Exception:
                pass

        def _unbind_from_mousewheel(event):
            try:
                canvas.unbind_all('<MouseWheel>')
                canvas.unbind_all('<Button-4>')
                canvas.unbind_all('<Button-5>')
            except Exception:
                pass

        # Activar el scroll con la rueda al entrar/salir del área desplazable
        scrollable_frame.bind('<Enter>', _bind_to_mousewheel)
        scrollable_frame.bind('<Leave>', _unbind_from_mousewheel)
        
        # Frame para el número máximo de órdenes
        orders_frame = ttk.Frame(content_frame)
        orders_frame.pack(fill="x", pady=(15, 5))
        
        ttk.Label(orders_frame, text="Máximo de órdenes simultáneas (0 = ilimitado):").pack(side="left", padx=(0, 10))
        
        self.max_orders = tk.StringVar(value="5")
        orders_spinbox = ttk.Spinbox(
            orders_frame,
            from_=0,
            to=1000000,
            textvariable=self.max_orders,
            width=5
        )
        orders_spinbox.pack(side="left")
        
        # Opciones avanzadas: intentos, semilla, guardar mejor config
        advanced_frame = ttk.Frame(content_frame)
        advanced_frame.pack(fill="x", pady=(10, 5))
        ttk.Label(
            advanced_frame,
            text="Opciones avanzadas",
            font=("Arial", 10, "bold")
        ).pack(anchor="w")

        # (Eliminados: Máximo de intentos y Semilla aleatoria)

        # Timesteps por intento
        ts_frame = ttk.Frame(advanced_frame)
        ts_frame.pack(fill="x", pady=(6, 0))
        ttk.Label(ts_frame, text="Timesteps por intento:").pack(side="left")
        self.timesteps_var = tk.StringVar(value="3000")
        ts_spin = ttk.Spinbox(
            ts_frame,
            from_=1,
            to=10000000,
            textvariable=self.timesteps_var,
            width=8
        )
        ts_spin.pack(side="left", padx=(10, 0))

        # Guardar mejor configuración
        save_frame = ttk.Frame(advanced_frame)
        save_frame.pack(fill="x", pady=(6, 0))
        self.save_best_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            save_frame,
            text="Guardar mejor configuración",
            variable=self.save_best_var,
            onvalue=True,
            offvalue=False
        ).pack(side="left")

        # Label Paso 3: Orden de finalización
        ttk.Label(
            content_frame,
            text="Paso 3: Orden de finalización",
            font=("Arial", 10, "bold")
        ).pack(anchor="w", pady=(10, 0))
        
        # Controles del Paso 3
        paso3_frame = ttk.Frame(content_frame)
        paso3_frame.pack(fill="x", pady=(8, 0))

        # Opción 2: Win Rate %
        winrate_frame = ttk.Frame(paso3_frame)
        winrate_frame.pack(fill="x", pady=4)
        self.use_winrate_var = tk.BooleanVar(value=False)
        self.winrate_var = tk.StringVar(value="")
        win_cb = ttk.Checkbutton(
            winrate_frame,
            text="Win Rate % igual a",
            variable=self.use_winrate_var,
            onvalue=True,
            offvalue=False
        )
        win_cb.pack(side="left")
        # Validación para permitir sólo números con punto
        vcmd = (self.register(self._validate_float), '%P')
        win_entry = ttk.Entry(
            winrate_frame,
            textvariable=self.winrate_var,
            width=8,
            validate='key',
            validatecommand=vcmd
        )
        win_entry.pack(side="left", padx=(10, 0))
        
        # Frame para los botones inferiores
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20, padx=20, fill="x", side="bottom")

        # Botón Cancelar
        self.btn_cancel = ttk.Button(
            button_frame,
            text="Cancelar",
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=5)

        # Botón Aceptar
        self.btn_accept = ttk.Button(
            button_frame,
            text="Aceptar",
            command=self._on_accept,
            state="disabled"
        )
        self.btn_accept.pack(side="right", padx=5)

        # Botón Abrir reporte IA
        self.btn_open_report = ttk.Button(
            button_frame,
            text="Abrir reporte IA",
            command=self._open_best_report
        )
        self.btn_open_report.pack(side="left", padx=5)
        # Aviso de condiciones para habilitar Aceptar
        self.accept_hint = ttk.Label(
            button_frame,
            text="",
            foreground="red",
            wraplength=380,
            justify="left"
        )
        self.accept_hint.pack(side="left", fill="x", expand=True)
        # Aplicar estado pendiente si fue calculado antes de crear el botón
        if hasattr(self, "_pending_accept_state"):
            try:
                self.btn_accept.config(state=self._pending_accept_state)
            except Exception:
                pass
            delattr(self, "_pending_accept_state")

        # Configurar estilos
        self._setup_styles()
        
        # Verificar si hay modelos en la carpeta models_rl
        self._check_rl_models()
        # Enlazar cambios de controles globales a la lógica de habilitación
        try:
            self.max_orders.trace_add('write', lambda *_: self._recompute_accept_state())
            self.use_winrate_var.trace_add('write', lambda *_: self._recompute_accept_state())
            self.winrate_var.trace_add('write', lambda *_: self._recompute_accept_state())
        except Exception:
            pass

    def _setup_styles(self):
        """Configura los estilos para los widgets"""
        style = ttk.Style()
        
        # Estilo para el frame de estado
        style.configure('Status.TFrame', background='#f0f0f0')
        style.configure('Status.TLabel', background='#f0f0f0')
        
        # Fuente para los iconos
        self.icon_font = Font(family="Arial", size=12, weight="bold")

    def _validate_float(self, P: str) -> bool:
        """Permite sólo números con punto (float) o vacío durante la escritura."""
        if P == "":
            return True
        return re.fullmatch(r"\d*\.?\d*", P) is not None

    def _check_rl_models(self):
        """Verifica si hay modelos en la carpeta models_rl"""
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models_rl')
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir, exist_ok=True)
            return
            
        rl_models = [f for f in os.listdir(self.models_dir) 
                    if f.endswith(('.h5', '.pkl', '.pt', '.zip'))]
        if rl_models:
            self.btn_load_rl.config(state="normal")

    def _on_load_rl(self):
        """Maneja el evento de cargar modelo RL"""
        # Abrir diálogo de selección de archivo
        file_path = filedialog.askopenfilename(
            initialdir=self.models_dir,
            title="Seleccionar modelo RL",
            filetypes=(
                ("Modelos RL", "*.h5 *.pkl *.pt *.zip"),
                ("Todos los archivos", "*.*")
            )
        )
        
        if not file_path:
            return  # Usuario canceló la selección
            
        # Normalizar las rutas para comparación
        normalized_models_dir = os.path.normpath(self.models_dir)
        normalized_file_path = os.path.normpath(file_path)
        
        # Validar que el archivo esté en la carpeta models_rl
        if not normalized_file_path.startswith(normalized_models_dir):
            messagebox.showerror(
                "Error",
                f"El archivo debe estar en la carpeta: {self.models_dir}"
            )
            self._update_status(False, "Archivo no válido")
            return
            
        # Validar extensión del archivo
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in ['.h5', '.pkl', '.pt', '.zip']:
            messagebox.showerror(
                "Error",
                "Formato de archivo no soportado. Use .h5, .pkl, .pt o .zip"
            )
            self._update_status(False, "Formato no válido")
            return
            
        # Si todo está bien, actualizar la interfaz
        self.selected_model = file_path
        self._update_status(True, "Modelo cargado correctamente")
        # Recalcular condiciones de habilitación
        self._recompute_accept_state()
        
    def _create_risk_controls(self, parent, show_labels=False):
        """Crea los controles de riesgo y RR para una estrategia"""
        # Frame principal para los controles de riesgo
        main_frame = ttk.Frame(parent)
        
        # Nota: Las etiquetas de cabecera se gestionan en la sección superior,
        # por lo que aquí no se crean etiquetas.
        
        # Frame para los textboxes
        entries_frame = ttk.Frame(main_frame)
        entries_frame.pack(fill="x")
        
        # Variables para los controles
        risk_var = tk.StringVar(value="1.0")
        rr_var = tk.StringVar(value="2.0")
        
        # Entradas (una al lado de la otra)
        risk_entry = ttk.Entry(
            entries_frame,
            textvariable=risk_var,
            width=5,
            font=("Arial", 8),
            justify="right"
        )
        risk_entry.pack(side="left", padx=(0, 10))
        
        rr_entry = ttk.Entry(
            entries_frame,
            textvariable=rr_var,
            width=5,
            font=("Arial", 8),
            justify="right"
        )
        rr_entry.pack(side="left")
        
        return main_frame, risk_var, rr_var
    
    def _load_strategies(self, parent_frame):
        """Carga las estrategias disponibles en el frame especificado"""
        # Usar el registro centralizado de alias para Forex y Candle strategies
        fx_methods, candle_methods = get_available_strategies()
        # Sección de estrategias Forex con cabecera alineada y botones de selección
        header_frame = ttk.Frame(parent_frame)
        header_frame.pack(fill="x", pady=(0, 5))
        
        # Título a la izquierda
        forex_label = ttk.Label(
            header_frame,
            text="Estrategias Forex:",
            font=("Arial", 9, "bold")
        )
        forex_label.pack(side="left", anchor="w")
        
        # Función auxiliar para seleccionar/deseleccionar en bloque
        def _set_all(vars_dict, value: bool):
            try:
                for v in vars_dict.values():
                    v.set(value)
            except Exception:
                pass
        
        # Botones de seleccionar/deseleccionar a la derecha
        buttons_frame_fx = ttk.Frame(header_frame)
        buttons_frame_fx.pack(side="right")
        ttk.Button(
            buttons_frame_fx,
            text="Seleccionar todos",
            command=lambda: _set_all(self.strategy_vars, True),
            width=16
        ).pack(side="right", padx=(5, 10))
        ttk.Button(
            buttons_frame_fx,
            text="Deseleccionar todos",
            command=lambda: _set_all(self.strategy_vars, False),
            width=18
        ).pack(side="right", padx=(5, 10))
        
        # Cabecera de controles a la derecha (alineada con los inputs)
        controls_header = ttk.Frame(header_frame)
        controls_header.pack(side="right", padx=10)
        ttk.Label(controls_header, text="% Riesgo:", font=("Arial", 8)).pack(side="left", padx=(0, 10))
        ttk.Label(controls_header, text="RR Ratio:", font=("Arial", 8)).pack(side="left")
        
        # Inicializar estructuras
        self.strategy_vars = {}  # Forex
        self.risk_vars = {}
        self.rr_vars = {}
        self.candle_vars = {}    # Candle strategies
        
        # Estrategias Forex (alias desde el registro)
        for strategy in sorted(fx_methods):
            # Frame para cada estrategia
            strategy_frame = ttk.Frame(parent_frame)
            strategy_frame.pack(fill="x", pady=2)
            
            # Checkbox de la estrategia
            var = tk.BooleanVar()
            self.strategy_vars[strategy] = var
            cb = ttk.Checkbutton(
                strategy_frame,
                text=strategy.replace('_', ' ').capitalize(),
                variable=var,
                onvalue=True,
                offvalue=False
            )
            cb.pack(side="left", anchor="w")
            
            # Frame para los controles de la derecha
            controls_frame = ttk.Frame(strategy_frame)
            controls_frame.pack(side="right", padx=10)
            
            # Controles de riesgo y RR (sin etiquetas aquí; cabecera ya creada)
            risk_frame, risk_var, rr_var = self._create_risk_controls(controls_frame, show_labels=False)
            # Primero empaquetar los controles, luego la etiqueta para que quede a la derecha del RR
            risk_frame.pack(side="right", padx=(10, 0))
            # Etiqueta de versión junto al RR según el nombre real de la estrategia
            try:
                real_name = resolve_strategy_name(strategy, "forex")
                v1_names = {"adx_strategy", "trend_following", "breakout", "rsi_strategy"}
                version_text = "(versión 1.0)" if real_name in v1_names else "(versión 2.0)"
                ttk.Label(controls_frame, text=version_text, font=("Arial", 8, "italic")).pack(side="right", padx=(8, 0))
            except Exception:
                pass
            
            # Almacenar las variables de control
            self.risk_vars[strategy] = risk_var
            self.rr_vars[strategy] = rr_var
        
        # Separador
        ttk.Separator(parent_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Sección de Candle Strategies con botones de selección
        candle_header = ttk.Frame(parent_frame)
        candle_header.pack(fill='x', pady=(0, 5))
        candle_label = ttk.Label(
            candle_header,
            text="Candle Strategies:",
            font=("Arial", 9, "bold")
        )
        candle_label.pack(side='left', anchor='w')
        buttons_frame_candle = ttk.Frame(candle_header)
        buttons_frame_candle.pack(side='right')
        ttk.Button(
            buttons_frame_candle,
            text="Seleccionar todos",
            command=lambda: _set_all(self.candle_vars, True),
            width=16
        ).pack(side='right', padx=(5, 10))
        ttk.Button(
            buttons_frame_candle,
            text="Deseleccionar todos",
            command=lambda: _set_all(self.candle_vars, False),
            width=18
        ).pack(side='right', padx=(5, 10))

        for cstrat in sorted(candle_methods):
            var = tk.BooleanVar()
            self.candle_vars[cstrat] = var
            cb = ttk.Checkbutton(
                parent_frame,
                text=cstrat.replace('_', ' ').capitalize(),
                variable=var,
                onvalue=True,
                offvalue=False
            )
            cb.pack(anchor="w", padx=(20, 0), pady=2)


        # Habilitar/deshabilitar botón Aceptar según condiciones completas
        def _vars_changed(*_):
            self._recompute_accept_state()

        for v in list(self.strategy_vars.values()) + list(self.candle_vars.values()):
            v.trace_add('write', _vars_changed)

        self._recompute_accept_state()
    
    def _update_status(self, is_valid, message):
        """Actualiza el estado de la interfaz según la validación"""
        if is_valid:
            # Mostrar check verde
            self.status_label.config(
                text="✓",
                foreground="green",
                font=self.icon_font
            )
            # Actualizar etiqueta con ruta del archivo
            filename = os.path.basename(self.selected_model)
            self.file_label.config(
                text=f"Modelo seleccionado: {filename}",
                foreground="green"
            )
        else:
            # Mostrar X roja
            self.status_label.config(
                text="✗",
                foreground="red",
                font=self.icon_font
            )
            self.file_label.config(
                text=message,
                foreground="red"
            )
            if hasattr(self, 'btn_accept'):
                self.btn_accept.config(state="disabled")
            else:
                self._pending_accept_state = "disabled"

    # ----------------- Lógica de habilitación de Aceptar -----------------
    def _parse_positive_int(self, s: str) -> int:
        try:
            v = int(str(s).strip())
            return v if v > 0 else 0
        except Exception:
            return 0

    def _parse_positive_float(self, s: str) -> float:
        try:
            v = float(str(s).strip())
            return v if v > 0 else 0.0
        except Exception:
            return 0.0

    def _recompute_accept_state(self):
        # 1) Modelo cargado
        has_model = bool(self.selected_model)
        # 2) Alguna estrategia seleccionada
        any_fx = any(v.get() for v in getattr(self, 'strategy_vars', {}).values()) if hasattr(self, 'strategy_vars') else False
        any_cd = any(v.get() for v in getattr(self, 'candle_vars', {}).values()) if hasattr(self, 'candle_vars') else False
        has_selection = any_fx or any_cd
        # 3) Máx. órdenes simultáneas >= 0 (0 = ilimitado)
        try:
            max_orders_val = int(str(getattr(self, 'max_orders', tk.StringVar(value='0')).get()).strip()) if hasattr(self, 'max_orders') else 0
        except Exception:
            max_orders_val = 0
        max_ok = (max_orders_val >= 0)
        # 4) Condición de finalización: sólo WinRate activo y > 0
        win_ok = bool(self.use_winrate_var.get()) and self._parse_positive_float(self.winrate_var.get()) > 0.0 if hasattr(self, 'use_winrate_var') else False

        enabled = has_model and has_selection and max_ok and win_ok

        desired_state = 'normal' if enabled else 'disabled'
        if hasattr(self, 'btn_accept'):
            try:
                self.btn_accept.config(state=desired_state)
            except Exception:
                pass
        else:
            self._pending_accept_state = desired_state

        # Actualizar aviso
        if hasattr(self, 'accept_hint'):
            msgs = []
            if not has_model:
                msgs.append("• Cargue un modelo")
            if not has_selection:
                msgs.append("• Seleccione al menos una estrategia Forex o Candle")
            if not max_ok:
                msgs.append("• Máximo de órdenes simultáneas debe ser ≥ 0 (0 = ilimitado)")
            if not win_ok:
                if hasattr(self, 'use_winrate_var') and self.use_winrate_var.get() and self._parse_positive_float(self.winrate_var.get()) <= 0.0:
                    msgs.append("• Win Rate debe ser > 0")
                elif hasattr(self, 'use_winrate_var') and not self.use_winrate_var.get():
                    msgs.append("• Active 'Win Rate % igual a' (>0)")

            if enabled:
                self.accept_hint.config(text="Listo para entrenar", foreground="green")
            else:
                self.accept_hint.config(text="\n".join(msgs), foreground="red")

    def _on_accept(self):
        """Maneja el evento de aceptar: recopila selecciones y las devuelve."""
        seleccion_fx = {}
        for metodo, var in self.strategy_vars.items():
            if var.get():
                # Tratar siempre el input de riesgo como porcentaje (ej. 1.0 => 0.01)
                try:
                    riesgo_input = float(self.risk_vars[metodo].get() or 0.0)
                except Exception:
                    riesgo_input = 0.0
                riesgo = riesgo_input / 100.0
                try:
                    rr = float(self.rr_vars[metodo].get() or 0.0)
                except Exception:
                    rr = 0.0
                seleccion_fx[metodo] = {"tipo": "forex", "riesgo": riesgo, "rr": rr}

        seleccion_candle = []
        for metodo, var in getattr(self, 'candle_vars', {}).items():
            if var.get():
                seleccion_candle.append(metodo)

        # Los patrones de velas ahora están incluidos en CandleStrategies
        seleccion_patterns = []

        max_orders = int(self.max_orders.get()) if hasattr(self, 'max_orders') else 5
        # Parám. de parada
        use_winrate = bool(self.use_winrate_var.get()) if hasattr(self, 'use_winrate_var') else False
        winrate = self._parse_positive_float(self.winrate_var.get()) if hasattr(self, 'winrate_var') else 0.0
        # Modelo seleccionado (si hay)
        selected_model_path = self.selected_model if hasattr(self, 'selected_model') else None

        # Opciones avanzadas restantes
        save_best = bool(getattr(self, 'save_best_var', tk.BooleanVar(value=True)).get())

        if self.on_accept_callback:
            # Intentar con la firma más completa primero (sin iteraciones)
            try:
                # Intento 1: pasar con argumentos con nombre, incluyendo seleccion_candle si la firma lo permite
                try:
                    self.on_accept_callback(
                        seleccion_fx=seleccion_fx,
                        seleccion_candle=seleccion_candle,
                        max_orders=max_orders,
                        use_winrate=use_winrate,
                        winrate=winrate,
                        selected_model_path=selected_model_path,
                        save_best=save_best,
                        timesteps_per_attempt=int(self.timesteps_var.get() or 3000),
                    )
                except TypeError:
                    # Intento 2: sin seleccion_candle
                    try:
                        self.on_accept_callback(
                            seleccion_fx=seleccion_fx,
                            seleccion_candle=seleccion_candle,
                            max_orders=max_orders,
                            use_winrate=use_winrate,
                            winrate=winrate,
                            selected_model_path=selected_model_path,
                            save_best=save_best,
                            timesteps_per_attempt=int(self.timesteps_var.get() or 3000),
                        )
                    except TypeError:
                        # Intento 3: última compatibilidad con 3 parámetros
                        try:
                            self.on_accept_callback(seleccion_fx, seleccion_candle, max_orders)
                        except TypeError:
                            try:
                                # Intento 4: sin parámetros
                                self.on_accept_callback()
                            except TypeError:
                                pass
            except Exception:
                # Seguridad: no romper el modal si algo falla en los callbacks
                pass

        self.destroy()

    def show(self):
        """Muestra el modal"""
        self.wait_window()
        return None

    # ----------------- Helpers -----------------
    def _best_report_paths(self):
        try:
            project_root = os.path.dirname(os.path.dirname(__file__))
            reports_dir = os.path.join(project_root, 'reports')
            txt_path = os.path.join(reports_dir, 'best_config_ia.txt')
            json_path = os.path.join(reports_dir, 'best_config_ia.json')
            return txt_path, json_path
        except Exception:
            return None, None

    def _open_best_report(self):
        try:
            txt_path, json_path = self._best_report_paths()
            candidates = []
            if txt_path and os.path.isfile(txt_path):
                candidates.append(txt_path)
            if json_path and os.path.isfile(json_path):
                candidates.append(json_path)
            if not candidates:
                messagebox.showinfo("Reporte IA", "Aún no hay reportes generados. Ejecute un entrenamiento para crear best_config_ia.")
                return
            target = candidates[0]
            # Abrir según plataforma
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(target)
                else:
                    import webbrowser
                    webbrowser.open(f"file://{target}")
            except Exception:
                import webbrowser
                webbrowser.open(f"file://{target}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el reporte: {e}")
