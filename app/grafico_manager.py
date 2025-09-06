# app/grafico_manager.py

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .candlestick_chart import CandlestickChart
from .tooltip_zoom_pan import ChartInteractionManager
import numpy as np

class GraficoManager:
    def __init__(self, frame):
        self.frame = frame
        self.canvas = None
        self.grafico = None
        self.fig = None
        self.ax = None
        # Artistas (anotaciones/flechas) añadidos por señales RL para poder limpiarlos
        self._rl_artists = []
        # Gestor de interacciones (zoom, pan, tooltip)
        self.interaction_manager = None

    def dibujar_csv(self, df):
        self.grafico = CandlestickChart.from_dataframe(df)
        self.fig, self.ax = self.grafico.crear_figura()
        self._dibujar_canvas()
        # Configurar interacciones del gráfico (zoom, pan, tooltip) DESPUÉS del canvas
        self._setup_chart_interactions(df)
        return self.fig, self.ax

    def _dibujar_canvas(self):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        # Forzar actualización del canvas antes de configurar eventos
        self.canvas.get_tk_widget().update_idletasks()

    def _setup_chart_interactions(self, df):
        """Configura las interacciones del gráfico (zoom, pan, tooltip)."""
        # Limpiar gestor anterior si existe
        if self.interaction_manager:
            try:
                self.interaction_manager.cleanup()
            except Exception:
                pass
        
        # Crear nuevo gestor de interacciones
        if self.canvas and self.ax and df is not None and len(df) > 0:
            try:
                # Resetear el DataFrame para asegurar índice numérico
                df_reset = df.reset_index(drop=False)
                
                # Usar after_idle para asegurar que el canvas esté completamente listo
                def setup_interactions():
                    try:
                        self.interaction_manager = ChartInteractionManager(
                            canvas=self.canvas,
                            ax=self.ax,
                            data=df_reset
                        )
                        print(f"ChartInteractionManager configurado con {len(df_reset)} filas de datos")
                    except Exception as e:
                        print(f"Error configurando interacciones del gráfico: {e}")
                
                # Programar la configuración para después de que el canvas esté listo
                self.canvas.get_tk_widget().after_idle(setup_interactions)
                
            except Exception as e:
                print(f"Error programando interacciones del gráfico: {e}")

    def limpiar(self):
        """Limpia la figura y el canvas"""
        # Limpiar gestor de interacciones
        if self.interaction_manager:
            try:
                self.interaction_manager.cleanup()
                self.interaction_manager = None
            except Exception:
                pass
        
        if hasattr(self, 'grafico') and self.grafico:
            if hasattr(self.grafico, 'ax') and self.grafico.ax:
                self.grafico.ax.clear()
            if hasattr(self.grafico, 'fig') and self.grafico.fig:
                self.grafico.fig.clf()
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.draw_idle()

    def dibujar_senales_rl(self, signals):
        """
        Dibuja flechas de compra/venta sobre la gráfica de velas
        signals: lista de 0=mantener, 1=comprar, 2=vender
        """
        if self.grafico is None or self.ax is None:
            return
        df = self.grafico.data.reset_index()
        # Limpiar flechas anteriores de forma segura
        try:
            if hasattr(self, '_rl_artists') and self._rl_artists:
                # eliminar cada artista previo (Text/Line2D/Collection, etc.)
                for art in list(self._rl_artists):
                    try:
                        art.remove()
                    except Exception:
                        pass
                self._rl_artists.clear()
        except Exception:
            pass

        for i, signal in enumerate(signals):
            if signal == 1:  # Compra
                txt = self.ax.annotate(
                    "▲",
                    xy=(i, df['Low'].iloc[i] * 0.9995),
                    xytext=(0, 0),
                    textcoords="offset points",
                    color="green",
                    fontsize=12,
                    ha="center",
                    va="bottom"
                )
                try:
                    setattr(txt, 'es_flecha_rl', True)
                    self._rl_artists.append(txt)
                except Exception:
                    pass
            elif signal == 2:  # Venta
                txt = self.ax.annotate(
                    "▼",
                    xy=(i, df['High'].iloc[i] * 1.0005),
                    xytext=(0, 0),
                    textcoords="offset points",
                    color="red",
                    fontsize=12,
                    ha="center",
                    va="top"
                )
                try:
                    setattr(txt, 'es_flecha_rl', True)
                    self._rl_artists.append(txt)
                except Exception:
                    pass

        self.canvas.draw_idle()

    def set_candles_opacity(self, alpha: float):
        """Actualiza la opacidad de las velas y redibuja el canvas."""
        if not self.grafico:
            return
        try:
            self.grafico.set_candles_alpha(alpha)
            if self.canvas:
                self.canvas.draw_idle()
        except Exception:
            pass
