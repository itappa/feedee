import os

from .base import *

DEBUG = True

# Vite dev server (HMR)
VITE_DEV_MODE = True
VITE_DEV_URL = os.environ.get("VITE_DEV_URL", "http://localhost:5173")
