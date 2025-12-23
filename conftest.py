import sys
import os

# Add the project root (app/) to sys.path so 'core' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
