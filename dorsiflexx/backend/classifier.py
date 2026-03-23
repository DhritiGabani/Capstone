"""
TFLite inference wrapper for dorsiflexx backend.
"""

import json
import numpy as np

from config import MODEL_PATH, MODEL_CONFIG_PATH


class ExerciseClassifier:
    def __init__(self) -> None:
        try:
            from ai_edge_litert.interpreter import Interpreter
        except ImportError:
            try:
                from tflite_runtime.interpreter import Interpreter
            except ImportError:
                from tensorflow.lite.python.interpreter import Interpreter

        self.interpreter = Interpreter(model_path=MODEL_PATH)
        self.interpreter.allocate_tensors()

        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        with open(MODEL_CONFIG_PATH, "r") as f:
            config = json.load(f)
        self.classes = config["classes"]

    def classify(self, features: list[float]) -> dict:
        """
        Run inference on a single feature vector (112 floats).

        Returns:
            {"predicted_class": str, "confidence": float}
        """
        input_data = np.array([features], dtype=np.float32)
        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
        self.interpreter.invoke()

        output_data = self.interpreter.get_tensor(self.output_details[0]["index"])[0]

        # Apply softmax
        exp_values = np.exp(output_data - np.max(output_data))
        probabilities = exp_values / np.sum(exp_values)

        predicted_idx = int(np.argmax(probabilities))
        return {
            "predicted_class": self.classes[predicted_idx],
            "confidence": float(probabilities[predicted_idx]),
        }
