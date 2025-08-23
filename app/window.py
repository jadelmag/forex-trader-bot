import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle
from finrl.model.models import DRLAgent
from finrl.env.env_stocktrading import StockTradingEnv
from app.chart.candlestick_chart import CandlestickChart
from app.forex_pairs import ForexPairs

class Window:
    def __init__(self, root, monedas=None):
        self.root = root
        self.root.title("Trading Bot - Forex Market")
        self.root.geometry("1500x750")
        self.root.configure(bg="#F0F0F0")

        self.monedas = monedas if monedas else ForexPairs.CURRENCIES

        # ---------------- Frames ----------------
        self.frame_main = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_main.pack(padx=20, pady=20, anchor="w")
        self.frame_grafico = tk.Frame(self.root, bg="#FFFFFF", relief="sunken", bd=1)
        self.frame_grafico.pack(fill="both", expand=True, padx=20, pady=10)
        self.frame_trading = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_trading.pack(fill="x", pady=5, padx=20, anchor="e")

        # ---------------- Widgets ----------------
        tk.Label(self.frame_main, text="Moneda Base:", bg="#F0F0F0").grid(row=0, column=0, sticky="w")
        self.combo1 = ttk.Combobox(self.frame_main, values=self.monedas, state="readonly", width=12)
        self.combo1.grid(row=1, column=0, padx=5)
        self.combo1.bind("<<ComboboxSelected>>", self.on_seleccion)

        tk.Label(self.frame_main, text="Moneda Cotizada:", bg="#F0F0F0").grid(row=0, column=1, sticky="w")
        self.combo2 = ttk.Combobox(self.frame_main, values=self.monedas, state="readonly", width=12)
        self.combo2.grid(row=1, column=1, padx=5)
        self.combo2.bind("<<ComboboxSelected>>", self.on_seleccion)

        self.btn_confirmar = tk.Button(self.frame_main, text="Confirmar", state="disabled", command=self.confirmar)
        self.btn_confirmar.grid(row=1, column=2, padx=5)
        self.btn_clear_confirmar = tk.Button(self.frame_main, text="Clear", command=self.clear_confirmar, state="disabled")
        self.btn_clear_confirmar.grid(row=1, column=3, padx=5)

        # ---------------- Inicializaciones ----------------
        self.combo_periodo = None
        self.combo_intervalo = None
        self.btn_grafica = None
        self.btn_clear_grafica = None
        self.periodos_disponibles = ["1d", "5d", "7d", "1mo", "3mo", "6mo", "1y"]
        self.grafico = None
        self.fig = None
        self.ax = None
        self.canvas_grafico = None
        self.tooltip = None

        # Zoom y Pan
        self.zoom_activado = False
        self.zoom_x0 = None
        self.zoom_y0 = None
        self.rect_zoom = None
        self.pan_activado = False
        self.pan_x0 = None
        self.pan_y0 = None
        self.limites_x0 = None
        self.limites_y0 = None

        # Datos RL
        self.df_account_value = None

    # ---------------- Funciones Monedas ----------------
    def actualizar_segundo(self):
        seleccion1 = self.combo1.get()
        opciones2 = [m for m in self.monedas if m != seleccion1]
        self.combo2['values'] = opciones2
        if self.combo2.get() == seleccion1:
            self.combo2.set('')

    def on_seleccion(self, event):
        self.actualizar_segundo()
        if self.combo1.get() and self.combo2.get():
            self.btn_confirmar.config(state="normal")
        else:
            self.btn_confirmar.config(state="disabled")

    # ---------------- Confirmar ----------------
    def confirmar(self):
        self.btn_confirmar.config(state="disabled")
        self.btn_clear_confirmar.config(state="normal")
        self.combo1.config(state="disabled")
        self.combo2.config(state="disabled")

        # Periodo
        tk.Label(self.frame_main, text="Periodo:", bg="#F0F0F0").grid(row=0, column=4, sticky="w")
        self.combo_periodo = ttk.Combobox(self.frame_main, values=self.periodos_disponibles, state="readonly", width=12)
        self.combo_periodo.grid(row=1, column=4, padx=5)
        self.combo_periodo.bind("<<ComboboxSelected>>", self.on_periodo_cambiado)

        # Intervalo
        tk.Label(self.frame_main, text="Intervalo:", bg="#F0F0F0").grid(row=0, column=5, sticky="w")
        self.combo_intervalo = ttk.Combobox(self.frame_main, state="disabled", width=12)
        self.combo_intervalo.grid(row=1, column=5, padx=5)

        # Botones Cargar gráfica / Clear
        self.btn_grafica = tk.Button(self.frame_main, text="Cargar Gráfica", command=self.cargar_grafica, width=12)
        self.btn_grafica.grid(row=1, column=6, padx=5)
        self.btn_clear_grafica = tk.Button(self.frame_main, text="Clear", command=self.clear_grafica, state="disabled")
        self.btn_clear_grafica.grid(row=1, column=7, padx=5)

        # Botones RL + Zoom/Pan
        self.btn_rl = tk.Button(self.frame_trading, text="Entrenar Agente RL", command=self.entrenar_agente_thread)
        self.btn_rl.pack(side="right", padx=5)
        self.btn_zoom = tk.Button(self.frame_trading, text="Zoom", command=self.toggle_zoom)
        self.btn_zoom.pack(side="right", padx=5)
        self.btn_pan = tk.Button(self.frame_trading, text="Pan", command=self.toggle_pan)
        self.btn_pan.pack(side="right", padx=5)

    # ---------------- Intervalo dinámico ----------------
    def on_periodo_cambiado(self, event):
        periodo = self.combo_periodo.get()
        base = self.combo1.get()
        cotizada = self.combo2.get()
        if base and cotizada:
            intervalos_validos = ForexPairs.intervalos_permitidos(base, cotizada)
            self.combo_intervalo['values'] = intervalos_validos
            if intervalos_validos:
                self.combo_intervalo.current(0)
                self.combo_intervalo.config(state="readonly")
            else:
                self.combo_intervalo.set('')
                self.combo_intervalo.config(state="disabled")

    # ---------------- Cargar Gráfica ----------------
    def cargar_grafica(self):
        base = self.combo1.get()
        cotizada = self.combo2.get()
        intervalo = self.combo_intervalo.get()
        periodo = self.combo_periodo.get()
        if not intervalo or not periodo:
            messagebox.showwarning("Atención", "Selecciona intervalo y periodo antes de cargar la gráfica.")
            return

        try:
            self.grafico = CandlestickChart(base, cotizada, period=periodo, interval=intervalo)
            self.grafico.obtener_datos()
            self.fig = self.grafico.crear_figura()
            self.ax = self.fig.axes[0]

            if self.canvas_grafico:
                self.canvas_grafico.get_tk_widget().destroy()

            self.canvas_grafico = FigureCanvasTkAgg(self.fig, master=self.frame_grafico)
            self.canvas_grafico.draw()
            self.canvas_grafico.get_tk_widget().pack(fill="both", expand=True)

            # Activar tooltip
            self.canvas_grafico.mpl_connect("motion_notify_event", self.mostrar_tooltip)
            self.btn_grafica.config(state="disabled")
            self.btn_clear_grafica.config(state="normal")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- Tooltip ----------------
    def mostrar_tooltip(self, event):
        if event.inaxes is None: return
        xdata = int(round(event.xdata))
        if hasattr(self.grafico, "data") and 0 <= xdata < len(self.grafico.data):
            vela = self.grafico.data.iloc[xdata]
            text = f"Open:{vela['Open']}\nHigh:{vela['High']}\nLow:{vela['Low']}\nClose:{vela['Close']}\nVol:{vela['Volume']}"
            self._crear_tooltip(event.guiEvent.x_root, event.guiEvent.y_root, text)
        else:
            self._ocultar_tooltip()

    def _crear_tooltip(self, x, y, text):
        self._ocultar_tooltip()
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x+10}+{y+10}")
        tk.Label(self.tooltip, text=text, background="yellow", relief="solid", borderwidth=1).pack()

    def _ocultar_tooltip(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    # ---------------- Entrenamiento RL ----------------
    def entrenar_agente_thread(self):
        threading.Thread(target=self.entrenar_agente_rl, daemon=True).start()

    def entrenar_agente_rl(self):
        base = self.combo1.get()
        cotizada = self.combo2.get()
        periodo = self.combo_periodo.get()
        intervalo = self.combo_intervalo.get()
        if not base or not cotizada or not periodo or not intervalo:
            messagebox.showwarning("Atención", "Selecciona todas las opciones antes de entrenar")
            return

        # Descargar datos históricos
        ticker = f"{base}{cotizada}=X"
        df = yf.download(ticker, period=periodo, interval=intervalo)
        df = df[['Open','High','Low','Close','Volume']].reset_index()
        df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'}, inplace=True)

        # Crear entorno RL
        env_kwargs = {
            "hmax": 100,
            "initial_amount": 10000,
            "transaction_cost_pct": 0.001,
            "state_space": 5,
            "stock_dim": 1,
            "tech_indicator_list": [],
            "action_space": 3,
            "reward_scaling": 1e-4,
            "print_verbosity": 0
        }
        env = StockTradingEnv(df=df, **env_kwargs)

        agent = DRLAgent(env=env)
        model = agent.get_model("ppo")
        trained_model = agent.train_model(model=model, tb_log_name="ppo_rl", total_timesteps=5000)

        # Predicción y resultados
        self.df_account_value, _ = agent.DRL_prediction(model=trained_model)

        # ---------------- Graficar curvas completas ----------------
        if self.canvas_grafico:
            self.canvas_grafico.get_tk_widget().destroy()

        self.fig, self.ax = plt.subplots(3,1, figsize=(12,8))
        self.ax[0].plot(self.df_account_value['date'], self.df_account_value['account_value'], label="Equity")
        self.ax[0].set_title("Equity")
        self.ax[1].plot(self.df_account_value['date'], self.df_account_value['cash'], label="Cash", color='orange')
        self.ax[1].set_title("Cash")
        self.ax[2].plot(self.df_account_value['date'], self.df_account_value['position'], label="Posiciones", color='green')
        self.ax[2].set_title("Posiciones")
        for a in self.ax: a.legend(); a.grid(True)
        self.canvas_grafico = FigureCanvasTkAgg(self.fig, master=self.frame_grafico)
        self.canvas_grafico.draw()
        self.canvas_grafico.get_tk_widget().pack(fill="both", expand=True)

    # ---------------- Zoom y Pan ----------------
    def toggle_zoom(self):
        self.zoom_activado = not self.zoom_activado
        if self.zoom_activado:
            self.btn_zoom.config(relief="sunken")
            self.canvas_grafico.mpl_connect("button_press_event", self.iniciar_zoom)
            self.canvas_grafico.mpl_connect("motion_notify_event", self.actualizar_rect)
            self.canvas_grafico.mpl_connect("button_release_event", self.finalizar_zoom)
        else:
            self.btn_zoom.config(relief="raised")
            if self.rect_zoom: self.rect_zoom.remove(); self.rect_zoom=None; self.canvas_grafico.draw()

    def iniciar_zoom(self, event):
        if not self.zoom_activado or event.inaxes is None: return
        self.zoom_x0, self.zoom_y0 = event.xdata, event.ydata
        self.rect_zoom = Rectangle((self.zoom_x0, self.zoom_y0), 0, 0, linewidth=1, edgecolor='gray', linestyle='--', facecolor='none')
        event.inaxes.add_patch(self.rect_zoom)

    def actualizar_rect(self, event):
        if self.zoom_activado and self.rect_zoom and event.inaxes:
            self.rect_zoom.set_width(event.xdata - self.zoom_x0)
            self.rect_zoom.set_height(event.ydata - self.zoom_y0)
            self.canvas_grafico.draw_idle()

    def finalizar_zoom(self, event):
        if not self.zoom_activado or event.inaxes is None: return
        ax = event.inaxes
        ax.set_xlim(min(self.zoom_x0, event.xdata), max(self.zoom_x0, event.xdata))
        ax.set_ylim(min(self.zoom_y0, event.ydata), max(self.zoom_y0, event.ydata))
        if self.rect_zoom: self.rect_zoom.remove(); self.rect_zoom=None
        self.canvas_grafico.draw_idle()

    def toggle_pan(self):
        self.pan_activado = not self.pan_activado
        if self.pan_activado:
            self.btn_pan.config(relief="sunken")
            self.canvas_grafico.mpl_connect("button_press_event", self.iniciar_pan)
            self.canvas_grafico.mpl_connect("motion_notify_event", self.actualizar_pan)
            self.canvas_grafico.mpl_connect("button_release_event", self.finalizar_pan)
        else:
            self.btn_pan.config(relief="raised")
            self.pan_x0 = self.pan_y0 = None
            self.limites_x0 = self.limites_y0 = None

    def iniciar_pan(self, event):
        if not self.pan_activado or event.inaxes is None or event.button!=1: return
        self.pan_x0, self.pan_y0 = event.xdata, event.ydata
        self.limites_x0 = event.inaxes.get_xlim()
        self.limites_y0 = event.inaxes.get_ylim()

    def actualizar_pan(self, event):
        if not self.pan_activado or event.inaxes is None or event.button!=1: return
        dx, dy = self.pan_x0 - event.xdata, self.pan_y0 - event.ydata
        x_min, x_max = self.limites_x0
        y_min, y_max = self.limites_y0
        event.inaxes.set_xlim(x_min + dx, x_max + dx)
        event.inaxes.set_ylim(y_min + dy, y_max + dy)
        self.canvas_grafico.draw_idle()

    def finalizar_pan(self, event):
        self.pan_x0 = self.pan_y0 = None
        self.limites_x0 = self.limites_y0 = None

    # ---------------- Clear ----------------
    def clear_grafica(self):
        if self.canvas_grafico: self.canvas_grafico.get_tk_widget().destroy(); self.canvas_grafico=None
        self.btn_grafica.config(state="normal")
        self.btn_clear_grafica.config(state="disabled")

    def clear_confirmar(self):
        self.combo1.set(""); self.combo2.set("")
        self.combo1.config(state="readonly"); self.combo2.config(state="readonly")
        self.btn_confirmar.config(state="disabled"); self.btn_clear_confirmar.config(state="disabled")
        for widget in self.frame_main.grid_slaves():
            if int(widget.grid_info()['column'])>=4: widget.destroy()
        if self.canvas_grafico: self.canvas_grafico.get_tk_widget().destroy(); self.canvas_grafico=None
        for widget in self.frame_trading.winfo_children(): widget.destroy()

    # ---------------- Run ----------------
    def run(self):
        self.root.mainloop()
