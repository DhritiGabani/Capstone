#!/usr/bin/env python3
"""
Convert scikit-learn MLPClassifier to TensorFlow Lite for React Native deployment.

This script:
1. Loads the trained sklearn MLP model from pickle
2. Creates an equivalent TensorFlow/Keras model
3. Transfers the weights from sklearn to Keras
4. Converts to TFLite format
5. Exports scaler parameters and metadata to JSON

Output files are saved to dorsiflexx/assets/models/
"""

import pickle
import json
import os
import numpy as np

# TensorFlow imports
import tensorflow as tf
from tensorflow import keras

# Path configuration
PICKLE_PATH = "/Users/dhritigabani/Capstone/mlp_model_v2.pkl"
OUTPUT_DIR = "/Users/dhritigabani/Capstone/dorsiflexx/assets/models"

def load_sklearn_model(pickle_path: str) -> dict:
    """Load the sklearn model, scaler, and label encoder from pickle."""
    print(f"Loading model from {pickle_path}...")
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)

    # Handle both dict format and direct model format
    if isinstance(data, dict):
        model = data.get('model') or data.get('classifier') or data.get('mlp')
        scaler = data.get('scaler')
        label_encoder = data.get('label_encoder') or data.get('encoder')
    else:
        # Assume it's just the model
        model = data
        scaler = None
        label_encoder = None

    print(f"Model type: {type(model)}")
    if scaler:
        print(f"Scaler type: {type(scaler)}")
    if label_encoder:
        print(f"Label encoder classes: {label_encoder.classes_.tolist()}")

    return {
        'model': model,
        'scaler': scaler,
        'label_encoder': label_encoder
    }


def inspect_sklearn_model(model) -> dict:
    """Extract architecture details from sklearn MLPClassifier."""
    print("\n--- Inspecting sklearn MLP model ---")

    # Get layer sizes
    n_features = model.n_features_in_
    hidden_layers = model.hidden_layer_sizes
    if isinstance(hidden_layers, int):
        hidden_layers = (hidden_layers,)
    n_outputs = model.n_outputs_

    print(f"Input features: {n_features}")
    print(f"Hidden layers: {hidden_layers}")
    print(f"Output classes: {n_outputs}")
    print(f"Activation: {model.activation}")
    print(f"Output activation: {model.out_activation_}")

    # Get weights and biases
    weights = model.coefs_  # List of weight matrices
    biases = model.intercepts_  # List of bias vectors

    print(f"\nWeight shapes:")
    for i, w in enumerate(weights):
        print(f"  Layer {i}: {w.shape}")

    return {
        'n_features': n_features,
        'hidden_layers': hidden_layers,
        'n_outputs': n_outputs,
        'activation': model.activation,
        'out_activation': model.out_activation_,
        'weights': weights,
        'biases': biases
    }


def build_keras_model(arch: dict) -> keras.Model:
    """Build an equivalent Keras model with the same architecture."""
    print("\n--- Building Keras model ---")

    # Map sklearn activation to Keras
    activation_map = {
        'relu': 'relu',
        'tanh': 'tanh',
        'logistic': 'sigmoid',
        'identity': 'linear'
    }
    hidden_activation = activation_map.get(arch['activation'], 'relu')

    # Build sequential model
    model = keras.Sequential()

    # Input layer
    model.add(keras.layers.InputLayer(input_shape=(arch['n_features'],)))

    # Hidden layers
    for i, units in enumerate(arch['hidden_layers']):
        model.add(keras.layers.Dense(
            units,
            activation=hidden_activation,
            name=f'hidden_{i}'
        ))

    # Output layer
    output_activation = 'softmax' if arch['out_activation'] == 'softmax' else 'linear'
    model.add(keras.layers.Dense(
        arch['n_outputs'],
        activation=output_activation,
        name='output'
    ))

    model.summary()
    return model


def transfer_weights(keras_model: keras.Model, arch: dict):
    """Transfer weights from sklearn to Keras model."""
    print("\n--- Transferring weights ---")

    weights = arch['weights']
    biases = arch['biases']

    layer_idx = 0
    for layer in keras_model.layers:
        if hasattr(layer, 'kernel'):  # Dense layer
            w = weights[layer_idx]
            b = biases[layer_idx]

            print(f"Setting weights for {layer.name}: kernel={w.shape}, bias={b.shape}")
            layer.set_weights([w, b])
            layer_idx += 1

    print(f"Transferred {layer_idx} layer weights")


def verify_conversion(sklearn_model, keras_model, scaler, n_samples: int = 10) -> bool:
    """Verify that Keras model produces same outputs as sklearn."""
    print("\n--- Verifying conversion ---")

    # Generate random test data
    n_features = sklearn_model.n_features_in_
    np.random.seed(42)
    X_test = np.random.randn(n_samples, n_features).astype(np.float32)

    # Apply scaler if present
    if scaler is not None:
        X_scaled = scaler.transform(X_test)
    else:
        X_scaled = X_test

    # Get sklearn predictions
    sklearn_probs = sklearn_model.predict_proba(X_scaled)

    # Get Keras predictions
    keras_probs = keras_model.predict(X_scaled.astype(np.float32), verbose=0)

    # Compare
    max_diff = np.max(np.abs(sklearn_probs - keras_probs))
    mean_diff = np.mean(np.abs(sklearn_probs - keras_probs))

    print(f"Max probability difference: {max_diff:.8f}")
    print(f"Mean probability difference: {mean_diff:.8f}")

    if max_diff < 1e-5:
        print("✓ Conversion verified - predictions match!")
        return True
    else:
        print("⚠ Warning: Predictions differ slightly")
        return False


