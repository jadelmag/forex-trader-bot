# app/config_app_modal.py

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from pathlib import Path
from datetime import datetime

from .progress_modal import centrar_ventana


class ConfigAppModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Configuración Forex Trader Bot")
        self.geometry("400x450")
        self.resizable(False, False)
        self.grab_set()  # Modal
        
        # Centrar sobre ventana principal
        centrar_ventana(self, parent)
        
        # Configurar el archivo de configuración
        self.config_dir = Path(__file__).parent.parent / "config"
        self.config_file = self.config_dir / "app_config.json"
        
        # Crear directorio config si no existe
        self.config_dir.mkdir(exist_ok=True)
        
        # Variables para los campos
        self.capital_limit_var = tk.StringVar(value="100")
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.hours_var = tk.StringVar(value="0")
        self.password_visible = False
        
        # Cargar configuración existente
        self._cargar_configuracion()
        
        # Crear la interfaz
        self._crear_interfaz()
        
    def _crear_interfaz(self):
        """Crear la interfaz del modal"""
        # Título principal
        title_label = tk.Label(self, text="Configuración Forex Trader Bot", 
                              font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=20)
        
        # Frame principal para los campos
        main_frame = tk.Frame(self)
        main_frame.pack(padx=30, pady=10, fill="both", expand=True)
        
        # Campo Límite de dinero para operaciones
        tk.Label(main_frame, text="Límite de dinero para realizar operaciones:", 
                font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # Frame para límite de capital y botón aplicar
        capital_frame = tk.Frame(main_frame)
        capital_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        capital_frame.columnconfigure(0, weight=1)
        
        self.capital_limit_entry = tk.Entry(capital_frame, textvariable=self.capital_limit_var, 
                                          width=30, font=("Segoe UI", 10))
        self.capital_limit_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # Botón Aplicar
        self.btn_aplicar = ttk.Button(capital_frame, text="Aplicar", 
                                     command=self._aplicar_limite_capital)
        self.btn_aplicar.grid(row=0, column=1, sticky="e")
        
        # Campo Email
        tk.Label(main_frame, text="Correo electrónico:", 
                font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=(0, 5))
        self.email_entry = tk.Entry(main_frame, textvariable=self.email_var, 
                                   width=40, font=("Segoe UI", 10))
        self.email_entry.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        
        # Campo Contraseña con icono de ojo
        tk.Label(main_frame, text="Contraseña de correo:", 
                font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w", pady=(0, 5))
        
        # Frame para contraseña y botón de ojo
        password_frame = tk.Frame(main_frame)
        password_frame.grid(row=5, column=0, sticky="ew", pady=(0, 15))
        password_frame.columnconfigure(0, weight=1)
        
        self.password_entry = tk.Entry(password_frame, textvariable=self.password_var, 
                                      show="*", font=("Segoe UI", 10))
        self.password_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Botón de ojo para mostrar/ocultar contraseña
        self.eye_button = tk.Button(password_frame, text="👁", 
                                   command=self._toggle_password_visibility,
                                   font=("Segoe UI", 10), width=3, height=1,
                                   relief="flat", bg="#f0f0f0", cursor="hand2")
        self.eye_button.grid(row=0, column=1, sticky="ns")
        
        # Campo Horas para envío de correo
        tk.Label(main_frame, text="Horas para envío de informe (0 = desactivado):", 
                font=("Segoe UI", 10)).grid(row=6, column=0, sticky="w", pady=(0, 5))
        self.hours_entry = tk.Entry(main_frame, textvariable=self.hours_var, 
                                   width=40, font=("Segoe UI", 10))
        self.hours_entry.grid(row=7, column=0, sticky="ew", pady=(0, 15))
        
        # Configurar expansión de columnas
        main_frame.columnconfigure(0, weight=1)
        
        # Botones Cancelar y Aceptar
        frame_btn = tk.Frame(self)
        frame_btn.pack(pady=10)
        btn_cancelar = ttk.Button(frame_btn, text="Cancelar", command=self._cancelar)
        btn_cancelar.pack(side="left", padx=10)
        btn_guardar = ttk.Button(frame_btn, text="Guardar", command=self._guardar)
        btn_guardar.pack(side="left", padx=10)
        
        # Validación para el campo de horas y capital
        self.hours_entry.bind('<KeyRelease>', self._validar_horas)
        self.capital_limit_entry.bind('<KeyRelease>', self._validar_capital_limit)
        
    def _toggle_password_visibility(self):
        """Alternar visibilidad de la contraseña"""
        if self.password_visible:
            # Ocultar contraseña
            self.password_entry.config(show="*")
            self.eye_button.config(text="👁")
            self.password_visible = False
        else:
            # Mostrar contraseña
            self.password_entry.config(show="")
            self.eye_button.config(text="🙈")
            self.password_visible = True
        
    def _validar_horas(self, event=None):
        """Validar que el campo de horas contenga solo números"""
        valor = self.hours_var.get()
        if valor and not valor.isdigit():
            # Eliminar caracteres no numéricos
            nuevo_valor = ''.join(c for c in valor if c.isdigit())
            self.hours_var.set(nuevo_valor)
    
    def _validar_capital_limit(self, event=None):
        """Validar que el campo de límite de capital contenga solo números"""
        valor = self.capital_limit_var.get()
        if valor and not valor.replace('.', '').isdigit():
            # Permitir solo números y un punto decimal
            nuevo_valor = ''
            punto_encontrado = False
            for c in valor:
                if c.isdigit():
                    nuevo_valor += c
                elif c == '.' and not punto_encontrado:
                    nuevo_valor += c
                    punto_encontrado = True
            self.capital_limit_var.set(nuevo_valor)
    
    def _aplicar_limite_capital(self):
        """Aplicar el límite de capital a los archivos correspondientes"""
        try:
            capital_limit_str = self.capital_limit_var.get().strip()
            if not capital_limit_str:
                messagebox.showerror("Error", "Por favor, ingrese un límite de capital válido.")
                return
            
            try:
                capital_limit = float(capital_limit_str)
                if capital_limit <= 0:
                    messagebox.showerror("Error", "El límite de capital debe ser mayor que 0.")
                    return
            except ValueError:
                messagebox.showerror("Error", "El límite de capital debe ser un número válido.")
                return
            
            # Actualizar risk_manager.py
            self._actualizar_risk_manager(capital_limit)
            
            # Actualizar gui_main.py
            self._actualizar_gui_main(capital_limit)
            
            # Guardar en configuración
            self._guardar_limite_capital(capital_limit)
            
            messagebox.showinfo("Éxito", f"Límite de capital actualizado a ${capital_limit:,.2f} correctamente.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al aplicar el límite de capital: {str(e)}")
    
    def _cargar_configuracion(self):
        """Cargar configuración existente desde el archivo JSON"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                self.capital_limit_var.set(str(config.get('capital_limit', 100)))
                self.email_var.set(config.get('email', ''))
                self.password_var.set(config.get('password', ''))
                self.hours_var.set(str(config.get('report_hours', 0)))
                
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
            # En caso de error, usar valores por defecto
            self.capital_limit_var.set('100')
            self.email_var.set('')
            self.password_var.set('')
            self.hours_var.set('0')
    
    def _actualizar_risk_manager(self, capital_limit):
        """Actualizar el archivo risk_manager.py con el nuevo límite de capital"""
        risk_manager_path = Path(__file__).parent.parent / "strategies" / "risk_manager.py"
        
        with open(risk_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar y reemplazar la línea del límite de capital
        import re
        pattern = r'if self\.capital < \d+(\.\d+)?:'
        replacement = f'if self.capital < {capital_limit}:'
        content = re.sub(pattern, replacement, content)
        
        with open(risk_manager_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _actualizar_gui_main(self, capital_limit):
        """Actualizar el archivo gui_main.py con el nuevo límite de capital"""
        gui_main_path = Path(__file__).parent / "gui_main.py"
        
        with open(gui_main_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar y reemplazar la línea del límite de capital
        import re
        pattern = r'if self\.dinero_ficticio <= \d+(\.\d+)?:'
        replacement = f'if self.dinero_ficticio <= {capital_limit}:'
        content = re.sub(pattern, replacement, content)
        
        with open(gui_main_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _guardar_limite_capital(self, capital_limit):
        """Guardar el límite de capital en la configuración"""
        try:
            # Cargar configuración existente
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # Actualizar límite de capital
            config['capital_limit'] = capital_limit
            config['last_updated'] = str(datetime.now())
            
            # Guardar configuración
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error al guardar límite de capital: {e}")
    
    def _guardar(self):
        """Guardar la configuración en archivo JSON"""
        try:
            # Validar campos
            email = self.email_var.get().strip()
            password = self.password_var.get().strip()
            hours_str = self.hours_var.get().strip()
            
            # Validar email (básico)
            if email and '@' not in email:
                messagebox.showerror("Error", "Por favor, ingrese un correo electrónico válido.")
                return
            
            # Validar horas
            try:
                hours = int(hours_str) if hours_str else 0
                if hours < 0:
                    messagebox.showerror("Error", "Las horas deben ser un número positivo o 0.")
                    return
            except ValueError:
                messagebox.showerror("Error", "Las horas deben ser un número válido.")
                return
            
            # Si se configuran email y password, validar que ambos estén presentes
            if (email and not password) or (password and not email):
                messagebox.showerror("Error", "Si configura el correo, debe proporcionar tanto el email como la contraseña.")
                return
            
            # Validar límite de capital
            capital_limit_str = self.capital_limit_var.get().strip()
            try:
                capital_limit = float(capital_limit_str) if capital_limit_str else 100
                if capital_limit <= 0:
                    messagebox.showerror("Error", "El límite de capital debe ser mayor que 0.")
                    return
            except ValueError:
                messagebox.showerror("Error", "El límite de capital debe ser un número válido.")
                return
            
            # Crear configuración
            config = {
                'capital_limit': capital_limit,
                'email': email,
                'password': password,
                'report_hours': hours,
                'last_updated': str(datetime.now())
            }
            
            # Guardar en archivo JSON
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            messagebox.showinfo("Éxito", "Configuración guardada correctamente.")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar la configuración: {str(e)}")
    
    def _cancelar(self):
        """Cancelar y cerrar el modal"""
        self.destroy()
    
    @staticmethod
    def get_config():
        """Método estático para obtener la configuración actual"""
        config_dir = Path(__file__).parent.parent / "config"
        config_file = config_dir / "app_config.json"
        
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    'capital_limit': 100,
                    'email': '',
                    'password': '',
                    'report_hours': 0
                }
        except Exception as e:
            print(f"Error al leer configuración: {e}")
            return {
                'capital_limit': 100,
                'email': '',
                'password': '',
                'report_hours': 0
            }