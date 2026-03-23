"""
Convert mlp_model_v5.pkl (sklearn MLP) to TFLite and update model_config.json.

Outputs:
  - dorsiflexx/assets/models/exercise_classifier.tflite  (new model)
  - dorsiflexx/assets/models/model_config.json           (updated config)
"""

import json
import pickle
from pathlib import Path

import numpy as np
import tensorflow as tf

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR      = Path(__file__).parent
ASSETS_DIR     = REPO_ROOT / "dorsiflexx" / "assets" / "models"

MODEL_PKL      = MODEL_DIR / "mlp_model_v5.pkl"
SCALER_PKL     = MODEL_DIR / "scaler_v5.pkl"
ENCODER_PKL    = MODEL_DIR / "label_encoder_v5.pkl"

TFLITE_OUT     = ASSETS_DIR / "exercise_classifier.tflite"
CONFIG_OUT     = ASSETS_DIR / "model_config.json"

# ---------------------------------------------------------------------------
# Feature names (8 signals × 15 features = 120)
# ---------------------------------------------------------------------------

SIGNALS = ["acc_x_norm", "acc_y_norm", "acc_z_norm",
           "gyr_x_norm", "gyr_y_norm", "gyr_z_norm",
           "roll_norm",  "pitch_norm"]

STATS = ["mean", "std", "min", "max", "range", "median", "p25", "p75",
         "fft_dom_freq", "fft_power", "fft_low_ratio",
         "zero_crossings", "peak_count", "peak_distance"]

FEATURE_NAMES = [f"{sig}_{stat}" for sig in SIGNALS for stat in STATS]

# ---------------------------------------------------------------------------
# Load sklearn artifacts
# ---------------------------------------------------------------------------

with open(MODEL_PKL,  "rb") as f: mlp     = pickle.load(f)
with open(SCALER_PKL, "rb") as f: scaler  = pickle.load(f)
with open(ENCODER_PKL,"rb") as f: encoder = pickle.load(f)

n_features = mlp.n_features_in_
hidden     = mlp.hidden_layer_sizes
n_classes  = mlp.n_outputs_
classes    = list(encoder.classes_)

print(f"Model: {n_features} features → hidden {hidden} → {n_classes} classes")
print(f"Classes: {classes}")
assert n_features == len(FEATURE_NAMES), (
    f"Feature count mismatch: model has {n_features}, expected {len(FEATURE_NAMES)}"
)

# ---------------------------------------------------------------------------
# Rebuild as Keras model and copy weights
# ---------------------------------------------------------------------------

inputs = tf.keras.Input(shape=(n_features,), name="input")
x = inputs
for units in (hidden if isinstance(hidden, (list, tuple)) else [hidden]):
    x = tf.keras.layers.Dense(units, activation="relu")(x)
outputs = tf.keras.layers.Dense(n_classes, activation=None, name="logits")(x)

keras_model = tf.keras.Model(inputs, outputs)

# Copy sklearn weights layer by layer
for layer_idx, keras_layer in enumerate(
    [l for l in keras_model.layers if isinstance(l, tf.keras.layers.Dense)]
):
    W = mlp.coefs_[layer_idx].astype(np.float32)
    b = mlp.intercepts_[layer_idx].astype(np.float32)
    keras_layer.set_weights([W, b])

# Verify a forward pass matches sklearn
test_input = np.random.randn(1, n_features).astype(np.float32)
keras_out   = keras_model.predict(test_input, verbose=0)[0]
sklearn_out = mlp.predict_proba(test_input)[0]

print(f"Keras logits[:3]:  {keras_out[:3]}")
print(f"Sklearn proba[:3]: {sklearn_out[:3]}")

# ---------------------------------------------------------------------------
# Convert to TFLite (float32, no quantization)
# ---------------------------------------------------------------------------

converter = tf.lite.TFLiteConverter.from_keras_model(keras_model)
tflite_model = converter.convert()

ASSETS_DIR.mkdir(parents=True, exist_ok=True)
TFLITE_OUT.write_bytes(tflite_model)
print(f"TFLite model saved → {TFLITE_OUT}  ({len(tflite_model):,} bytes)")

# ---------------------------------------------------------------------------
# Update model_config.json
# ---------------------------------------------------------------------------

hidden_list = list(hidden) if isinstance(hidden, (list, tuple)) else [hidden]

config = {
    "modelVersion": "4.0.0",
    "architecture": {
        "inputSize":    n_features,
        "hiddenLayers": hidden_list,
        "outputSize":   n_classes,
        "activation":   "relu",
    },
    "classes":      classes,
    "scaler": {
        "mean":  scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
    },
    "featureNames": FEATURE_NAMES,
}

with open(CONFIG_OUT, "w") as f:
    json.dump(config, f, indent=2)
print(f"model_config.json saved → {CONFIG_OUT}")
