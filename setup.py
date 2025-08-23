from setuptools import setup, find_packages

setup(
    name="forex_trader_bot",
    version="1.0.0",
    description="Forex Trading Bot con Tkinter, FinRL y Reinforcement Learning",
    author="jadelmag",
    author_email="kientienemibarraespaciadora@gmail.com",
    packages=find_packages(where="app"),
    package_dir={"": "app"},
    install_requires=[
        "yfinance==0.2.25",       # compatible con websockets<11
        "pandas>=2.1.0",
        "numpy>=2.3.0",
        "matplotlib>=3.8.0",
        "mplfinance>=0.12.10b0",
        "stable-baselines3>=2.7.0",
        "torch>=2.8.0",
        "gym>=0.26.0",
        "tensorboard>=2.15.0",
        "scikit-learn>=1.3.0",
        "websockets==10.4"        # compatible con alpaca-trade-api
    ],
    entry_points={
        "console_scripts": [
            "forex-trader-bot=main:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
)
