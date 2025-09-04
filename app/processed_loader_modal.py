# app/processed_loader_modal.py

import os
import io
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pickle
import pandas as pd

# Opcional: PyArrow para Parquet y lecturas parciales
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PYARROW = True
except Exception:
    HAS_PYARROW = False

from .progress_modal import centrar_ventana

MESES = [
    ("Enero", 1), ("Febrero", 2), ("Marzo", 3), ("Abril", 4),
    ("Mayo", 5), ("Junio", 6), ("Julio", 7), ("Agosto", 8),
    ("Septiembre", 9), ("Octubre", 10), ("Noviembre", 11), ("Diciembre", 12)
]

class ProcessedDataModal(tk.Toplevel):
    def __init__(self, parent, on_loaded_df):
        super().__init__(parent)
        self.parent = parent
        self.on_loaded_df = on_loaded_df
        self.title("Cargar datos procesados")
        self.geometry("560x350")
        self.resizable(False, False)
        self.grab_set()

        # Estado
        self._cancel_event = threading.Event()
        self.total_rows = 0
        self.filepath = None
        self._loading = False
        self._last_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'processed')

        # Vars UI
        self.var_total_label = tk.StringVar(value="Selecciona un archivo procesado (.parquet o .pkl)")
        self.var_first_n = tk.StringVar(value="20000")
        self.var_last_n = tk.StringVar(value="20000")
        self.var_mes = tk.StringVar(value=MESES[0][0])

        # Checkboxes (mutuamente excluyentes por lógica)
        self.var_opt_all = tk.BooleanVar(value=True)
        self.var_opt_first = tk.BooleanVar(value=False)
        self.var_opt_last = tk.BooleanVar(value=False)
        self.var_opt_month = tk.BooleanVar(value=False)

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=18, pady=16)

        # Archivo
        file_frame = ttk.Frame(container)
        file_frame.pack(fill="x")
        ttk.Label(file_frame, text="Archivo procesado:", font=("Arial", 10, "bold")).pack(anchor="w")
        row = ttk.Frame(file_frame)
        row.pack(fill="x", pady=(6,0))
        self.entry_file = ttk.Entry(row)
        self.entry_file.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Seleccionar", width=16, command=self._select_file).pack(side="left", padx=(8,0))

        # Info total
        info_frame = ttk.Frame(container)
        info_frame.pack(fill="x", pady=(10, 0))
        lbl = ttk.Label(info_frame, textvariable=self.var_total_label, anchor="center")
        lbl.pack(fill="x")

        # Opciones
        opts = ttk.LabelFrame(container, text="Opciones de carga (selección única)")
        opts.pack(fill="x", pady=(12, 0))

        # All
        frm_all = ttk.Frame(opts)
        frm_all.pack(fill="x", pady=(6,0))
        chk_all = ttk.Checkbutton(frm_all, text="Seleccionar todo el fichero", variable=self.var_opt_all, command=lambda: self._select_only("all"))
        chk_all.pack(side="left")

        # First N
        frm_first = ttk.Frame(opts)
        frm_first.pack(fill="x", pady=(6,0))
        chk_first = ttk.Checkbutton(frm_first, text="Seleccionar las primeras N filas:", variable=self.var_opt_first, command=lambda: self._select_only("first"))
        chk_first.pack(side="left")
        self.entry_first = ttk.Entry(frm_first, textvariable=self.var_first_n, width=10)
        self.entry_first.pack(side="left", padx=(8,0))

        # Last N
        frm_last = ttk.Frame(opts)
        frm_last.pack(fill="x", pady=(6,0))
        chk_last = ttk.Checkbutton(frm_last, text="Seleccionar las últimas N filas:", variable=self.var_opt_last, command=lambda: self._select_only("last"))
        chk_last.pack(side="left")
        self.entry_last = ttk.Entry(frm_last, textvariable=self.var_last_n, width=10)
        self.entry_last.pack(side="left", padx=(8,0))

        # Month
        frm_month = ttk.Frame(opts)
        frm_month.pack(fill="x", pady=(6,0))
        chk_month = ttk.Checkbutton(frm_month, text="Seleccionar por mes:", variable=self.var_opt_month, command=lambda: self._select_only("month"))
        chk_month.pack(side="left")
        self.cmb_mes = ttk.Combobox(frm_month, state="readonly", values=[m[0] for m in MESES], textvariable=self.var_mes, width=14)
        self.cmb_mes.pack(side="left", padx=(8,0))

        # Estado simple (sin barra de progreso)
        status_row = ttk.Frame(container)
        status_row.pack(fill="x", pady=(10,0))
        self.lbl_status = ttk.Label(status_row, text="Listo")
        self.lbl_status.pack(side="left")

        # Botones
        btns = ttk.Frame(container)
        btns.pack(fill="x", pady=(14, 0))
        self.btn_cancel = ttk.Button(btns, text="Cancelar", command=self._on_cancel)
        self.btn_cancel.pack(side="right")
        self.btn_accept = ttk.Button(btns, text="Aceptar", command=self._on_accept, state="disabled")
        self.btn_accept.pack(side="right", padx=(0,8))

        centrar_ventana(self, parent)

        # Ajustar estados iniciales
        self._apply_option_states()

    # --- UI helpers ---
    def _select_only(self, which: str):
        # Asegura selección única tipo checkboxes
        self.var_opt_all.set(which == "all")
        self.var_opt_first.set(which == "first")
        self.var_opt_last.set(which == "last")
        self.var_opt_month.set(which == "month")
        self._apply_option_states()

    def _apply_option_states(self):
        # habilitar/deshabilitar entries según opción
        self.entry_first.config(state=("normal" if self.var_opt_first.get() else "disabled"))
        self.entry_last.config(state=("normal" if self.var_opt_last.get() else "disabled"))
        self.cmb_mes.config(state=("readonly" if self.var_opt_month.get() else "disabled"))

    def _select_file(self):
        initial_dir = self._last_dir
        # Poner PKL primero para que sea el filtro por defecto
        filetypes = [("Pickle", "*.pkl"), ("Parquet", "*.parquet"), ("Todos", "*.*")]
        fp = filedialog.askopenfilename(initialdir=initial_dir, filetypes=filetypes)
        if not fp:
            return
        self.filepath = fp
        try:
            self._last_dir = os.path.dirname(fp)
        except Exception:
            pass
        self.entry_file.delete(0, tk.END)
        self.entry_file.insert(0, fp)
        # Contar filas
        self._update_total_rows_async(fp)

    def _update_total_rows_async(self, fp: str):
        def worker():
            total = 0
            try:
                if fp.lower().endswith('.parquet') and HAS_PYARROW:
                    pf = pq.ParquetFile(fp)
                    total = pf.metadata.num_rows or 0
                    if not total and pf.num_row_groups:
                        try:
                            total = sum(pf.metadata.row_group(i).num_rows for i in range(pf.num_row_groups))
                        except Exception:
                            total = 0
                elif fp.lower().endswith('.pkl'):
                    with open(fp, 'rb') as f:
                        df = pickle.load(f)
                    total = len(df)
                else:
                    total = 0
            except Exception:
                total = 0
            self.total_rows = total
            self.after(0, lambda: self._on_total_rows_ready(total))
        threading.Thread(target=worker, daemon=True).start()

    def _on_total_rows_ready(self, total: int):
        if total > 0:
            self.var_total_label.set(f"El fichero contiene: {total:,} filas")
            self.btn_accept.config(state="normal")
            # clamp defaults
            try:
                n = int(self.var_first_n.get() or '0')
                self.var_first_n.set(str(min(max(n,0), total)))
            except Exception:
                self.var_first_n.set("20000")
            try:
                n = int(self.var_last_n.get() or '0')
                self.var_last_n.set(str(min(max(n,0), total)))
            except Exception:
                self.var_last_n.set("20000")
        else:
            self.var_total_label.set("No se pudo determinar filas del archivo")
            self.btn_accept.config(state="disabled")

    # --- Accept ---
    def _on_accept(self):
        if not self.filepath:
            messagebox.showwarning("Archivo", "Seleccione un archivo primero")
            return
        # Pre-chequeo para Parquet sin PyArrow
        if self.filepath.lower().endswith('.parquet') and not HAS_PYARROW:
            messagebox.showerror("Carga", "PyArrow no está instalado. Instale 'pyarrow' para leer archivos Parquet.")
            return
        # bloquear botones
        self.btn_accept.config(state="disabled")
        self.btn_cancel.config(state="normal", text="Cancelar carga")
        self._cancel_event.clear()
        self._loading = True
        self.lbl_status.config(text="Cargando datos...")
        threading.Thread(target=self._load_in_background, daemon=True).start()

    def _load_in_background(self):
        try:
            fp = self.filepath
            df = None
            if fp.lower().endswith('.parquet') and HAS_PYARROW:
                df = self._load_parquet(fp)
            elif fp.lower().endswith('.pkl'):
                df = self._load_pickle(fp)
            else:
                raise RuntimeError("Formato no soportado o PyArrow no disponible")

            # Si el usuario canceló durante la carga, abortar de forma controlada
            if self._cancel_event.is_set():
                raise RuntimeError("Cancelado por el usuario")

            if df is None or df.empty:
                raise RuntimeError("No se obtuvieron datos")

            # Normalizar índice DateTime
            if 'DateTime' in df.columns:
                try:
                    # Asegurar tipo datetime
                    if not pd.api.types.is_datetime64_any_dtype(df['DateTime']):
                        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
                    df = df.dropna(subset=['DateTime'])
                    df.set_index('DateTime', inplace=True)
                except Exception:
                    pass

            # Callback al hilo principal
            self.after(0, lambda d=df: self._finish_ok(d))
        except Exception as e:
            self.after(0, lambda: self._finish_err(str(e)))

    def _finish_ok(self, df: pd.DataFrame):
        try:
            self.lbl_status.config(text="Completado")
        except Exception:
            pass
        finally:
            self._loading = False
            try:
                self.btn_cancel.config(text="Cancelar")
            except Exception:
                pass
        try:
            if callable(self.on_loaded_df):
                self.on_loaded_df(df)
        finally:
            self.destroy()

    def _finish_err(self, msg: str):
        # Detener/limpiar estados si fuese necesario
        self._loading = False
        if "Cancelado por el usuario" in msg:
            # Cancelación amigable: no mostrar dialogo de error
            self.lbl_status.config(text="Cancelado")
        else:
            self.lbl_status.config(text="Error")
            messagebox.showerror("Carga", f"No se pudo cargar: {msg}")
        self.btn_accept.config(state="normal")
        try:
            self.btn_cancel.config(state="normal", text="Cancelar")
        except Exception:
            pass

    def _on_cancel(self):
        # Si no estamos cargando, cerrar el modal
        if not self._loading:
            self.destroy()
            return
        # Si estamos cargando, marcar cancelación y actualizar UI
        try:
            self._cancel_event.set()
            self.lbl_status.config(text="Cancelando...")
            # mantener botón activo por si el usuario desea cerrar tras cancelar
        except Exception:
            pass

    # --- Loaders ---
    def _load_pickle(self, fp: str) -> pd.DataFrame:
        # Mostrar estado mientras se lee
        try:
            self.after(0, lambda: self.lbl_status.config(text="Leyendo archivo..."))
        except Exception:
            pass
        buffer = io.BytesIO()
        read_bytes = 0
        chunk_size = 4 * 1024 * 1024  # 4MB
        with open(fp, 'rb') as f:
            while True:
                if self._cancel_event.is_set():
                    raise RuntimeError("Cancelado por el usuario")
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                buffer.write(chunk)
                read_bytes += len(chunk)

        # Deserialización (sin barra)
        buffer.seek(0)
        try:
            self.after(0, lambda: self.lbl_status.config(text="Deserializando..."))
        except Exception:
            pass
        df = pickle.load(buffer)
        # Aplicar selección
        if self.var_opt_all.get():
            return df
        if self.var_opt_first.get():
            n = min(int(self.var_first_n.get() or '0'), len(df))
            return df.iloc[:n]
        if self.var_opt_last.get():
            n = min(int(self.var_last_n.get() or '0'), len(df))
            return df.iloc[-n:]
        if self.var_opt_month.get():
            mes_nombre = self.var_mes.get()
            mes_num = dict(MESES)[mes_nombre]
            idx = df.index
            if 'DateTime' in df.columns:
                col = pd.to_datetime(df['DateTime'], errors='coerce')
                return df[col.dt.month == mes_num]
            if isinstance(idx, pd.DatetimeIndex):
                return df[idx.month == mes_num]
            # fallback: nada
            return df
        return df

    def _load_parquet(self, fp: str) -> pd.DataFrame:
        # Columnas esperadas
        cols = ["DateTime", "Open", "High", "Low", "Close", "Volume"]
        pf = pq.ParquetFile(fp)
        total = pf.metadata.num_rows or 0
        if not total and pf.num_row_groups:
            try:
                total = sum(pf.metadata.row_group(i).num_rows for i in range(pf.num_row_groups))
            except Exception:
                total = 0

        if self.var_opt_all.get():
            # Leer por lotes (sin barra de progreso)
            parts = []
            processed = 0
            for batch in pf.iter_batches(batch_size=100_000, columns=cols):
                if self._cancel_event.is_set():
                    break
                t = pa.Table.from_batches([batch])
                parts.append(t.to_pandas())
                processed += t.num_rows
            return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)

        if self.var_opt_first.get():
            n = min(int(self.var_first_n.get() or '0'), total)
            if n <= 0:
                return pd.DataFrame(columns=cols)
            remain = n
            parts = []
            # iter_batches respeta columnas
            processed = 0
            for batch in pf.iter_batches(batch_size=100_000, columns=cols):
                if remain <= 0:
                    break
                t = pa.Table.from_batches([batch])
                take = min(remain, t.num_rows)
                if take < t.num_rows:
                    t = t.slice(0, take)
                parts.append(t.to_pandas())
                remain -= take
                processed += take
            return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)

        if self.var_opt_last.get():
            n = min(int(self.var_last_n.get() or '0'), total)
            if n <= 0:
                return pd.DataFrame(columns=cols)
            remain = n
            parts = []
            # Leer row groups al revés
            processed = 0
            num_rgs = pf.num_row_groups
            for rg in range(num_rgs - 1, -1, -1):
                if remain <= 0:
                    break
                t = pf.read_row_group(rg, columns=cols)
                take = min(remain, t.num_rows)
                if take < t.num_rows:
                    t = t.slice(t.num_rows - take, take)
                parts.append(t.to_pandas())
                remain -= take
                processed += take
            if parts:
                df = pd.concat(reversed(parts), ignore_index=True)
                return df.tail(n)
            return pd.DataFrame(columns=cols)

        if self.var_opt_month.get():
            mes_nombre = self.var_mes.get()
            mes_num = dict(MESES)[mes_nombre]
            # Filtrar por mes streameando row groups (sin barra)
            parts = []
            processed = 0
            for rg in range(pf.num_row_groups):
                t = pf.read_row_group(rg, columns=cols)
                df = t.to_pandas()
                # asegurar datetime
                if not pd.api.types.is_datetime64_any_dtype(df['DateTime']):
                    df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
                df = df[df['DateTime'].dt.month == mes_num]
                if not df.empty:
                    parts.append(df)
                processed += t.num_rows
            return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)
        # fallback all
        table = pf.read(columns=cols)
        return table.to_pandas()
