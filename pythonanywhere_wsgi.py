#!/usr/bin/env python
"""
PythonAnywhere WSGI Configuration for STN Diklat Panel

This file is required for deployment on PythonAnywhere.
Place this in the root directory and configure it in PythonAnywhere settings.

Path: /home/username/STN-diklat-panel/pythonanywhere_wsgi.py
"""

import os
import sys

# Add the project directory to the Python path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = 'False'

# Load environment variables from .env file if it exists
from dotenv import load_dotenv
env_path = os.path.join(project_home, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # Fallback: load from .env.example as template
    load_dotenv(os.path.join(project_home, '.env.example'))

# Create Flask app
from run import app

# WSGI entry point
application = app
