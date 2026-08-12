from setuptools import setup, find_packages

setup(
    name="cpas_autogen",
    version="0.1.0",
    packages=find_packages(include=["cpas_autogen", "cpas_autogen.*", "cpas", "cpas.*"]),
    description="CPAS legacy utilities and CPAS-Core v2 reference protocols",
    install_requires=[
        "pandas",
        "matplotlib",
        "sentence-transformers",
        "spacy",
        "scikit-learn",
        "numpy",
        "torch",
        "requests",
        "jsonschema",
        "rfc8785==0.1.4",
    ],
    extras_require={
        "web": ["Flask", "streamlit"],
    },
)
