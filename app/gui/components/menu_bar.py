# app/gui/components/menu_bar.py
import tkinter as tk
from tkinter import ttk

class MenuBar:
    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        
        # Frames para organizar los botones
        self.frame_left = tk.Frame(parent_frame, bg="#F0F0F0")
        self.frame_left.pack(side="left", anchor="w")
        
        self.frame_center = tk.Frame(parent_frame, bg="#F0F0F0")
        self.frame_center.pack(side="left", padx=10)
        
        self.frame_right = tk.Frame(parent_frame, bg="#F0F0F0")
        self.frame_right.pack(side="right", anchor="e")
        
        self._create_menus()
        
    def _create_menus(self):
        """Crea los menús de la aplicación"""
        self._create_process_menu()
        self._create_streamer_menu()
        self._create_money_section()
        self._create_options_menu()
        self._create_ai_menu()
        self._create_telegram_button()
        self._create_restart_button()
        
    def _create_process_menu(self):
        """Crea el menú de procesamiento de datos"""
        self.btn_procesar_datos = ttk.Menubutton(self.frame_left, text="Procesar datos")
        self.btn_procesar_datos.pack(side="left", padx=5)
        self.menu_procesar_datos = tk.Menu(self.btn_procesar_datos, tearoff=0)
        self.btn_procesar_datos.configure(menu=self.menu_procesar_datos)
        
        # Añadir opciones al menú
        self.menu_procesar_datos.add_command(
            label="Cargar CSV", 
            command=self.main_app.csv_handler.cargar_csv
        )
        self.menu_procesar_datos.add_command(
            label="Cargar datos procesados", 
            command=self.main_app.csv_handler.cargar_procesados
        )
        self.menu_procesar_datos.add_separator()
        self.menu_procesar_datos.add_command(
            label="Guardar datos procesados", 
            command=self.main_app.csv_handler.guardar_procesados
        )
        self.menu_procesar_datos.add_command(
            label="Procesar CSV a PKL", 
            command=self.main_app.csv_handler.abrir_modal_csv_a_pkl
        )
        
    def _create_streamer_menu(self):
        """Crea el menú del CandleStreamer"""
        self.btn_streamer = ttk.Menubutton(self.frame_left, text="Candle Streamer")
        self.btn_streamer.pack(side="left", padx=5)
        self.menu_streamer = tk.Menu(self.btn_streamer, tearoff=0)
        self.btn_streamer.configure(menu=self.menu_streamer)
        
        # Añadir opciones al menú
        self.menu_streamer.add_command(label="Conectar", command=self.main_app.simulation_handler.iniciar_streamer)
        self.menu_streamer.add_command(label="Desconectar", command=self.main_app.simulation_handler.detener_streamer, state="disabled")
        self.menu_streamer.add_command(label="Cambiar símbolo/intervalo", command=self.main_app.simulation_handler.cambiar_config_streamer, state="disabled")
        self.menu_streamer.add_separator()
        self.menu_streamer.add_command(label="Iniciar simulación Binance", command=self.main_app.simulation_handler.iniciar_simulacion_binance, state="disabled")
        self.menu_streamer.add_command(label="Modificar configuración simulación Binance", command=self.main_app.simulation_handler.modificar_config_simulacion_binance, state="disabled")
        self.menu_streamer.add_command(label="Detener simulación Binance", command=self.main_app.simulation_handler.detener_simulacion_binance, state="disabled")
        self.menu_streamer.add_separator()
        self.menu_streamer.add_command(label="Activar Debug", command=lambda: self.main_app.simulation_handler.toggle_debug_mode(True), state="disabled")
        self.menu_streamer.add_command(label="Desactivar Debug", command=lambda: self.main_app.simulation_handler.toggle_debug_mode(False), state="disabled")
        self.menu_streamer.add_separator()
        self.menu_streamer.add_command(label="Generar informe", command=self.main_app.simulation_handler.generar_informe, state="normal")
        self.menu_streamer.add_command(label="Configuración", command=self.main_app.simulation_handler.configuracion, state="normal")
        
        # Botón de prueba temporal
        self.test_btn = ttk.Button(self.frame_left, text="Test", command=self.main_app.simulation_handler.test_iniciar_streamer, style='Small.TButton')
        self.test_btn.pack(side="left", padx=2)
        
    def _create_money_section(self):
        """Crea la sección de dinero ficticio"""
        # Label y entry para dinero
        self.label_entry_dinero = tk.Label(self.frame_center, text="Dinero ficticio:", bg="#F0F0F0")
        self.label_entry_dinero.pack(side="left", padx=(0, 5))
        
        self.entry_dinero = ttk.Entry(self.frame_center, width=12)
        self.entry_dinero.pack(side="left", padx=5)
        
        self.btn_add_dinero = ttk.Button(
            self.frame_center, 
            text="Añadir", 
            command=self.main_app.strategy_handler.add_dinero,
            style='Small.TButton'
        )
        self.btn_add_dinero.pack(side="left", padx=2)
        
    def _create_options_menu(self):
        """Crea el menú de opciones"""
        self.btn_opciones = ttk.Menubutton(self.frame_center, text="Opciones", state="disabled")
        self.btn_opciones.pack(side="left", padx=5)
        self.menu_opciones = tk.Menu(self.btn_opciones, tearoff=0)
        self.btn_opciones.configure(menu=self.menu_opciones)
        
        # Etiquetas para controlar el estado por nombre
        self._menu_label_estrategias = "Mostrar Estrategias"
        self._menu_label_patrones = "Aplicar Patrones"
        self._menu_label_candle_strategies = "Aplicar Estrategias de velas"
        self._menu_label_backtesting = "Iniciar Backtesting"
        self._menu_label_entrenar_ia = "Entrenar IA"
        self._menu_label_detener_ia = "Detener IA"
        
        # Añadir opciones al menú
        self.menu_opciones.add_command(
            label=self._menu_label_estrategias, 
            command=self.main_app.strategy_handler.cargar_estrategias,
            state="disabled"
        )
        self.menu_opciones.add_command(
            label=self._menu_label_patrones, 
            command=self.main_app.abrir_modal_patrones,
            state="disabled"
        )
        self.menu_opciones.add_command(
            label=self._menu_label_candle_strategies, 
            command=self.main_app.abrir_modal_candle_strategies,
            state="disabled"
        )
        self.menu_opciones.add_command(
            label=self._menu_label_backtesting, 
            command=self.main_app.strategy_handler.abrir_modal_backtesting,
            state="disabled"
        )
        self.menu_opciones.add_separator()
        self.menu_opciones.add_command(
            label=self._menu_label_entrenar_ia, 
            command=self.main_app.strategy_handler.entrenar_ia,
            state="disabled"
        )
        self.menu_opciones.add_command(
            label=self._menu_label_detener_ia, 
            command=self.main_app.strategy_handler.detener_entrenamiento_ia,
            state="disabled"
        )
        
    def _create_ai_menu(self):
        """Crea el menú de IA"""
        self._ia_label_crear_rl = "Crear Modelo RL"
        self._ia_label_cargar_rl = "Cargar Modelo RL"
        self._ia_label_aplicar_rl = "Aplicar Señales RL"
        
        self.btn_modelo_ia = ttk.Menubutton(self.frame_center, text="Modelo IA", state="disabled")
        self.btn_modelo_ia.pack(side="left", padx=5)
        self.menu_modelo_ia = tk.Menu(self.btn_modelo_ia, tearoff=0)
        self.btn_modelo_ia.configure(menu=self.menu_modelo_ia)
        
        # Añadir opciones al menú
        self.menu_modelo_ia.add_command(
            label=self._ia_label_crear_rl, 
            command=self.main_app.rl_handler.entrenar_rl,
            state="disabled"
        )
        self.menu_modelo_ia.add_command(
            label=self._ia_label_cargar_rl, 
            command=self.main_app.rl_handler.cargar_rl,
            state="disabled"
        )
        self.menu_modelo_ia.add_command(
            label=self._ia_label_aplicar_rl, 
            command=self.main_app.rl_handler.aplicar_senales_rl,
            state="disabled"
        )
        
    def _create_telegram_button(self):
        """Crea el botón de Telegram"""
        self.btn_telegram = ttk.Button(
            self.frame_center, 
            text="Telegram", 
            command=self.main_app.telegram_handler.abrir_modal_telegram, 
            state="disabled", 
            style='Small.TButton'
        )
        self.btn_telegram.pack(side="left", padx=2)
        
    def _create_restart_button(self):
        """Crea el botón de reinicio"""
        self.btn_reiniciar = ttk.Button(
            self.frame_center, 
            text="Reiniciar", 
            command=self.main_app.reiniciar_app,
            style='Small.TButton'
        )
        self.btn_reiniciar.pack(side="left", padx=2)
        
    def update_buttons_state(self):
        """Actualiza el estado de los botones según las condiciones actuales"""
        # Verificar si hay datos cargados - usar csv_handler.df_actual
        has_data = hasattr(self.main_app, 'csv_handler') and self.main_app.csv_handler.df_actual is not None
        has_money = hasattr(self.main_app, 'strategy_handler') and self.main_app.strategy_handler.dinero_ficticio > 0
        
        # Habilitar/deshabilitar botones según las condiciones
        enable_analysis = has_data and has_money
        
        # Actualizar estado de botones de análisis
        if hasattr(self, 'btn_patrones'):
            self.btn_patrones.config(state="normal" if enable_analysis else "disabled")
        if hasattr(self, 'btn_estrategias'):
            self.btn_estrategias.config(state="normal" if enable_analysis else "disabled")
        if hasattr(self, 'btn_backtesting'):
            self.btn_backtesting.config(state="normal" if enable_analysis else "disabled")
            
        # Actualizar menús desplegables Opciones y Modelo IA
        state = "normal" if enable_analysis else "disabled"
        
        # Menú Opciones
        if hasattr(self, "btn_opciones"):
            self.btn_opciones.config(state=state)
            try:
                if state == "normal":
                    self.btn_opciones.state(["!disabled"])
                else:
                    self.btn_opciones.state(["disabled"])
            except Exception:
                pass
                
        # Menú Modelo IA
        if hasattr(self, "btn_modelo_ia"):
            self.btn_modelo_ia.config(state=state)
            try:
                if state == "normal":
                    self.btn_modelo_ia.state(["!disabled"])
                else:
                    self.btn_modelo_ia.state(["disabled"])
            except Exception:
                pass
                
        # Botón Telegram
        if hasattr(self, "btn_telegram"):
            self.btn_telegram.config(state=state)
            
        # Actualizar elementos dentro de los menús
        self._update_menu_items_state(enable_analysis)
            
    def _update_btn_aplicar_patrones(self):
        """Habilita 'Mostrar Patrones' solo si se han cargado procesados y se ha añadido dinero ficticio (> 0)."""
        has_data = hasattr(self.main_app, 'csv_handler') and self.main_app.csv_handler.df_actual is not None
        has_money = hasattr(self.main_app, 'strategy_handler') and self.main_app.strategy_handler.dinero_ficticio > 0
        habilitar = has_data and has_money
        
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
                
        # Sincronizar menú 'Opciones'
        if hasattr(self, "btn_opciones"):
            self.btn_opciones.config(state=state)
            try:
                if state == "normal":
                    self.btn_opciones.state(["!disabled"])
                else:
                    self.btn_opciones.state(["disabled"])
            except Exception:
                pass
                
    def _update_btn_cargar_estrategias(self):
        """Habilita 'Mostrar Estrategias' solo si se han cargado procesados y se ha añadido dinero ficticio (> 0)."""
        has_data = hasattr(self.main_app, 'csv_handler') and self.main_app.csv_handler.df_actual is not None
        has_money = hasattr(self.main_app, 'strategy_handler') and self.main_app.strategy_handler.dinero_ficticio > 0
        habilitar = has_data and has_money
        
        if hasattr(self, "btn_estrategias"):
            self.btn_estrategias.config(state="normal" if habilitar else "disabled")
        if hasattr(self, "btn_patrones"):
            self.btn_patrones.config(state="normal" if habilitar else "disabled")
            
    def _update_menu_items_state(self, enable_analysis):
        """Actualiza el estado de los elementos dentro de los menús desplegables"""
        menu_state = "normal" if enable_analysis else "disabled"
        
        # Actualizar elementos del menú Opciones
        if hasattr(self, 'menu_opciones'):
            try:
                # Cargar estrategias
                self.menu_opciones.entryconfig(self._menu_label_estrategias, state=menu_state)
                # Mostrar patrones
                self.menu_opciones.entryconfig(self._menu_label_patrones, state=menu_state)
                # Estrategias de velas
                self.menu_opciones.entryconfig(self._menu_label_candle_strategies, state=menu_state)
                # Backtesting
                self.menu_opciones.entryconfig(self._menu_label_backtesting, state=menu_state)
                # Entrenar IA - siempre habilitado si hay datos y dinero
                self.menu_opciones.entryconfig(self._menu_label_entrenar_ia, state=menu_state)
                # Detener IA - habilitado solo durante entrenamiento
                detener_state = "normal" if (enable_analysis and self._is_training_active()) else "disabled"
                self.menu_opciones.entryconfig(self._menu_label_detener_ia, state=detener_state)
            except Exception:
                pass
                
        # Actualizar elementos del menú Modelo IA
        if hasattr(self, 'menu_modelo_ia'):
            try:
                # Crear Modelo RL
                self.menu_modelo_ia.entryconfig(self._ia_label_crear_rl, state=menu_state)
                # Cargar Modelo RL
                self.menu_modelo_ia.entryconfig(self._ia_label_cargar_rl, state=menu_state)
                # Aplicar Señales RL
                self.menu_modelo_ia.entryconfig(self._ia_label_aplicar_rl, state=menu_state)
            except Exception:
                pass
                
    def _is_training_active(self):
        """Verifica si hay un entrenamiento de IA activo"""
        if hasattr(self.main_app, 'rl_handler'):
            return getattr(self.main_app.rl_handler, '_training_active', False)
        return False
        
    def _update_menu_states(self):
        """Actualiza el estado de las opciones del menú"""
        # Implementar lógica para actualizar estados del menú
        pass