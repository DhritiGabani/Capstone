"""
Configuration constants for dorsiflexx backend.
"""

import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_CONFIG_PATH = os.environ.get(
    "MODEL_CONFIG_PATH",
    os.path.join(_BASE_DIR, "assets", "models", "model_config.json"),
)
MODEL_PATH = os.environ.get(
    "MODEL_PATH",
    os.path.join(_BASE_DIR, "assets", "models", "exercise_classifier.tflite"),
)
DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(_BASE_DIR, "dorsiflexx.db"),
)

TOTAL_FEATURES = 64
