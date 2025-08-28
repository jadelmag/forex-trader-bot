# app/gui_main.py

import tkinter as tk
from tkinter import ttk, messagebox
from .csv_manager import CSVManager
from .grafico_manager import GraficoManager
from .tooltip_zoom_pan import TooltipZoomPan
from .csv_loader_modal import CSVLoaderModal
from .patterns_modal import PatternsModal
from .strategies_modal import EstrategiasModal

# Imports externos
from strategies.strategies import ForexStrategies
from backtesting.backtester import ForexBacktester
from rl.rl_agent import RLTradingAgent


class GUIPrincipal:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Bot - CSV Data Viewer")
        self.root.geometry("1900x950")
        self.root.configure(bg="#F0F0F0")

        # Inicializaciones
        self.csv_manager = CSVManager(root)
        self.grafico_manager = GraficoManager(frame=None)
        self.tooltip_zoom_pan = None
        self.df_actual = None
        self.dinero_ficticio = 0
        self.beneficios = 0
        self.perdidas = 0
        self.rl_agent = None
        self.rl_signals = []
        self.compra_activa = None

        # Frames principales
        self.frame_controls = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_controls.pack(fill="x", padx=20, pady=10)

        self.frame_grafico = tk.Frame(self.root, bg="#FFFFFF", relief="sunken", bd=1)
        self.frame_grafico.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.grafico_manager.frame = self.frame_grafico

        self.frame_log = tk.Frame(self.root, bg="#F8F8F8", relief="sunken", bd=1)
        self.frame_log.pack(fill="both", expand=False, padx=20, pady=(0, 20), ipady=120)
        
        # Estilo exclusivo para el scrollbar de logs (no afecta botones)
        self._logs_style = ttk.Style()
        self._logs_style.configure(
            "Logs.Vertical.TScrollbar",
            troughcolor="#EFEFEF",
            background="#B5B5B5",
            bordercolor="#EFEFEF",
            lightcolor="#EFEFEF",
            darkcolor="#EFEFEF",
            arrowcolor="#7A7A7A",
        )
        self._logs_style.map(
            "Logs.Vertical.TScrollbar",
            background=[("active", "#A0A0A0"), ("pressed", "#8C8C8C")],
        )

        # Área de logs con scrollbar vertical a la derecha
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

        # Contenedores de botones
        self.frame_left = tk.Frame(self.frame_controls, bg="#F0F0F0")
        self.frame_left.pack(side="left", anchor="w")

        self.frame_center = tk.Frame(self.frame_controls, bg="#F0F0F0")
        self.frame_center.pack(side="left", expand=True)

        self.frame_right = tk.Frame(self.frame_controls, bg="#F0F0F0")
        self.frame_right.pack(side="right", anchor="e")

        # ---------------- Botones CSV (izquierda) ----------------
        self.btn_cargar_csv = ttk.Button(self.frame_left, text="Cargar CSV", command=self.cargar_csv)
        self.btn_cargar_csv.pack(side="left", padx=5)

        self.btn_cargar_procesados = ttk.Button(
            self.frame_left, text="Cargar datos procesados", command=self.cargar_procesados
        )
        self.btn_cargar_procesados.pack(side="left", padx=5)

        self.btn_guardar_procesados = ttk.Button(
            self.frame_left, text="Guardar datos procesados", command=self.guardar_procesados
        )
        self.btn_guardar_procesados.pack(side="left", padx=5)

        self.btn_reset_zoom = ttk.Button(self.frame_left, text="Reset Zoom", command=self.reset_zoom)
        self.btn_reset_zoom.pack(side="left", padx=5)

        # ---------------- Dinero/beneficios/pérdidas (centro) ----------------
        self.label_dinero = tk.Label(
            self.frame_center, text=f"Dinero: ${self.dinero_ficticio:,.2f}", fg="black", bg="#F0F0F0"
        )
        self.label_dinero.pack(side="left", padx=10)

        self.label_beneficios = tk.Label(
            self.frame_center, text=f"Beneficios: ${self.beneficios:,.2f}", fg="green", bg="#F0F0F0"
        )
        self.label_beneficios.pack(side="left", padx=10)

        self.label_perdidas = tk.Label(
            self.frame_center, text=f"Pérdidas: ${self.perdidas:,.2f}", fg="red", bg="#F0F0F0"
        )
        self.label_perdidas.pack(side="left", padx=10)

        # ---------------- Botones derecha ----------------
        self.label_entry_dinero = tk.Label(self.frame_right, text="Dinero ficticio:", bg="#F0F0F0")
        self.label_entry_dinero.pack(side="left", padx=5)
        self.entry_dinero = ttk.Entry(self.frame_right, width=10)
        self.entry_dinero.pack(side="left", padx=5)
        self.btn_add_dinero = ttk.Button(self.frame_right, text="Añadir dinero", command=self.add_dinero)
        self.btn_add_dinero.pack(side="left", padx=5)

        self.btn_cargar_estrategias = ttk.Button(
            self.frame_right, text="Mostrar Estrategias", command=self.cargar_estrategias, state="disabled"
        )
        self.btn_cargar_estrategias.pack(side="left", padx=5)

        self.btn_aplicar_patrones = ttk.Button(
            self.frame_right, text="Mostrar Patrones", command=self.abrir_modal_patrones, state="disabled"
        )
        self.btn_aplicar_patrones.pack(side="left", padx=5)

        self.btn_backtesting = ttk.Button(
            self.frame_right, text="Iniciar Backtesting", command=self.iniciar_backtesting, state="disabled"
        )
        self.btn_backtesting.pack(side="left", padx=5)

        # ---------------- Botones RL ----------------
        self.btn_entrenar_rl = ttk.Button(
            self.frame_right, text="Entrenar RL", command=self.entrenar_rl
        )
        self.btn_entrenar_rl.pack(side="left", padx=5)

        self.btn_cargar_rl = ttk.Button(
            self.frame_right, text="Cargar RL", command=self.cargar_rl
        )
        self.btn_cargar_rl.pack(side="left", padx=5)

        self.btn_aplicar_rl = ttk.Button(
            self.frame_right, text="Aplicar Señales RL", command=self.aplicar_senales_rl
        )
        self.btn_aplicar_rl.pack(side="left", padx=5)

    # ---------------- Funciones CSV ----------------
    def cargar_csv(self):
        df = self.csv_manager.cargar_csv()
        if df is not None:
            CSVLoaderModal(self.root, df, callback=self._on_csv_cargado)

    def _on_csv_cargado(self, df_seleccion):
        self.df_actual = df_seleccion
        self._dibujar_grafico(df_seleccion)
        # Habilitar botón de patrones tras cargar datos
        self.btn_aplicar_patrones.config(state="normal")
        self.btn_cargar_estrategias.config(state="normal")
        self.btn_backtesting.config(state="normal")

    def cargar_procesados(self):
        df = self.csv_manager.cargar_procesados()
        if df is not None:
            self.df_actual = df
            self._dibujar_grafico(df)
            self.btn_aplicar_patrones.config(state="normal")

    def guardar_procesados(self):
        self.csv_manager.df_cache = self.df_actual
        self.csv_manager.guardar_procesados()

    # ---------------- Funciones Dinero ----------------
    def add_dinero(self):
        try:
            cantidad = float(self.entry_dinero.get())
            self.dinero_ficticio += cantidad
            self.actualizar_labels()
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número válido")

    def actualizar_labels(self):
        self.label_dinero.config(text=f"Dinero: ${self.dinero_ficticio:,.2f}")
        self.label_beneficios.config(text=f"Beneficios: ${self.beneficios:,.2f}")
        self.label_perdidas.config(text=f"Pérdidas: ${self.perdidas:,.2f}")

    # ---------------- Funciones Estrategias ----------------
    def cargar_estrategias(self):
        if self.df_actual is None:
            messagebox.showwarning("Atención", "Cargue primero un CSV o datos procesados")
            return
        # Instanciar estrategias con el DataFrame actual
        self.strategies = ForexStrategies(self.df_actual)
        # Descubrir métodos públicos de la clase como nombres de estrategias
        estrategias_disponibles = [
            nombre for nombre in dir(ForexStrategies)
            if callable(getattr(ForexStrategies, nombre)) and not nombre.startswith("_")
        ]
        # Abrir modal con checkboxes y callback
        EstrategiasModal(self.root, estrategias_disponibles, callback=self._on_estrategias_seleccionadas)

    def _on_estrategias_seleccionadas(self, estrategias):
        """Aplica las estrategias seleccionadas sobre el DataFrame actual.
        Añade columnas <estrategia>_Signal y redibuja el gráfico, reinstalando zoom/hover.
        """
        if not estrategias or self.df_actual is None or not hasattr(self, 'strategies'):
            return

        df_new = self.df_actual.copy()

        for nombre in estrategias:
            try:
                metodo = getattr(self.strategies, nombre, None)
                if not callable(metodo):
                    continue
                df_res = metodo()
                if 'Signal' in df_res.columns:
                    col_name = f"{nombre}_Signal"
                    # Alinear por índice
                    df_new[col_name] = df_res['Signal']
                    # Loguear eventos de la estrategia
                    for idx, val in df_res['Signal'].items():
                        if val != 0:
                            close_val = df_new.loc[idx, 'Close'] if 'Close' in df_new.columns else None
                            fecha_str = idx.strftime('%d/%m/%Y') if hasattr(idx, 'strftime') else str(idx)
                            msg = f"Estrategia: {nombre} | Fecha: {fecha_str} | Señal: {val}"
                            if close_val is not None:
                                msg += f" | Close: {close_val:.5f}"
                            self.log(msg, color='cyan')
            except Exception as e:
                self.log(f"Error aplicando estrategia {nombre}: {e}", color='red')

        # Redibujar y reinstalar TooltipZoomPan
        self.grafico_manager.dibujar_csv(df_new)
        self.df_actual = df_new
        if self.tooltip_zoom_pan:
            try:
                self.tooltip_zoom_pan.cleanup()
            except Exception:
                pass
        if hasattr(self.grafico_manager, 'canvas') and hasattr(self.grafico_manager, 'grafico'):
            self.tooltip_zoom_pan = TooltipZoomPan(self.root, self.grafico_manager.canvas, self.grafico_manager.grafico)

    def iniciar_backtesting(self):
        if not hasattr(self, "strategies") or self.df_actual is None:
            messagebox.showwarning("Atención", "Cargue CSV y estrategias primero")
            return
        backtester = ForexBacktester(self.df_actual)
        resultados = backtester.compare_strategies()
        self.beneficios = sum(v - self.dinero_ficticio for v in resultados.values() if v > self.dinero_ficticio)
        self.perdidas = sum(self.dinero_ficticio - v for v in resultados.values() if v < self.dinero_ficticio)
        self.actualizar_labels()
        messagebox.showinfo("Resultados Backtesting", str(resultados))

    # ---------------- Funciones Patrones ----------------
    def abrir_modal_patrones(self):
        if self.df_actual is not None:
            # Pasar callback para reinstalar zoom/hover tras redibujar
            PatternsModal(self.root, self.df_actual, self.grafico_manager, self, callback=self._on_patrones_aplicados)
        else:
            messagebox.showwarning("Atención", "No hay datos cargados para aplicar patrones")

    # ---------------- Funciones RL ----------------
    def entrenar_rl(self):
        if self.df_actual is None:
            messagebox.showwarning("Atención", "Debe cargar un CSV primero")
            return
        self.rl_agent = RLTradingAgent(self.df_actual)
        self.rl_agent.entrenar(timesteps=50_000)
        messagebox.showinfo("RL", "Entrenamiento completado y modelo guardado")

    def cargar_rl(self):
        if self.df_actual is None:
            messagebox.showwarning("Atención", "Debe cargar un CSV primero")
            return
        self.rl_agent = RLTradingAgent(self.df_actual)
        cargado = self.rl_agent.cargar_modelo()
        if cargado:
            messagebox.showinfo("RL", "Modelo cargado correctamente")

    def aplicar_senales_rl(self):
        if self.rl_agent is None or self.df_actual is None:
            messagebox.showwarning("Atención", "Entrene o cargue primero el agente RL")
            return

        self.rl_signals = self.rl_agent.generar_senales()
        self.text_log.configure(state="normal")
        self.text_log.delete("1.0", "end")
        self.text_log.configure(state="disabled")
        self.compra_activa = None

        for i, row in self.df_actual.iterrows():
            mensaje = f"{i.strftime('%Y-%m-%d %H:%M')} | Close: {row['Close']:.5f}"
            signal = self.rl_signals[i] if i < len(self.rl_signals) else 0

            if signal == 1:
                self.compra_activa = (row["Close"], i)
                mensaje += f" | SEÑAL RL: COMPRA a {row['Close']:.5f}"
                self.log(mensaje, color="green")
            elif signal == 2 and self.compra_activa:
                precio_compra, fecha_compra = self.compra_activa
                ganancia = row["Close"] - precio_compra
                if ganancia >= 0:
                    color = "green"
                    msg_gan = f"Ganancia: +{ganancia:.5f}"
                else:
                    color = "red"
                    msg_gan = f"Pérdida: {ganancia:.5f}"
                mensaje += f" | SEÑAL RL: VENTA a {row['Close']:.5f} | {msg_gan}"
                self.log(mensaje, color=color)
                self.compra_activa = None
            else:
                self.log(mensaje, color="white")

        if self.grafico_manager:
            self.grafico_manager.dibujar_senales_rl(self.rl_signals)

    # ---------------- Funciones Gráficos ----------------
    def _dibujar_grafico(self, df):
        self.grafico_manager.dibujar_csv(df)
        self.tooltip_zoom_pan = TooltipZoomPan(self.root, self.grafico_manager.canvas, self.grafico_manager.grafico)

    def reset_zoom(self):
        if self.tooltip_zoom_pan:
            self.tooltip_zoom_pan.reset_zoom()

    def limpiar_grafico(self):
        self.df_actual = None
        if self.tooltip_zoom_pan:
            self.tooltip_zoom_pan.cleanup()
        self.tooltip_zoom_pan = None
        if hasattr(self.grafico_manager, "limpiar"):
            self.grafico_manager.limpiar()
        if hasattr(self.grafico_manager, "canvas") and self.grafico_manager.canvas:
            self.grafico_manager.canvas.get_tk_widget().pack_forget()
            self.grafico_manager.canvas = None

    # ---------------- Función Log ----------------
    def log(self, mensaje, color="white"):
        self.text_log.configure(state="normal")
        self.text_log.insert("end", mensaje + "\n", color)
        self.text_log.tag_configure(color, foreground=color)
        self.text_log.see("end")
        self.text_log.configure(state="disabled")

    # ---------------- Función callback para patrones ----------------
    def _on_patrones_aplicados(self, df_actualizado):
        """Callback desde PatternsModal tras aplicar y dibujar patrones.
        Reasigna df_actual y reinstala los handlers de zoom/hover sobre el nuevo canvas/figura.
        """
        self.df_actual = df_actualizado
        # Si existía un gestor previo de zoom/hover, desconectarlo limpiamente
        if self.tooltip_zoom_pan:
            try:
                self.tooltip_zoom_pan.cleanup()
            except Exception:
                pass
        # Instalar nuevo gestor con el canvas/figura recién creados
        if hasattr(self.grafico_manager, "canvas") and hasattr(self.grafico_manager, "grafico"):
            self.tooltip_zoom_pan = TooltipZoomPan(
                self.root,
                self.grafico_manager.canvas,
                self.grafico_manager.grafico,
            )

    # ---------------- Run ----------------
    def run(self):
        self.root.mainloop()
