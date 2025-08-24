from setuptools import setup, find_packages

setup(
    name="forex_trader_bot",
    version="1.0.0",
    description="Visualizador avanzado de datos Forex CSV con gráficos de velas",
    author="jadelmag",
    author_email="kientienemibarraespaciadora@gmail.com",
    
    # Paquetes a incluir
    packages=find_packages(where="."),
    package_dir={"": "."},
    
    # Incluir archivos de datos importantes
    package_data={
        '': ['*.csv', '*.pkl', '*.png'],
    },
    include_package_data=True,
    
    # Dependencias optimizadas
    install_requires=[
        "pandas==2.2.3",           # Manejo de datos CSV
        "numpy==1.26.4",           # Operaciones numéricas
        "matplotlib==3.8.0",       # Gráficos básicos
        "mplfinance==0.12.10b0",   # Gráficos de velas
        "scikit-learn==1.3.0",     # Para análisis técnico futuro
    ],
    
    # Scripts de consola
    entry_points={
        "console_scripts": [
            "forex-viewer=app.main:main"          # Viewer principal
        ]
    },
    
    # Metadatos adicionales
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Visualization",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="forex, csv, visualization, candlestick, dukascopy",
    python_requires=">=3.8",
    
    # URLs del proyecto
    url="https://github.com/jadelmag/forex-trader-bot",
    project_urls={
        "Bug Reports": "https://github.com/jadelmag/forex-trader-bot/issues",
        "Source": "https://github.com/jadelmag/forex-trader-bot",
    },
)