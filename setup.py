from setuptools import setup, find_packages

setup(
    name="trademesh",
    version="0.1.0",
    description="Universal trading execution layer — one interface, any venue",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Miracle Universe Inc.",
    author_email="charles@miracleuniverse.com",
    url="https://github.com/miracleuniverse/trademesh",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "simmer": ["simmer-sdk"],
        "robinhood": ["robin-stocks"],
        "alpaca": ["alpaca-trade-api"],
        "all": ["simmer-sdk", "robin-stocks", "alpaca-trade-api"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    keywords="trading, algotrading, polymarket, robinhood, alpaca, options, prediction markets",
)
