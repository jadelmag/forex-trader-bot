# app/gui/managers/thread_manager.py
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor
import weakref

class ThreadManager:
    def __init__(self, main_app):
        self.main_app = main_app
        
        # Pool de hilos para procesamiento asíncrono (limitado a 3 hilos)
        self._thread_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ForexBot")
        
        # Queue thread-safe para comunicación entre hilos
        self._gui_update_queue = queue.Queue()
        self._log_queue = queue.Queue()
        
        # Throttling para actualizaciones de GUI
        self._last_gui_update = 0
        self._gui_update_interval = 0.1  # 100ms mínimo entre actualizaciones
        self._last_log_update = 0
        self._log_update_interval = 0.05  # 50ms mínimo entre logs
        
        # Flags de control
        self._processing_candle = False
        self._shutdown_requested = False
        
        # Inicializar worker de threading
        self._start_gui_update_worker()
        
    def _start_gui_update_worker(self):
        """Inicia el worker para actualizaciones de GUI thread-safe"""
        try:
            def _gui_update_worker():
                while not self._shutdown_requested:
                    try:
                        # Procesar actualizaciones de GUI
                        try:
                            update_type, data = self._gui_update_queue.get_nowait()
                            self._process_gui_update(update_type, data)
                        except queue.Empty:
                            pass
                        
                        # Procesar logs
                        try:
                            log_data = self._log_queue.get_nowait()
                            self._process_log_update(log_data)
                        except queue.Empty:
                            pass
                            
                        time.sleep(0.01)  # Pequeña pausa para no saturar CPU
                    except Exception as e:
                        print(f"Error en GUI update worker: {e}")
                        
            self._gui_worker_thread = threading.Thread(target=_gui_update_worker, daemon=True)
            self._gui_worker_thread.start()
        except Exception as e:
            print(f"Error iniciando worker de threading: {e}")
            
    def _process_gui_update(self, update_type, data):
        """Procesa actualizaciones de GUI de forma thread-safe"""
        try:
            current_time = time.time()
            if current_time - self._last_gui_update < self._gui_update_interval:
                return
                
            if update_type == 'cash':
                if hasattr(self.main_app, 'status_bar'):
                    self.main_app.status_bar.actualizar_dinero_visible(data, data)
            elif update_type == 'equity':
                equity, cash = data
                if hasattr(self.main_app, 'status_bar'):
                    self.main_app.status_bar.actualizar_dinero_visible(equity, cash)
            elif update_type == 'simulation_status':
                estado, color = data
                if hasattr(self.main_app, 'status_bar'):
                    self.main_app.status_bar.actualizar_estado_simulacion(estado, color)
                    
            self._last_gui_update = current_time
        except Exception as e:
            print(f"Error procesando actualización GUI: {e}")
            
    def _process_log_update(self, log_data):
        try:
            if hasattr(self.main_app, 'status_bar'):
                self.main_app.status_bar.update_simulation_status(status, color)
        except Exception as e:
            print(f"Error actualizando estado de simulación: {e}")
            
    def is_processing(self):
        """Verifica si hay procesamiento en curso"""
        return getattr(self, '_processing', False)
        
    def set_processing(self, processing):
        """Establece el estado de procesamiento"""
        self._processing = processing
        
    def queue_gui_update(self, update_type, data):
        """Método público para encolar actualizaciones de GUI"""
        try:
            self._gui_update_queue.put_nowait((update_type, data))
        except queue.Full:
            pass  # Ignorar si la cola está llena
            
    def queue_log_update(self, message, color="white"):
        """Encola una actualización de log thread-safe"""
        try:
            self._log_queue.put_nowait((message, color))
        except queue.Full:
            pass  # Ignorar si la cola está llena
            
    def submit_task(self, func, *args, **kwargs):
        """Envía una tarea al pool de hilos"""
        try:
            return self._thread_pool.submit(func, *args, **kwargs)
        except Exception as e:
            print(f"Error enviando tarea al pool: {e}")
            return None
            
    def is_processing(self):
        """Verifica si hay procesamiento en curso"""
        return self._processing_candle
        
    def set_processing(self, processing):
        """Establece el estado de procesamiento"""
        self._processing_candle = processing
        
    def shutdown(self):
        """Cierra el gestor de hilos limpiamente"""
        self._shutdown_requested = True
        try:
            self._thread_pool.shutdown(wait=True, timeout=5)
        except Exception as e:
            print(f"Error cerrando pool de hilos: {e}")
            
        try:
            if hasattr(self, '_gui_worker_thread') and self._gui_worker_thread.is_alive():
                self._gui_worker_thread.join(timeout=2)
        except Exception as e:
            print(f"Error cerrando worker thread: {e}")