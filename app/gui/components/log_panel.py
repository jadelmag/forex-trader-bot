# app/gui/components/log_panel.py
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from ..utils.constants import COLORS

class LogPanel:
    def __init__(self, parent_root):
        self.parent_root = parent_root
        self._log_height_locked = False
        
        self._create_log_frame()
        self._create_log_components()
        
    def _create_log_frame(self):
        """Crea el frame principal del panel de logs"""
        self.frame_log = tk.Frame(self.parent_root, bg=COLORS['LOG_BACKGROUND'], relief="sunken", bd=1)
        self.frame_log.pack(fill="both", expand=False, padx=20, pady=(0, 20), ipady=120)
        # Altura fija del área de log
        self.frame_log.configure(height=50)
        self.frame_log.pack_propagate(False)
        
    def _create_log_components(self):
        """Crea los componentes del panel de logs"""
        # Header del área de logs con botón en la esquina superior derecha
        self.frame_log_header = tk.Frame(self.frame_log, bg=COLORS['LOG_BACKGROUND'])
        self.frame_log_header.pack(fill="x", padx=8, pady=(6, 0))
        
        self.btn_clear_log = ttk.Button(
            self.frame_log_header, 
            text="Limpiar", 
            command=self.limpiar_log, 
            style='Small.TButton'
        )
        self.btn_clear_log.pack(side="right", padx=2, pady=1)

        # Barra de progreso compacta en el header
        self.progress_var = tk.IntVar(value=0)
        self.header_progress_frame = tk.Frame(self.frame_log_header, bg=COLORS['LOG_BACKGROUND'])
        
        self.header_progressbar = ttk.Progressbar(
            self.header_progress_frame,
            orient='horizontal',
            mode='determinate',
            maximum=100,
            variable=self.progress_var,
            length=220,
        )
        self.header_progressbar.pack(side="left", padx=(0, 6))
        
        # Etiqueta sobre la barra para mostrar el %
        self.header_progress_label = tk.Label(
            self.header_progress_frame,
            text="0%",
            bg=self.frame_log_header.cget("bg"),
            fg="black",
            bd=0,
            highlightthickness=0,
        )
        
        # Área de logs con scrollbar vertical
        self.text_log = tk.Text(
            self.frame_log,
            height=12,
            bg="black",
            fg="white",
            state="disabled",
            font=("Consolas", 10),
        )
        
        self.scrollbar_log_y = ttk.Scrollbar(
            self.frame_log,
            orient="vertical",
            style="Logs.Vertical.TScrollbar",
            command=self.text_log.yview,
        )
        self.text_log.configure(yscrollcommand=self.scrollbar_log_y.set)

        # Layout
        self.text_log.pack(side="left", fill="both", expand=True)
        self.scrollbar_log_y.pack(side="right", fill="y")
        
    def log(self, message, color="white"):
        """Añade un mensaje al área de log con el color especificado"""
        try:
            self.text_log.configure(state="normal")
            self.text_log.insert("end", message + "\n", color)
            self.text_log.tag_configure(color, foreground=color)
            self.text_log.see("end")
            self.text_log.configure(state="disabled")
        except Exception as e:
            print(f"Error al escribir en el log: {str(e)}")
            
    def limpiar_log(self):
        """Limpia el contenido del log"""
        try:
            self.text_log.configure(state="normal")
            self.text_log.delete(1.0, tk.END)
            self.text_log.configure(state="disabled")
        except Exception as e:
            print(f"Error al limpiar el log: {str(e)}")
        
    def show_progress_bar(self):
        """Muestra la barra de progreso"""
        self.header_progress_frame.pack(side="right", padx=(0, 8))
        self._place_header_progress_text()
        
    def hide_progress_bar(self):
        """Oculta la barra de progreso"""
        self.header_progress_frame.pack_forget()
        
    def update_progress(self, value, text=""):
        """Actualiza el valor de la barra de progreso"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.update_progress(value, text)
            
    def _fix_log_height_once(self):
        """Fija la altura del log una sola vez después de cargar datos"""
        if not self._log_height_locked:
            self.frame_log.configure(height=150)
            self.frame_log.pack_propagate(False)
            self._log_height_locked = True
            
    def _place_header_progress_text(self):
        """Posiciona el texto sobre la barra de progreso"""
        try:
            x = self.header_progressbar.winfo_x()
            y = self.header_progressbar.winfo_y()
            w = self.header_progressbar.winfo_width()
            h = self.header_progressbar.winfo_height()
            # Centrar el texto en la barra
            self.header_progress_label.place(x=x + w//2, y=y + h//2, anchor="center")
        except Exception:
            pass