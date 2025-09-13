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
        self.frame_center.pack(side="left", expand=True)
        
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
        
        # Añadir opciones al menú (implementación simplificada)
        self.menu_streamer.add_command(label="Conectar", command=self.main_app.simulation_handler.iniciar_streamer)
        self.menu_streamer.add_command(label="Desconectar", command=self.main_app.simulation_handler.detener_streamer, state="disabled")
        
    def _create_money_section(self):
        """Crea la sección de dinero ficticio"""
        # Label y entry para dinero
        self.label_entry_dinero = tk.Label(self.frame_right, text="Dinero ficticio:", bg="#F0F0F0")
        self.label_entry_dinero.pack(side="left", padx=5)
        
        self.entry_dinero = ttk.Entry(self.frame_right, width=12)
        self.entry_dinero.pack(side="left", padx=5)
        
        self.btn_add_dinero = ttk.Button(
            self.frame_right, 
            text="Añadir", 
            command=self.main_app.strategy_handler.add_dinero,
            style='Small.TButton'
        )
        self.btn_add_dinero.pack(side="left", padx=2)
        
    def _create_options_menu(self):
        """Crea el menú de opciones"""
        self.btn_opciones = ttk.Menubutton(self.frame_right, text="Opciones", state="disabled")
        self.btn_opciones.pack(side="left", padx=5)
        self.menu_opciones = tk.Menu(self.btn_opciones, tearoff=0)
        self.btn_opciones.configure(menu=self.menu_opciones)
        
        # Añadir opciones al menú
        self.menu_opciones.add_command(
            label="Mostrar Estrategias", 
            command=self.main_app.strategy_handler.cargar_estrategias,
            state="disabled"
        )
        self.menu_opciones.add_command(
            label="Aplicar Patrones", 
            command=self.main_app.pattern_handler.abrir_modal_patrones,
            state="disabled"
        )
        # ... más opciones
        
    def _create_ai_menu(self):
        """Crea el menú de IA"""
        self.btn_modelo_ia = ttk.Menubutton(self.frame_right, text="Modelo IA", state="disabled")
        self.btn_modelo_ia.pack(side="left", padx=5)
        self.menu_modelo_ia = tk.Menu(self.btn_modelo_ia, tearoff=0)
        self.btn_modelo_ia.configure(menu=self.menu_modelo_ia)
        
        # Añadir opciones al menú
        self.menu_modelo_ia.add_command(
            label="Crear Modelo RL", 
            command=self.main_app.rl_handler.entrenar_rl,
            state="disabled"
        )
        # ... más opciones
        
    def _create_telegram_button(self):
        """Crea el botón de Telegram"""
        self.btn_telegram = ttk.Button(
            self.frame_right, 
            text="Telegram", 
            command=self.main_app.telegram_handler.abrir_modal_telegram, 
            state="disabled", 
            style='Small.TButton'
        )
        self.btn_telegram.pack(side="left", padx=2)
        
    def _create_restart_button(self):
        """Crea el botón de reinicio"""
        self.btn_reiniciar = ttk.Button(
            self.frame_right, 
            text="Reiniciar", 
            command=self.main_app.reiniciar_app,
            style='Small.TButton'
        )
        self.btn_reiniciar.pack(side="left", padx=2)
        
    def update_buttons_state(self):
        """Actualiza el estado de los botones según el estado de la aplicación"""
        has_data = self.main_app.csv_handler.df_actual is not None
        has_money = self.main_app.strategy_handler.dinero_ficticio > 0
        
        # Habilitar/deshabilitar botones según condiciones
        state = "normal" if (has_data and has_money) else "disabled"
        
        self.btn_opciones.config(state=state)
        self.btn_modelo_ia.config(state=state)
        self.btn_telegram.config(state=state)
        
        # Actualizar estado de las opciones del menú
        self._update_menu_states()
        
    def _update_menu_states(self):
        """Actualiza el estado de las opciones del menú"""
        # Implementar lógica para actualizar estados del menú
        pass