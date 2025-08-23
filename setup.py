from setuptools import setup, find_packages

setup(
    name="forex_trader_bot",
    version="1.0.0",
    description="Forex Trading Bot con Tkinter, FinRL y Reinforcement Learning",
    author="jadelmag",
    author_email="kientienemibarraespaciadora@gmail.com",
    packages=find_packages(where="."),
    package_dir={"": "."},
    install_requires=[
        "yfinance==0.2.25",
        "pandas==2.2.3",
        "numpy==1.26.4",
        "matplotlib>=3.8.0",
        "mplfinance>=0.12.10b0",
        "stable-baselines3>=2.7.0",
        "torch>=2.8.0",
        "gymnasium>=0.30.0",          # reemplaza gym
        "tensorboard>=2.15.0",
        "requests==2.32.5",
        "scikit-learn>=1.3.0",
        "websockets==10.4",
        "wrds==3.4.0",
        # FinRL desde GitHub con PEP 508
        "FinRL @ git+https://github.com/AI4Finance-Foundation/FinRL.git",
    ],
    entry_points={
        "console_scripts": [
            "forex-trader-bot=forex_trader_bot.main:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
)