def convert_to_tflite(keras_model: keras.Model, output_path: str):
    """Convert Keras model to TFLite format."""
    print("\n--- Converting to TFLite ---")

    # Convert to TFLite
    converter = tf.lite.TFLiteConverter.from_keras_model(keras_model)

    # Optimize for mobile
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

    # Convert
    tflite_model = converter.convert()

    # Save
    with open(output_path, 'wb') as f:
        f.write(tflite_model)

    size_kb = len(tflite_model) / 1024
    print(f"Saved TFLite model to {output_path}")
    print(f"Model size: {size_kb:.2f} KB")

    return tflite_model


def verify_tflite(tflite_path: str, keras_model: keras.Model, scaler, n_samples: int = 5):
    """Verify TFLite model produces same outputs as Keras."""
    print("\n--- Verifying TFLite model ---")

    # Load TFLite model
    interpreter = tf.lite.Interpreter(model_path=tflite_path)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    print(f"Input shape: {input_details[0]['shape']}")
    print(f"Input dtype: {input_details[0]['dtype']}")
    print(f"Output shape: {output_details[0]['shape']}")

    # Generate test data
    n_features = input_details[0]['shape'][1]
    np.random.seed(42)
    X_test = np.random.randn(n_samples, n_features).astype(np.float32)

    # Apply scaler if present
    if scaler is not None:
        X_scaled = scaler.transform(X_test).astype(np.float32)
    else:
        X_scaled = X_test

    # Get Keras predictions
    keras_probs = keras_model.predict(X_scaled, verbose=0)

    # Get TFLite predictions
    tflite_probs = []
    for i in range(n_samples):
        interpreter.set_tensor(input_details[0]['index'], X_scaled[i:i+1])
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]['index'])
        tflite_probs.append(output[0])
    tflite_probs = np.array(tflite_probs)

    # Compare
    max_diff = np.max(np.abs(keras_probs - tflite_probs))
    print(f"Max difference between Keras and TFLite: {max_diff:.8f}")

    if max_diff < 1e-5:
        print("✓ TFLite model verified!")
    else:
        print("⚠ Small differences (expected due to quantization)")


def export_config(scaler, label_encoder, arch: dict, output_path: str):
    """Export scaler parameters and model metadata to JSON."""
    print("\n--- Exporting configuration ---")

    config = {
        'modelVersion': '1.0.0',
        'architecture': {
            'inputSize': arch['n_features'],
            'hiddenLayers': list(arch['hidden_layers']),
            'outputSize': arch['n_outputs'],
            'activation': arch['activation']
        },
        'classes': [],
        'scaler': None,
        'featureNames': []
    }

    # Add class labels
    if label_encoder is not None:
        config['classes'] = label_encoder.classes_.tolist()
    else:
        # Default class names based on plan
        config['classes'] = ['Ankle Rotation', 'Calf Raises', 'Heel Walk']

    # Add scaler parameters
    if scaler is not None:
        config['scaler'] = {
            'mean': scaler.mean_.tolist(),
            'scale': scaler.scale_.tolist()
        }

    # Generate feature names (8 features x 8 windows = 64)
    base_features = [
        'accel_x', 'accel_y', 'accel_z',
        'gyro_x', 'gyro_y', 'gyro_z',
        'accel_magnitude', 'gyro_magnitude'
    ]
    n_windows = arch['n_features'] // len(base_features)
    feature_names = []
    for window in range(n_windows):
        for feature in base_features:
            feature_names.append(f'{feature}_w{window}')
    config['featureNames'] = feature_names

    # Save JSON
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Saved configuration to {output_path}")
    print(f"Classes: {config['classes']}")
    if config['scaler']:
        print(f"Scaler mean length: {len(config['scaler']['mean'])}")
        print(f"Scaler scale length: {len(config['scaler']['scale'])}")


def main():
    """Main conversion pipeline."""
    print("=" * 60)
    print("MLP Model Conversion: sklearn -> TensorFlow Lite")
    print("=" * 60)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Load sklearn model
    data = load_sklearn_model(PICKLE_PATH)
    sklearn_model = data['model']
    scaler = data['scaler']
    label_encoder = data['label_encoder']

    # Step 2: Inspect model architecture
    arch = inspect_sklearn_model(sklearn_model)

    # Step 3: Build equivalent Keras model
    keras_model = build_keras_model(arch)

    # Step 4: Transfer weights
    transfer_weights(keras_model, arch)

    # Step 5: Verify conversion
    verify_conversion(sklearn_model, keras_model, scaler)

    # Step 6: Convert to TFLite
    tflite_path = os.path.join(OUTPUT_DIR, "exercise_classifier.tflite")
    convert_to_tflite(keras_model, tflite_path)

    # Step 7: Verify TFLite model
    verify_tflite(tflite_path, keras_model, scaler)

    # Step 8: Export configuration
    config_path = os.path.join(OUTPUT_DIR, "model_config.json")
    export_config(scaler, label_encoder, arch, config_path)

    print("\n" + "=" * 60)
    print("Conversion complete!")
    print(f"TFLite model: {tflite_path}")
    print(f"Config file: {config_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
