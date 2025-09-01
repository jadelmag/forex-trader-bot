# app/ai_training_modal.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.font import Font
import os
import shutil
import re

from .progress_modal import centrar_ventana
from strategies import ForexStrategies, CandleStrategies
from patterns.candlestickpatterns import CandlestickPatterns


class AITrainingModal(tk.Toplevel):
    def __init__(self, parent, on_accept_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.on_accept_callback = on_accept_callback
        self.selected_model = None
        self.title("Entrenamiento de IA")
        
        # Tamaño y posición inicial
        self.width = 500
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
            text="Paso 2: Seleccionar estrategias y patrones para aplicar al modelo",
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

        # Máximo de intentos (0 = ilimitado)
        attempts_frame = ttk.Frame(advanced_frame)
        attempts_frame.pack(fill="x", pady=(6, 0))
        ttk.Label(attempts_frame, text="Máximo de intentos (0 = ilimitado):").pack(side="left")
        self.max_attempts_var = tk.StringVar(value="0")
        attempts_spin = ttk.Spinbox(
            attempts_frame,
            from_=0,
            to=100000,
            textvariable=self.max_attempts_var,
            width=7
        )
        attempts_spin.pack(side="left", padx=(10, 0))

        # Semilla aleatoria (vacío = aleatorio) con tooltip
        seed_frame = ttk.Frame(advanced_frame)
        seed_frame.pack(fill="x", pady=(6, 0))
        ttk.Label(seed_frame, text="Semilla aleatoria (opcional):").pack(side="left")
        self.seed_var = tk.StringVar(value="")
        seed_entry = ttk.Entry(seed_frame, textvariable=self.seed_var, width=10)
        seed_entry.pack(side="left", padx=(10, 0))

        # Tooltip explicativo para la semilla
        self._seed_tooltip = None
        def _show_seed_tooltip(event=None):
            try:
                if self._seed_tooltip is not None:
                    return
                tip = tk.Toplevel(self)
                tip.wm_overrideredirect(True)
                tip.configure(bg="#333333")
                msg = (
                    "La semilla fija la aleatoriedad para hacer los resultados reproducibles.\n"
                    "• Vacío: cada ejecución será distinta (bueno para explorar).\n"
                    "• Entero (p. ej. 0, 42, 20240831): resultados reproducibles con los mismos datos y opciones.\n"
                    "En cada intento se usa semilla+intento-1 para variar de forma determinista.\n"
                    "Recomendación: usa un entero >= 0; deja vacío si quieres máxima exploración."
                )
                lbl = tk.Label(tip, text=msg, justify="left", bg="#333333", fg="#FFFFFF", padx=8, pady=6, font=("Segoe UI", 9))
                lbl.pack()
                # Posicionar al lado del entry
                x = seed_entry.winfo_rootx() + seed_entry.winfo_width() + 8
                y = seed_entry.winfo_rooty()
                tip.wm_geometry(f"+{x}+{y}")
                self._seed_tooltip = tip
            except Exception:
                pass
        def _hide_seed_tooltip(event=None):
            try:
                if self._seed_tooltip is not None:
                    self._seed_tooltip.destroy()
                    self._seed_tooltip = None
            except Exception:
                self._seed_tooltip = None
        seed_entry.bind("<Enter>", _show_seed_tooltip)
        seed_entry.bind("<Leave>", _hide_seed_tooltip)

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
        # Obtener métodos públicos por introspección (coincidir con modal de mostrar estrategias)
        fx_methods = [
            nombre for nombre in dir(ForexStrategies)
            if callable(getattr(ForexStrategies, nombre)) and not nombre.startswith("_")
        ]
        candle_methods = [
            nombre for nombre in dir(CandleStrategies)
            if callable(getattr(CandleStrategies, nombre)) and not nombre.startswith("_")
        ]
        pattern_methods = [
            nombre for nombre in dir(CandlestickPatterns)
            if callable(getattr(CandlestickPatterns, nombre)) and not nombre.startswith("_")
        ]
        # Sección de estrategias Forex con cabecera alineada
        header_frame = ttk.Frame(parent_frame)
        header_frame.pack(fill="x", pady=(0, 5))
        
        # Título a la izquierda
        forex_label = ttk.Label(
            header_frame,
            text="Estrategias Forex:",
            font=("Arial", 9, "bold")
        )
        forex_label.pack(side="left", anchor="w")
        
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
        self.pattern_vars = {}   # Candlestick patterns
        
        # Estrategias Forex (todas las públicas)
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
            risk_frame.pack(side="right", padx=(10, 0))
            
            # Almacenar las variables de control
            self.risk_vars[strategy] = risk_var
            self.rr_vars[strategy] = rr_var
        
        # Separador
        ttk.Separator(parent_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Sección de Candle Strategies
        candle_label = ttk.Label(
            parent_frame,
            text="Candle Strategies:",
            font=("Arial", 9, "bold")
        )
        candle_label.pack(anchor="w", pady=(0, 5))

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

        # Separador
        ttk.Separator(parent_frame, orient='horizontal').pack(fill='x', pady=10)

        # Sección de patrones de velas
        candle_label = ttk.Label(
            parent_frame,
            text="Patrones de Velas:",
            font=("Arial", 9, "bold")
        )
        candle_label.pack(anchor="w", pady=(0, 5))
        
        # Patrones de velas (todos los públicos)
        for pattern in sorted(pattern_methods):
            var = tk.BooleanVar()
            self.pattern_vars[pattern] = var
            cb = ttk.Checkbutton(
                parent_frame,
                text=pattern.replace('_', ' ').capitalize(),
                variable=var,
                onvalue=True,
                offvalue=False
            )
            cb.pack(anchor="w", padx=(20, 0), pady=2)

        # Habilitar/deshabilitar botón Aceptar según condiciones completas
        def _vars_changed(*_):
            self._recompute_accept_state()

        for v in list(self.strategy_vars.values()) + list(self.candle_vars.values()) + list(self.pattern_vars.values()):
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
        # 2) Alguna estrategia o patrón seleccionado
        any_fx = any(v.get() for v in getattr(self, 'strategy_vars', {}).values()) if hasattr(self, 'strategy_vars') else False
        any_cd = any(v.get() for v in getattr(self, 'candle_vars', {}).values()) if hasattr(self, 'candle_vars') else False
        any_pt = any(v.get() for v in getattr(self, 'pattern_vars', {}).values()) if hasattr(self, 'pattern_vars') else False
        has_selection = any_fx or any_cd or any_pt
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
                msgs.append("• Seleccione al menos una estrategia o un patrón")
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
                riesgo = float(self.risk_vars[metodo].get() or 0.0) / (100 if float(self.risk_vars[metodo].get() or 0.0) > 1.0 else 1.0)
                rr = float(self.rr_vars[metodo].get() or 0.0)
                seleccion_fx[metodo] = {"tipo": "forex", "riesgo": riesgo, "rr": rr}

        seleccion_candle = []
        for metodo, var in getattr(self, 'candle_vars', {}).items():
            if var.get():
                seleccion_candle.append(metodo)

        seleccion_patterns = []
        for metodo, var in self.pattern_vars.items():
            if var.get():
                seleccion_patterns.append(metodo)

        max_orders = int(self.max_orders.get()) if hasattr(self, 'max_orders') else 5
        # Parám. de parada
        use_winrate = bool(self.use_winrate_var.get()) if hasattr(self, 'use_winrate_var') else False
        winrate = self._parse_positive_float(self.winrate_var.get()) if hasattr(self, 'winrate_var') else 0.0
        # Modelo seleccionado (si hay)
        selected_model_path = self.selected_model if hasattr(self, 'selected_model') else None

        # Opciones avanzadas
        try:
            max_attempts = int(str(getattr(self, 'max_attempts_var', tk.StringVar(value='0')).get()).strip())
            if max_attempts < 0:
                max_attempts = 0
        except Exception:
            max_attempts = 0
        seed_val = None
        try:
            seed_txt = str(getattr(self, 'seed_var', tk.StringVar(value='')).get()).strip()
            seed_val = int(seed_txt) if seed_txt != "" else None
        except Exception:
            seed_val = None
        save_best = bool(getattr(self, 'save_best_var', tk.BooleanVar(value=True)).get())

        if self.on_accept_callback:
            # Intentar con la firma más completa primero (sin iteraciones)
            try:
                # Intento 1: pasar con argumentos con nombre, incluyendo seleccion_candle si la firma lo permite
                try:
                    self.on_accept_callback(
                        seleccion_fx=seleccion_fx,
                        seleccion_patterns=seleccion_patterns,
                        max_orders=max_orders,
                        use_winrate=use_winrate,
                        winrate=winrate,
                        selected_model_path=selected_model_path,
                        max_attempts=max_attempts,
                        seed_val=seed_val,
                        save_best=save_best,
                        seleccion_candle=seleccion_candle,
                    )
                except TypeError:
                    # Intento 2: sin seleccion_candle
                    try:
                        self.on_accept_callback(
                            seleccion_fx=seleccion_fx,
                            seleccion_patterns=seleccion_patterns,
                            max_orders=max_orders,
                            use_winrate=use_winrate,
                            winrate=winrate,
                            selected_model_path=selected_model_path,
                            max_attempts=max_attempts,
                            seed_val=seed_val,
                            save_best=save_best,
                        )
                    except TypeError:
                        # Intento 3: última compatibilidad con 3 parámetros
                        try:
                            self.on_accept_callback(seleccion_fx, seleccion_patterns, max_orders)
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
