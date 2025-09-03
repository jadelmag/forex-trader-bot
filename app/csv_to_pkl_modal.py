# app/csv_to_pkl_modal.py

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd

# PyArrow opcional para Parquet en streaming
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PYARROW = True
except Exception:
    HAS_PYARROW = False

from .progress_modal import centrar_ventana


class CSVToPKLModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Procesar CSV a PKL")
        self.geometry("560x320")
        self.resizable(False, False)
        self.grab_set()  # Modal

        # Rutas base
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.csv_dir = os.path.join(self.base_dir, 'csv')
        self.processed_dir = os.path.join(self.base_dir, 'processed')
        os.makedirs(self.processed_dir, exist_ok=True)

        # Variables
        self.var_csv_path = tk.StringVar(value="")
        self.var_output_dir = tk.StringVar(value=self.processed_dir)
        self.var_output_name = tk.StringVar(value="processed_data.parquet")
        self.var_format = tk.StringVar(value="parquet")  # 'parquet' | 'pkl'
        self._cancel_event = threading.Event()

        # Layout principal
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=18, pady=16)

        # Selección CSV
        csv_frame = ttk.Frame(container)
        csv_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(csv_frame, text="Archivo CSV origen:", font=("Arial", 10, "bold")).pack(anchor="w")

        path_row = ttk.Frame(csv_frame)
        path_row.pack(fill="x", pady=(6, 0))
        self.entry_csv = ttk.Entry(path_row, textvariable=self.var_csv_path)
        self.entry_csv.pack(side="left", fill="x", expand=True)
        ttk.Button(path_row, text="Seleccionar CSV", width=20, command=self._select_csv).pack(side="left", padx=(8, 0))

        # Salida
        out_frame = ttk.Frame(container)
        out_frame.pack(fill="x", pady=(10, 10))
        ttk.Label(out_frame, text="Destino del archivo:", font=("Arial", 10, "bold")).pack(anchor="w")

        # Directorio
        dir_row = ttk.Frame(out_frame)
        dir_row.pack(fill="x", pady=(6, 0))
        self.entry_dir = ttk.Entry(dir_row, textvariable=self.var_output_dir)
        self.entry_dir.pack(side="left", fill="x", expand=True)
        ttk.Button(dir_row, text="Elegir carpeta", width=16, command=self._select_dir).pack(side="left", padx=(8, 0))

        # Formato de salida
        fmt_row = ttk.Frame(out_frame)
        fmt_row.pack(fill="x", pady=(0, 6))
        ttk.Label(fmt_row, text="Formato:").pack(side="left")
        self.cmb_format = ttk.Combobox(fmt_row, state="readonly", width=12,
                                       values=["parquet", "pkl"], textvariable=self.var_format)
        self.cmb_format.pack(side="left", padx=(8, 0))
        self.cmb_format.bind("<<ComboboxSelected>>", self._on_format_change)

        # Nombre de archivo
        name_row = ttk.Frame(out_frame)
        name_row.pack(fill="x", pady=(6, 0))
        self.lbl_name = ttk.Label(name_row, text="Nombre de archivo (.parquet):")
        self.lbl_name.pack(side="left")
        self.entry_name = ttk.Entry(name_row, textvariable=self.var_output_name, width=38)
        self.entry_name.pack(side="left", padx=(8, 0))

        # Progreso
        progress_frame = ttk.Frame(container)
        progress_frame.pack(fill="x", pady=(6, 0))
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x")
        self.lbl_progress = ttk.Label(progress_frame, text="0%", anchor="e")
        self.lbl_progress.pack(fill="x", pady=(4, 0))

        # Botones inferiores
        btns = ttk.Frame(container)
        btns.pack(fill="x", pady=(16, 0))
        self.btn_close = ttk.Button(btns, text="Cerrar", command=self.destroy)
        self.btn_close.pack(side="right")
        self.btn_process = ttk.Button(btns, text="Procesar", command=self._on_click_process)
        self.btn_process.pack(side="right", padx=(0, 8))
        self.btn_cancel = ttk.Button(btns, text="Cancelar", command=self._on_cancel, state="disabled")
        self.btn_cancel.pack(side="left")

        # Centrar modal
        centrar_ventana(self, parent)

    def _select_csv(self):
        initial_dir = self.csv_dir if os.path.isdir(self.csv_dir) else self.base_dir
        filepath = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Seleccionar CSV",
            filetypes=[("CSV Files", "*.csv"), ("Todos", "*.*")]
        )
        if not filepath:
            return
        self.var_csv_path.set(filepath)
        # Sugerir nombre basado en archivo
        base = os.path.splitext(os.path.basename(filepath))[0]
        safe_name = f"{base}.pkl"
        self.var_output_name.set(safe_name)

    def _select_dir(self):
        directory = filedialog.askdirectory(initialdir=self.var_output_dir.get() or self.processed_dir)
        if directory:
            self.var_output_dir.set(directory)

    def _on_click_process(self):
        csv_path = self.var_csv_path.get().strip()
        out_dir = self.var_output_dir.get().strip()
        out_name = self.var_output_name.get().strip()

        if not csv_path or not os.path.isfile(csv_path):
            messagebox.showerror("Error", "Seleccione un archivo CSV válido.")
            return
        if not out_dir:
            messagebox.showerror("Error", "Seleccione una carpeta de destino.")
            return
        os.makedirs(out_dir, exist_ok=True)
        # Ajustar extensión según formato
        fmt = (self.var_format.get() or "parquet").lower()
        if fmt == 'parquet' and not out_name.lower().endswith('.parquet'):
            out_name = os.path.splitext(out_name)[0] + '.parquet'
        if fmt == 'pkl' and not out_name.lower().endswith('.pkl'):
            out_name = os.path.splitext(out_name)[0] + '.pkl'
        out_path = os.path.join(out_dir, os.path.basename(out_name))
        self.var_output_name.set(os.path.basename(out_name))

        # Deshabilitar botones durante el procesamiento
        self._cancel_event.clear()
        self.btn_process.config(state="disabled")
        self.btn_close.config(state="disabled")
        self.btn_cancel.config(state="normal")

        # Lanzar hilo de procesamiento
        threading.Thread(target=self._process_in_thread, args=(csv_path, out_path, fmt), daemon=True).start()

    def _process_in_thread(self, csv_path: str, out_path: str, fmt: str):
        try:
            # 1) Contar líneas para progreso (puede tardar, pero va en hilo)
            try:
                with open(csv_path, 'r', errors='ignore') as f:
                    total_lines = sum(1 for _ in f)
            except Exception:
                total_lines = 0  # fallback a indeterminado

            # Configurar progreso (en hilo principal)
            def _init_progress():
                if total_lines > 0:
                    self.progress.config(mode='determinate', maximum=total_lines)
                else:
                    self.progress.config(mode='indeterminate')
                    self.progress.start(10)
            self.after(0, _init_progress)

            # 2) Leer por chunks
            chunk_size = 100000  # filas por chunk
            processed = 0
            wrote_any = False
            parquet_writer = None

            if fmt == 'parquet':
                if not HAS_PYARROW:
                    # Fallback automático a PKL si no hay pyarrow
                    fmt = 'pkl'
                    out_path = os.path.splitext(out_path)[0] + '.pkl'

            if fmt == 'parquet':
                try:
                    for chunk in pd.read_csv(
                        csv_path,
                        sep=';',
                        header=None,
                        names=['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'],
                        chunksize=chunk_size
                    ):
                        if self._cancel_event.is_set():
                            # Cancelación: cerrar y eliminar parcial
                            if parquet_writer is not None:
                                parquet_writer.close()
                            try:
                                if os.path.exists(out_path):
                                    os.remove(out_path)
                            except Exception:
                                pass
                            def _on_cancelled():
                                if self.progress.cget('mode') == 'indeterminate':
                                    self.progress.stop()
                                self.lbl_progress.config(text="Cancelado")
                                self.btn_process.config(state="normal")
                                self.btn_close.config(state="normal")
                                self.btn_cancel.config(state="disabled")
                            self.after(0, _on_cancelled)
                            return

                        # Convertir tipos
                        chunk['DateTime'] = pd.to_datetime(chunk['DateTime'], format='%Y%m%d %H%M%S')
                        # Asegurar tipos numéricos
                        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                            chunk[col] = pd.to_numeric(chunk[col], errors='coerce')

                        table = pa.Table.from_pandas(chunk, preserve_index=False)
                        if parquet_writer is None:
                            parquet_writer = pq.ParquetWriter(out_path, table.schema)
                        parquet_writer.write_table(table)
                        wrote_any = True

                        processed += len(chunk)
                        if total_lines > 0:
                            pct = int(min(100, (processed / total_lines) * 100))
                            val = processed
                            self.after(0, lambda v=val, p=pct: self._update_progress(v, p, total_lines))
                finally:
                    if parquet_writer is not None:
                        parquet_writer.close()
            else:
                # PKL: concatenar y guardar al final (puede usar memoria)
                chunks = []
                for chunk in pd.read_csv(
                    csv_path,
                    sep=';',
                    header=None,
                    names=['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'],
                    chunksize=chunk_size
                ):
                    if self._cancel_event.is_set():
                        def _on_cancelled():
                            if self.progress.cget('mode') == 'indeterminate':
                                self.progress.stop()
                            self.lbl_progress.config(text="Cancelado")
                            self.btn_process.config(state="normal")
                            self.btn_close.config(state="normal")
                            self.btn_cancel.config(state="disabled")
                        self.after(0, _on_cancelled)
                        return

                    processed += len(chunk)
                    chunks.append(chunk)

                    if total_lines > 0:
                        pct = int(min(100, (processed / total_lines) * 100))
                        val = processed
                        self.after(0, lambda v=val, p=pct: self._update_progress(v, p, total_lines))

                if chunks:
                    df = pd.concat(chunks, ignore_index=True)
                else:
                    df = pd.DataFrame(columns=['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'])

                df['DateTime'] = pd.to_datetime(df['DateTime'], format='%Y%m%d %H%M%S')
                df.set_index('DateTime', inplace=True)
                df.to_pickle(out_path)

            # Completar progreso al 100%
            def _finish_ok():
                if self.progress.cget('mode') == 'indeterminate':
                    self.progress.stop()
                self.progress.config(mode='determinate')
                self.progress['value'] = self.progress['maximum'] if self.progress['maximum'] else 100
                self.lbl_progress.config(text="100%")
                self.btn_process.config(state="normal")
                self.btn_close.config(state="normal")
                self.btn_cancel.config(state="disabled")
                messagebox.showinfo("Éxito", f"Procesado y guardado en:\n{out_path}")
            self.after(0, _finish_ok)

        except Exception as e:
            def _on_err(msg=str(e)):
                if self.progress.cget('mode') == 'indeterminate':
                    self.progress.stop()
                self.btn_process.config(state="normal")
                self.btn_close.config(state="normal")
                self.btn_cancel.config(state="disabled")
                messagebox.showerror("Error", f"No se pudo procesar el CSV: {msg}")
            self.after(0, _on_err)

    def _update_progress(self, value: int, pct: int, maximum: int):
        try:
            self.progress['maximum'] = maximum
            self.progress['value'] = min(value, maximum)
            self.lbl_progress.config(text=f"{pct}%")
        except Exception:
            pass

    def _on_cancel(self):
        try:
            self._cancel_event.set()
        except Exception:
            pass

    def _on_format_change(self, _evt=None):
        fmt = (self.var_format.get() or "parquet").lower()
        # Actualizar etiqueta
        if fmt == 'parquet':
            self.lbl_name.config(text="Nombre de archivo (.parquet):")
        else:
            self.lbl_name.config(text="Nombre de archivo (.pkl):")
        # Ajustar extensión del nombre actual
        name = self.var_output_name.get().strip()
        if not name:
            name = "processed_data"
        if fmt == 'parquet':
            if not name.lower().endswith('.parquet'):
                name = os.path.splitext(name)[0] + '.parquet'
        else:
            if not name.lower().endswith('.pkl'):
                name = os.path.splitext(name)[0] + '.pkl'
        self.var_output_name.set(name)
