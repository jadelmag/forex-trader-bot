# app/ai_training_modal.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.font import Font
import os
import shutil

from .progress_modal import centrar_ventana


class AITrainingModal(tk.Toplevel):
    def __init__(self, parent, on_accept_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.on_accept_callback = on_accept_callback
        self.selected_model = None
        self.title("Entrenamiento de IA")
        
        # Tamaño y posición inicial
        self.width = 500
        self.height = 700
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
        
        # Configurar el desplazamiento con la rueda del ratón
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Frame para el número máximo de órdenes
        orders_frame = ttk.Frame(content_frame)
        orders_frame.pack(fill="x", pady=(15, 5))
        
        ttk.Label(orders_frame, text="Máximo de órdenes simultáneas:").pack(side="left", padx=(0, 10))
        
        self.max_orders = tk.StringVar(value="5")
        orders_spinbox = ttk.Spinbox(
            orders_frame,
            from_=1,
            to=20,
            textvariable=self.max_orders,
            width=5
        )
        orders_spinbox.pack(side="left")
        
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

        # Configurar estilos
        self._setup_styles()
        
        # Verificar si hay modelos en la carpeta models_rl
        self._check_rl_models()

    def _setup_styles(self):
        """Configura los estilos para los widgets"""
        style = ttk.Style()
        
        # Estilo para el frame de estado
        style.configure('Status.TFrame', background='#f0f0f0')
        style.configure('Status.TLabel', background='#f0f0f0')
        
        # Fuente para los iconos
        self.icon_font = Font(family="Arial", size=12, weight="bold")

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
        # self.btn_accept.config(state="normal")
        
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
        
        # Inicializar diccionarios para almacenar las variables de control
        self.strategies = [
            'Estrategia 1', 'Estrategia 2', 'Estrategia 3', 'Estrategia 4', 'Estrategia 5',
            'Estrategia 6', 'Estrategia 7', 'Estrategia 8', 'Estrategia 9', 'Estrategia 10'
        ]
        self.strategy_vars = {}
        self.risk_vars = {}
        self.rr_vars = {}
        
        # Estrategias Forex (ejemplo)
        forex_strategies = [
            "Media Móvil Simple (SMA)",
            "Media Móvil Exponencial (EMA)",
            "Bandas de Bollinger",
            "RSI (Índice de Fuerza Relativa)",
            "MACD (Media Móvil de Convergencia/Divergencia)",
            "Estocástico",
            "Ichimoku Cloud"
        ]
        
        for strategy in forex_strategies:
            # Frame para cada estrategia
            strategy_frame = ttk.Frame(parent_frame)
            strategy_frame.pack(fill="x", pady=2)
            
            # Checkbox de la estrategia
            var = tk.BooleanVar()
            self.strategy_vars[strategy] = var
            cb = ttk.Checkbutton(
                strategy_frame,
                text=strategy,
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
        
        # Sección de patrones de velas
        candle_label = ttk.Label(
            parent_frame,
            text="Patrones de Velas:",
            font=("Arial", 9, "bold")
        )
        candle_label.pack(anchor="w", pady=(0, 5))
        
        # Patrones de velas (ejemplo)
        candle_patterns = [
            "Martillo (Hammer)",
            "Hombre Colgado (Hanging Man)",
            "Estrella Fugaz (Shooting Star)",
            "Envolvente Alcista (Bullish Engulfing)",
            "Envolvente Bajista (Bearish Engulfing)",
            "Harami Alcista (Bullish Harami)",
            "Harami Bajista (Bearish Harami)",
            "Estrella de la Mañana (Morning Star)",
            "Estrella de la Tarde (Evening Star)",
            "Tres Soldados Blancos (Three White Soldiers)",
            "Tres Cuervos Negros (Three Black Crows)"
        ]
        
        for pattern in candle_patterns:
            var = tk.BooleanVar()
            self.strategy_vars[pattern] = var
            cb = ttk.Checkbutton(
                parent_frame,
                text=pattern,
                variable=var,
                onvalue=True,
                offvalue=False
            )
            cb.pack(anchor="w", padx=(20, 0), pady=2)
    
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
            self.btn_accept.config(state="disabled")

    def _on_accept(self):
        """Maneja el evento de aceptar"""
        if self.on_accept_callback and self.selected_model:
            self.on_accept_callback(self.selected_model)
        self.destroy()

    def show(self):
        """Muestra el modal"""
        self.wait_window()
        return None
