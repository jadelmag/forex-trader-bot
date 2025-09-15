# app/gui/components/progress_bar.py
import tkinter as tk
from tkinter import ttk

class ProgressBar:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.is_visible = False
        
        self._create_progress_components()
        
    def _create_progress_components(self):
        """Crea los componentes de la barra de progreso"""
        # Frame contenedor para la barra de progreso
        self.progress_frame = tk.Frame(self.parent_frame, bg="#F0F0F0")
        
        # Variable para el progreso
        self.progress_var = tk.IntVar(value=0)
        
        # Barra de progreso
        self.progressbar = ttk.Progressbar(
            self.progress_frame,
            orient='horizontal',
            mode='determinate',
            maximum=100,
            variable=self.progress_var,
            length=300,
        )
        self.progressbar.pack(side="left", padx=(0, 10))
        
        # Etiqueta para mostrar el porcentaje y texto
        self.progress_label = tk.Label(
            self.progress_frame,
            text="0%",
            bg="#F0F0F0",
            fg="black",
            font=("Segoe UI", 9)
        )
        self.progress_label.pack(side="left")
        
    def show(self, position="top"):
        """Muestra la barra de progreso"""
        if not self.is_visible:
            if position == "top":
                self.progress_frame.pack(side="top", fill="x", padx=10, pady=(5, 0))
            elif position == "bottom":
                self.progress_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 5))
            else:
                self.progress_frame.pack(fill="x", padx=10, pady=5)
            self.is_visible = True
            
    def hide(self):
        """Oculta la barra de progreso"""
        if self.is_visible:
            self.progress_frame.pack_forget()
            self.is_visible = False
            
    def update_progress(self, value, text=""):
        """Actualiza el progreso y el texto"""
        # Asegurar que el valor esté en el rango correcto
        value = max(0, min(100, value))
        self.progress_var.set(value)
        
        if text:
            self.progress_label.config(text=f"{value}% - {text}")
        else:
            self.progress_label.config(text=f"{value}%")
            
        # Forzar actualización de la interfaz
        self.parent_frame.update_idletasks()
        
    def set_indeterminate(self, enable=True):
        """Cambia entre modo determinado e indeterminado"""
        if enable:
            self.progressbar.config(mode='indeterminate')
            self.progressbar.start(10)  # Velocidad de animación
            self.progress_label.config(text="Procesando...")
        else:
            self.progressbar.stop()
            self.progressbar.config(mode='determinate')
            
    def reset(self):
        """Reinicia la barra de progreso"""
        self.progress_var.set(0)
        self.progress_label.config(text="0%")
        if self.progressbar.cget('mode') == 'indeterminate':
            self.progressbar.stop()
            self.progressbar.config(mode='determinate')
            
    def complete(self, message="Completado"):
        """Marca la barra como completada"""
        self.progress_var.set(100)
        self.progress_label.config(text=f"100% - {message}")
        
    def set_color(self, color="blue"):
        """Cambia el color de la barra de progreso (si es soportado)"""
        try:
            style = ttk.Style()
            style.configure("Custom.Horizontal.TProgressbar", 
                          troughcolor='lightgray',
                          background=color)
            self.progressbar.config(style="Custom.Horizontal.TProgressbar")
        except Exception:
            pass  # Ignorar si no se puede cambiar el color
            
    def update_progress_with_throttling(self, value, text="", throttle_ms=100):
        """Actualiza la barra de progreso con throttling para evitar sobrecarga"""
        try:
            import time
            current_time = time.time() * 1000  # Convertir a milisegundos
            
            if not hasattr(self, '_last_progress_update'):
                self._last_progress_update = 0
                
            # Solo actualizar si ha pasado el tiempo de throttling
            if current_time - self._last_progress_update >= throttle_ms:
                self.update_progress(value, text)
                self._last_progress_update = current_time
        except Exception as e:
            print(f"Error en actualización de progreso con throttling: {str(e)}")
            
    def set_progress_color(self, color):
        """Establece el color de la barra de progreso"""
        try:
            # Configurar estilo de color para la barra de progreso
            style = ttk.Style()
            style.configure("Colored.Horizontal.TProgressbar", foreground=color, background=color)
            self.progressbar.configure(style="Colored.Horizontal.TProgressbar")
        except Exception as e:
            print(f"Error estableciendo color de progreso: {str(e)}")
            
    def animate_progress(self, start_value, end_value, duration_ms=1000, steps=20):
        """Anima la barra de progreso de un valor a otro"""
        try:
            step_size = (end_value - start_value) / steps
            step_delay = duration_ms // steps
            
            def animate_step(current_step):
                if current_step <= steps:
                    current_value = start_value + (step_size * current_step)
                    self.update_progress(current_value)
                    
                    # Programar siguiente paso
                    if hasattr(self, 'parent_frame') and self.parent_frame.winfo_exists():
                        self.parent_frame.after(step_delay, lambda: animate_step(current_step + 1))
                        
            animate_step(0)
        except Exception as e:
            print(f"Error en animación de progreso: {str(e)}")
            
    def reset_progress_style(self):
        """Resetea el estilo de la barra de progreso al predeterminado"""
        try:
            self.progressbar.configure(style="TProgressbar")
        except Exception as e:
            print(f"Error reseteando estilo de progreso: {str(e)}")
            
    def pulse(self, duration_ms=2000):
        """Hace un efecto de pulso en la barra de progreso"""
        try:
            original_mode = self.progressbar.cget('mode')
            self.progressbar.config(mode='indeterminate')
            self.progressbar.start(10)
            
            def restore_mode():
                self.progressbar.stop()
                self.progressbar.config(mode=original_mode)
                
            if hasattr(self, 'parent_frame') and self.parent_frame.winfo_exists():
                self.parent_frame.after(duration_ms, restore_mode)
        except Exception as e:
            print(f"Error en efecto de pulso: {str(e)}")