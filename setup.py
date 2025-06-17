from setuptools import setup, find_packages

setup(
    name="cpas_autogen",
    version="0.1.1",
    packages=find_packages(include=["cpas_autogen", "cpas_autogen.*"]),
    description="CPAS AutoGen utilities",
    install_requires=[
        "flask",
        "numpy",
        "sentence-transformers",
    ],
)
