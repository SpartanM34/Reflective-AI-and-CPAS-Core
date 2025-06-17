from setuptools import setup, find_packages

setup(
    name="cpas_autogen",
    version="0.1.0",
    packages=find_packages(include=["cpas_autogen", "cpas_autogen.*"]),
    description="CPAS AutoGen utilities",
    install_requires=[
        "Flask",
        "streamlit",
        "pandas",
        "matplotlib",
        "sentence-transformers",
        "spacy",
        "scikit-learn",
        "numpy",
        "torch",
        "requests",
        "jsonschema",
    ],
)
