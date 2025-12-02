#!/usr/bin/env python3
"""Run Streamlit app."""

import subprocess
import sys
from pathlib import Path

app = Path(__file__).parent / "web" / "streamlit" / "app.py"
subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)])
