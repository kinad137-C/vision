#!/usr/bin/env python3
"""Run Streamlit app."""

import subprocess
import sys
from pathlib import Path

# Add project to path
project = Path(__file__).parent
sys.path.insert(0, str(project))

# Run app
app = project / "src" / "app.py"
subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)])
