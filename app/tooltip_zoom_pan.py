from matplotlib.patches import Rectangle
import tkinter as tk

class TooltipZoomPan:
    def __init__(self, root, canvas, grafico):
        self.root = root
        self.canvas = canvas
        self.grafico = grafico
        self.tooltip = None

        # Conectar evento de movimiento del ratón
        self.canvas.mpl_connect("motion_notify_event", self.mostrar_tooltip)

    def mostrar_tooltip(self, event):
        # Solo mostrar si el cursor está dentro del axes
        if event.inaxes is None or self.grafico is None:
            self._ocultar_tooltip()
            return

        # Convertir la posición x del cursor a índice de vela
        xdata = int(round(event.xdata))
        if 0 <= xdata < len(self.grafico.data):
            vela = self.grafico.data.iloc[xdata]
            texto = (
                f"Open: {vela['Open']}\n"
                f"High: {vela['High']}\n"
                f"Low: {vela['Low']}\n"
                f"Close: {vela['Close']}\n"
                f"Volume: {vela['Volume']}"
            )
            self._crear_tooltip(event.guiEvent.x_root, event.guiEvent.y_root, texto)
        else:
            self._ocultar_tooltip()

    def _crear_tooltip(self, x, y, texto):
        self._ocultar_tooltip()
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x+10}+{y+10}")
        tk.Label(self.tooltip, text=texto, background="yellow", relief="solid", borderwidth=1).pack()

    def _ocultar_tooltip(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
