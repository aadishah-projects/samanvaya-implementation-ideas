from setuptools import setup, find_packages

setup(
    name="openimis-be-samanvaya",
    version="1.0.0",
    description="Samanvaya — Payment Execution Module for OpenIMIS (replaces SOSYS)",
    long_description=(
        "Native OpenIMIS module that handles bulk payment disbursement, "
        "transaction ledger, gateway integration, and SOSYS reconciliation. "
        "Closes the financial loop that OpenIMIS was missing."
    ),
    author="Samanvaya Team",
    license="AGPL-3.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.27",
    ],
    python_requires=">=3.10",
)
