import tkinter as tk
from tkinter import ttk, messagebox
import threading
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle

from app.candlestick_chart import CandlestickChart
from app.forex_pairs import ForexPairs

class Window:
    UPDATE_INTERVAL_MS = 60000  # 1 minuto

    def __init__(self, root, monedas=None):
        self.root = root
        self.root.title("Trading Bot - Forex Market")
        self.root.geometry("1500x750")
        self.root.configure(bg="#F0F0F0")

         # Icono personalizado
        try:
            from tkinter import PhotoImage
            icon = PhotoImage(file="assets/icon.png")
            self.root.iconphoto(True, icon)
        except Exception as e:
            print("No se pudo cargar el icono:", e)

        self.monedas = monedas if monedas else ForexPairs.CURRENCIES

        # Frames
        self.frame_main = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_main.pack(padx=20, pady=20, anchor="w")
        self.frame_grafico = tk.Frame(self.root, bg="#FFFFFF", relief="sunken", bd=1)
        self.frame_grafico.pack(fill="both", expand=True, padx=20, pady=10)
        self.frame_trading = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_trading.pack(fill="x", pady=5, padx=20, anchor="e")

        # Widgets de selección de monedas
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

        # Inicializaciones
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
        self.zoom_activado = False
        self.pan_activado = False
        self.actualizacion_activa = False

    # ---------- Función para mostrar modal 429 ----------
    def mostrar_modal_429(self):
        messagebox.showwarning(
            "Acceso limitado",
            "yfinance pudo conectarse a Yahoo Finance, pero Yahoo está limitando tu acceso "
            "porque detectó muchas solicitudes en poco tiempo.\n\n"
            "Esto no es un problema de red ni de tu entorno virtual, sino un límite de Yahoo Finance."
        )

    # ---------- Selección de monedas ----------
    def actualizar_segundo(self):
        base = self.combo1.get()
        if not base:
            return
        monedas_validas = []
        for c in self.monedas:
            if c == base:
                continue
            try:
                from app.forex_pairs import ForexPairs
                ForexPairs.ticker_valido(base, c)
                monedas_validas.append(c)
            except ValueError:
                continue
        self.combo2['values'] = monedas_validas
        if self.combo2.get() not in monedas_validas:
            self.combo2.set('')

    def on_seleccion(self, event):
        self.actualizar_segundo()
        self.btn_confirmar.config(state="normal" if self.combo1.get() and self.combo2.get() else "disabled")

    # ---------- Confirmar ----------
    def confirmar(self):
        self.btn_confirmar.config(state="disabled")
        self.btn_clear_confirmar.config(state="normal")
        self.combo1.config(state="disabled")
        self.combo2.config(state="disabled")

        tk.Label(self.frame_main, text="Periodo:", bg="#F0F0F0").grid(row=0, column=4, sticky="w")
        self.combo_periodo = ttk.Combobox(self.frame_main, values=self.periodos_disponibles, state="readonly", width=12)
        self.combo_periodo.grid(row=1, column=4, padx=5)
        self.combo_periodo.bind("<<ComboboxSelected>>", self.on_periodo_cambiado)

        tk.Label(self.frame_main, text="Intervalo:", bg="#F0F0F0").grid(row=0, column=5, sticky="w")
        self.combo_intervalo = ttk.Combobox(self.frame_main, state="disabled", width=12)
        self.combo_intervalo.grid(row=1, column=5, padx=5)

        self.btn_grafica = tk.Button(self.frame_main, text="Cargar Gráfica", command=self.cargar_grafica, width=12)
        self.btn_grafica.grid(row=1, column=6, padx=5)
        self.btn_clear_grafica = tk.Button(self.frame_main, text="Clear", command=self.clear_grafica, state="disabled")
        self.btn_clear_grafica.grid(row=1, column=7, padx=5)

        self.btn_rl = tk.Button(self.frame_trading, text="Entrenar Agente RL", command=self.entrenar_agente_thread)
        self.btn_rl.pack(side="right", padx=5)

    # ---------- Intervalo dinámico ----------
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

    # ---------- Cargar gráfica ----------
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
            try:
                self.grafico.obtener_datos()
            except Exception as e:
                if "429" in str(e):
                    self.mostrar_modal_429()
                    return
                else:
                    raise

            self.fig, self.ax = plt.subplots(figsize=(12,6))
            self._dibujar_velas()

            if self.canvas_grafico:
                self.canvas_grafico.get_tk_widget().destroy()

            self.canvas_grafico = FigureCanvasTkAgg(self.fig, master=self.frame_grafico)
            self.canvas_grafico.draw()
            self.canvas_grafico.get_tk_widget().pack(fill="both", expand=True)

            self.actualizacion_activa = True
            self._programar_actualizacion()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- Dibujar velas ----------
    def _dibujar_velas(self):
        self.ax.clear()
        data = self.grafico.data
        if data is not None and not data.empty:
            self.ax.plot(data.index, data['Close'], color='black')
            self.ax.set_title(f"{self.grafico.base}/{self.grafico.cotizada} - {self.grafico.interval}")
            self.ax.grid(True)
        if self.canvas_grafico:
            self.canvas_grafico.draw()

    # ---------- Actualización periódica ----------
    def _programar_actualizacion(self):
        if self.actualizacion_activa:
            self.root.after(self.UPDATE_INTERVAL_MS, self._actualizar_grafica)

    def _actualizar_grafica(self):
        if self.grafico:
            try:
                self.grafico.obtener_datos()
            except Exception as e:
                if "429" in str(e):
                    self.mostrar_modal_429()
                    return
            self._dibujar_velas()
        self._programar_actualizacion()

    # ---------- Clear ----------
    def clear_confirmar(self):
        self.combo1.set('')
        self.combo2.set('')
        self.combo1.config(state="readonly")
        self.combo2.config(state="readonly")
        self.btn_confirmar.config(state="disabled")
        self.btn_clear_confirmar.config(state="disabled")
        for widget in self.frame_main.grid_slaves():
            if int(widget.grid_info()['column']) >= 4:
                widget.destroy()
        if self.canvas_grafico:
            self.canvas_grafico.get_tk_widget().destroy()
            self.canvas_grafico = None

    def clear_grafica(self):
        if self.canvas_grafico:
            self.canvas_grafico.get_tk_widget().destroy()
            self.canvas_grafico = None
        self.btn_grafica.config(state="normal")
        self.btn_clear_grafica.config(state="disabled")

    # ---------- Entrenamiento RL ----------
    def entrenar_agente_thread(self):
        if DRLAgent is None or StockTradingEnv is None:
            messagebox.showwarning("Atención", "FinRL no está instalado. Funcionalidad RL deshabilitada.")
            return
        threading.Thread(target=self.entrenar_agente_rl, daemon=True).start()

    def entrenar_agente_rl(self):
        base = self.combo1.get()
        cotizada = self.combo2.get()
        periodo = self.combo_periodo.get()
        intervalo = self.combo_intervalo.get()
        if not base or not cotizada or not periodo or not intervalo:
            messagebox.showwarning("Atención", "Selecciona todas las opciones antes de entrenar")
            return

        ticker = f"{base}{cotizada}=X"
        try:
            df = yf.download(ticker, period=periodo, interval=intervalo)
        except Exception as e:
            if "429" in str(e):
                self.mostrar_modal_429()
                return
            else:
                messagebox.showerror("Error", str(e))
                return

        df = df[['Open','High','Low','Close','Volume']].reset_index()
        df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'}, inplace=True)

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
        self.df_account_value, _ = agent.DRL_prediction(model=trained_model)

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

    # ---------- Run ----------
    def run(self):
        self.root.mainloop()
