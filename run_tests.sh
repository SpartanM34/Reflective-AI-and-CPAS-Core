#!/bin/bash
set -e
pip install -r requirements.txt
pytest -q
