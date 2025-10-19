"""
Unit tests for the BMSSP routing backend.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch
import json
import os
import sys

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test data
SAMPLE_LOCATIONS = ["node_123", "node_456", "node_789"]
SAMPLE_MATRIX = np.array([
    [0.0, 100.0, 200.0],
    [100.0, 0.0, 150.0],
    [200.0, 150.0, 0.0]
])
