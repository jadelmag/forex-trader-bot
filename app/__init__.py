"""
Inicialización del paquete 'app'.
Importa los módulos más importantes para facilitar los imports.
"""

from .window import Window
from .candlestick_chart import CandlestickChart
from .gui_main import GUIPrincipal
from .csv_manager import CSVManager
from .grafico_manager import GraficoManager
from .tooltip_zoom_pan import TooltipZoomPan
from .csv_loader_modal import CSVLoaderModal

__all__ = [
    "Window",
    "CandlestickChart",
    "GUIPrincipal",
    "CSVManager",
    "GraficoManager",
    "TooltipZoomPan",
    "CSVLoaderModal"
]