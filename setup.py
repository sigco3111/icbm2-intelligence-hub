from setuptools import setup, find_packages

setup(
    name="icbm2-hub-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn>=0.27.0",
        "pydantic-settings>=2.0.0",
        "aiosqlite>=0.19.0",
        "httpx>=0.27.0",
        "beautifulsoup4>=4.12.0",
    ],
)
