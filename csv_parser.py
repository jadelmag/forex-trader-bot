import os
import pandas as pd

class DukascopyCSVParser:
    """
    Parser para convertir CSV crudos de Dukascopy al formato estándar:
    - Índice: DatetimeIndex
    - Columnas: Open, High, Low, Close, Volume
    """

    @staticmethod
    def parse_file(filepath, output_dir="csv/processed"):
        # Leer CSV sin headers y separador ;
        df = pd.read_csv(filepath, header=None, sep=';')

        # Asignar nombres de columnas
        df.columns = ['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']

        # Convertir a datetime
        df['DateTime'] = pd.to_datetime(df['DateTime'], format='%Y%m%d %H%M%S')
        df.set_index('DateTime', inplace=True)

        # Crear carpeta de salida si no existe
        os.makedirs(output_dir, exist_ok=True)

        # Construir nombre de archivo procesado
        base_name = os.path.basename(filepath)
        parts = base_name.replace(".csv","").split("_")
        if len(parts) >= 5:
            symbol = parts[2]       # Ej: EURUSD
            timeframe = parts[3]    # Ej: M1
            year = parts[4]         # Ej: 2024
            output_file = f"{symbol}_{timeframe}_{year}.csv"
        else:
            output_file = f"processed_{base_name}"

        output_path = os.path.join(output_dir, output_file)

        # Guardar CSV procesado
        df.to_csv(output_path)
        print(f"✅ Archivo procesado y guardado en: {output_path}")
        return output_path

    @staticmethod
    def batch_parse(input_dir="csv/raw", output_dir="csv/processed"):
        """
        Procesa todos los CSV en input_dir y los guarda en output_dir.
        """
        os.makedirs(output_dir, exist_ok=True)
        for filename in os.listdir(input_dir):
            if filename.endswith(".csv"):
                filepath = os.path.join(input_dir, filename)
                try:
                    DukascopyCSVParser.parse_file(filepath, output_dir)
                except Exception as e:
                    print(f"⚠️ Error procesando {filename}: {e}")


if __name__ == "__main__":
    # Procesar todos los CSV crudos automáticamente
    DukascopyCSVParser.batch_parse()
