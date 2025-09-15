# app/gui/components/telegram_panel.py
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from ..utils.constants import COLORS

class TelegramPanel:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        
        self._create_telegram_panel()
        self._create_telegram_components()
        
    def _create_telegram_panel(self):
        """Crea el panel lateral de Telegram"""
        self.frame_telegram_panel = tk.Frame(
            self.parent_frame, 
            bg=COLORS['LOG_BACKGROUND'], 
            relief="sunken", 
            bd=1, 
            width=360
        )
        self.frame_telegram_panel.pack(side="right", fill="y")
        self.frame_telegram_panel.pack_propagate(False)
        
    def _create_telegram_components(self):
        """Crea los componentes del panel de Telegram"""
        # Cabecera panel telegram
        tk.Label(
            self.frame_telegram_panel, 
            text="Telegram", 
            bg=COLORS['LOG_BACKGROUND'], 
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=10, pady=(10,5))
        
        # Estado de conexión
        self.telegram_status_frame = tk.Frame(self.frame_telegram_panel, bg=COLORS['LOG_BACKGROUND'])
        self.telegram_status_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        tk.Label(self.telegram_status_frame, text="Estado:", bg=COLORS['LOG_BACKGROUND']).pack(side="left")
        self.lbl_telegram_status = tk.Label(
            self.telegram_status_frame, 
            text="Desconectado", 
            fg="red", 
            bg=COLORS['LOG_BACKGROUND']
        )
        self.lbl_telegram_status.pack(side="left", padx=5)
        
        self.btn_telegram_connect = ttk.Button(
            self.frame_telegram_panel, 
            text="Conectar Telegram", 
            command=self.conectar_telegram, 
            state="disabled", 
            style='Small.TButton'
        )
        self.btn_telegram_connect.pack(fill="x", padx=5, pady=2)

        # Link de invitación + copiar
        link_frame = tk.Frame(self.frame_telegram_panel, bg=COLORS['LOG_BACKGROUND'])
        link_frame.pack(fill="x", padx=10, pady=(10, 0))
        
        tk.Label(link_frame, text="Enlace de invitación:", bg=COLORS['LOG_BACKGROUND']).pack(anchor="w")
        
        self.var_invite = tk.StringVar(value="(sin conectar)")
        self.lbl_invite = tk.Label(
            link_frame, 
            textvariable=self.var_invite, 
            bg=COLORS['LOG_BACKGROUND'], 
            fg="#0066CC", 
            wraplength=320, 
            justify="left"
        )
        self.lbl_invite.pack(fill="x")
        
        self.btn_copy_link = ttk.Button(
            link_frame, 
            text="Copiar", 
            command=self._copy_invite_link, 
            state="disabled", 
            style='Small.TButton'
        )
        self.btn_copy_link.pack(anchor="e", pady=(2, 0), padx=2)

        # Área de mensajes tipo canal
        tk.Label(
            self.frame_telegram_panel, 
            text="Mensajes del canal:", 
            bg=COLORS['LOG_BACKGROUND']
        ).pack(anchor="w", padx=10, pady=(10,0))
        
        self.text_telegram = tk.Text(
            self.frame_telegram_panel, 
            height=10, 
            bg="black", 
            fg="white", 
            state="disabled", 
            font=("Consolas", 10)
        )
        
        self.scroll_telegram = ttk.Scrollbar(
            self.frame_telegram_panel, 
            orient="vertical", 
            style="Logs.Vertical.TScrollbar", 
            command=self.text_telegram.yview
        )
        self.text_telegram.configure(yscrollcommand=self.scroll_telegram.set)
        
        # Layout del área de mensajes
        msg_frame = tk.Frame(self.frame_telegram_panel, bg=COLORS['LOG_BACKGROUND'])
        msg_frame.pack(fill="both", expand=True, padx=10, pady=(5,10))
        self.text_telegram.pack(in_=msg_frame, side="left", fill="both", expand=True)
        self.scroll_telegram.pack(in_=msg_frame, side="right", fill="y")
        
    def conectar_telegram(self):
        """Intenta conectar con el bot de Telegram"""
        try:
            self.log_telegram_message("Conectando con Telegram...")
            self.lbl_telegram_status.config(text="Conectando...", fg="orange")
            self.btn_telegram_connect.config(state="disabled")
            
            # Simular conexión exitosa después de 1 segundo
            self.frame_telegram_panel.after(1000, self._on_telegram_connected)
            
        except Exception as e:
            self.log_telegram_message(f"Error al conectar con Telegram: {str(e)}")
            self.lbl_telegram_status.config(text="Error de conexión", fg="red")
            self.btn_telegram_connect.config(state="normal")
    
    def _on_telegram_connected(self):
        """Se llama cuando la conexión con Telegram es exitosa"""
        self.lbl_telegram_status.config(text="Conectado", fg="green")
        self.btn_telegram_connect.config(text="Desconectar", command=self.desconectar_telegram, state="normal")
        self.btn_copy_link.config(state="normal")
        self.var_invite.set("https://t.me/mi_bot_forex?start=token_unico_123456")
        self.log_telegram_message("Conexión con Telegram establecida correctamente")
    
    def desconectar_telegram(self):
        """Desconecta el bot de Telegram"""
        try:
            self.log_telegram_message("Desconectando de Telegram...")
            # Aquí iría la lógica de desconexión
            self.lbl_telegram_status.config(text="Desconectado", fg="red")
            self.btn_telegram_connect.config(text="Conectar Telegram", command=self.conectar_telegram, state="normal")
            self.btn_copy_link.config(state="disabled")
            self.var_invite.set("(sin conectar)")
            self.log_telegram_message("Desconectado de Telegram")
        except Exception as e:
            self.log_telegram_message(f"Error al desconectar de Telegram: {str(e)}")
    
    def _copy_invite_link(self):
        """Copia el enlace de invitación al portapapeles"""
        try:
            self.frame_telegram_panel.clipboard_clear()
            self.frame_telegram_panel.clipboard_append(self.var_invite.get())
            self.log_telegram_message("Enlace copiado al portapapeles")
        except Exception as e:
            self.log_telegram_message(f"Error al copiar el enlace: {str(e)}")
    
    def log_telegram_message(self, message: str):
        """Añade un mensaje al área de mensajes de Telegram"""
        try:
            self.text_telegram.config(state="normal")
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.text_telegram.insert("end", f"[{timestamp}] {message}\n")
            self.text_telegram.see("end")
            self.text_telegram.config(state="disabled")
        except Exception as e:
            print(f"Error al mostrar mensaje en Telegram: {e}")