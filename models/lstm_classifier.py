"""
LSTM Model for Exercise Classification
Classifies Ankle Rotations, Heel Walking, and Calf Raises

Architecture:
- Bidirectional LSTM for temporal pattern learning
- Dropout for regularization
- Training on segmented data (clean reps)
- Testing on unsegmented data (sliding window)

Split: 80/10/10 (train/val/test)
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
import json
import pickle
from pathlib import Path


class LSTMExerciseClassifier:
    def __init__(self, input_shape, num_classes, lstm_units=[32], dropout_rate=0.5, l2_reg=0.01):
        """
        Initialize LSTM classifier with strong regularization

        Args:
            input_shape: (sequence_length, num_features)
            num_classes: Number of exercise classes
            lstm_units: List of units for each LSTM layer (simplified to single layer)
            dropout_rate: Dropout rate for regularization (increased to 0.5)
            l2_reg: L2 regularization strength
        """
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.l2_reg = l2_reg
        self.label_encoder = LabelEncoder()
        self.model = None
        self.history = None

    def build_model(self):
        """Build LSTM architecture with strong regularization to prevent overfitting"""
        from tensorflow.keras import regularizers

        model = keras.Sequential([
            # Input layer
            layers.Input(shape=self.input_shape),

            # Single Bidirectional LSTM layer (simplified from 2 layers)
            layers.Bidirectional(layers.LSTM(
                self.lstm_units[0],
                dropout=self.dropout_rate,
                recurrent_dropout=self.dropout_rate,  # Increased from 0.2 to dropout_rate
                kernel_regularizer=regularizers.l2(self.l2_reg),
                recurrent_regularizer=regularizers.l2(self.l2_reg)
            )),
            layers.BatchNormalization(),
            layers.Dropout(self.dropout_rate),

            # Simplified dense layers with L2 regularization
            layers.Dense(32,
                        activation='relu',
                        kernel_regularizer=regularizers.l2(self.l2_reg)),
            layers.Dropout(self.dropout_rate),

            # Output layer
            layers.Dense(self.num_classes, activation='softmax')
        ])

        # Compile model
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )

        self.model = model
        return model

    def prepare_sequences(self, df, max_length=None):
        """
        Prepare sequences from segmented data

        Args:
            df: DataFrame with segmented data
            max_length: Maximum sequence length (for padding)

        Returns:
            X: Padded sequences (n_samples, max_length, n_features)
            y: Labels
            max_length: Actual max length used
        """
        sequences = []
        labels = []

        print(f"Processing {len(df)} segments...")

        for idx, row in df.iterrows():
            # Extract sensor signals
            signals = []
            for signal_name in ['acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z']:
                if isinstance(row[signal_name], str):
                    clean_str = row[signal_name].strip('[]').replace('\n', ' ')
                    signal_values = np.fromstring(clean_str, sep=' ')
                else:
                    signal_values = np.array(row[signal_name])
                signals.append(signal_values)

            # Stack signals into feature matrix (time_steps, features)
            sequence = np.column_stack(signals)
            sequences.append(sequence)
            labels.append(row['exercise'])

        # Find max length if not specified
        if max_length is None:
            max_length = max(len(seq) for seq in sequences)
            print(f"Max sequence length: {max_length}")

        # Pad sequences to same length
        X = np.array([self._pad_sequence(seq, max_length) for seq in sequences])
        y = np.array(labels)

        print(f"Prepared sequences: {X.shape}")
        print(f"Labels: {y.shape}")

        return X, y, max_length

    def _pad_sequence(self, sequence, max_length):
        """Pad or truncate sequence to max_length"""
        if len(sequence) >= max_length:
            return sequence[:max_length]
        else:
            # Pad with zeros
            padding = np.zeros((max_length - len(sequence), sequence.shape[1]))
            return np.vstack([sequence, padding])

    def train(self, X_train, y_train, X_val, y_val, epochs=100, batch_size=32):
        """
        Train the LSTM model

        Args:
            X_train: Training sequences
            y_train: Training labels
            X_val: Validation sequences
            y_val: Validation labels
            epochs: Maximum number of epochs
            batch_size: Batch size
        """
        # Encode labels
        y_train_encoded = self.label_encoder.fit_transform(y_train)
        y_val_encoded = self.label_encoder.transform(y_val)

        print(f"\nTraining on {len(X_train)} samples, validating on {len(X_val)} samples")
        print(f"Classes: {self.label_encoder.classes_}")

        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=15,
                restore_best_weights=True,
                verbose=1
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-6,
                verbose=1
            ),
            ModelCheckpoint(
                'results/lstm_model/best_model.h5',
                monitor='val_accuracy',
                save_best_only=True,
                verbose=1
            )
        ]

        # Train
        self.history = self.model.fit(
            X_train, y_train_encoded,
            validation_data=(X_val, y_val_encoded),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )

        return self.history

    def predict(self, X):
        """Make predictions"""
        y_pred_proba = self.model.predict(X, verbose=0)
        y_pred_encoded = np.argmax(y_pred_proba, axis=1)
        return self.label_encoder.inverse_transform(y_pred_encoded)

    def predict_proba(self, X):
        """Get prediction probabilities"""
        return self.model.predict(X, verbose=0)

    def evaluate(self, X, y, dataset_name="Test"):
        """Evaluate model and print metrics"""
        y_pred = self.predict(X)

        print(f"\n{'='*60}")
        print(f"{dataset_name} Set Results")
        print(f"{'='*60}")
        print(f"Accuracy: {accuracy_score(y, y_pred):.4f}")
        print(f"\nClassification Report:")
        print(classification_report(y, y_pred))

        return y_pred

    def plot_confusion_matrix(self, y_true, y_pred, title="Confusion Matrix", save_path=None):
        """Plot confusion matrix"""
        cm = confusion_matrix(y_true, y_pred, labels=self.label_encoder.classes_)

        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=self.label_encoder.classes_,
                   yticklabels=self.label_encoder.classes_)
        plt.title(title)
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved confusion matrix to {save_path}")
        plt.close()

    def plot_training_history(self, save_path=None):
        """Plot training history"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

        # Accuracy
        ax1.plot(self.history.history['accuracy'], label='Train Accuracy')
        ax1.plot(self.history.history['val_accuracy'], label='Val Accuracy')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Accuracy')
        ax1.set_title('Model Accuracy')
        ax1.legend()
        ax1.grid(True)

        # Loss
        ax2.plot(self.history.history['loss'], label='Train Loss')
        ax2.plot(self.history.history['val_loss'], label='Val Loss')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Loss')
        ax2.set_title('Model Loss')
        ax2.legend()
        ax2.grid(True)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved training history to {save_path}")
        plt.close()

    def save_model(self, model_path, encoder_path):
        """Save model and label encoder"""
        self.model.save(model_path)
        with open(encoder_path, 'wb') as f:
            pickle.dump(self.label_encoder, f)
        print(f"Model saved to {model_path}")
        print(f"Encoder saved to {encoder_path}")

    def load_model(self, model_path, encoder_path):
        """Load model and label encoder"""
        self.model = keras.models.load_model(model_path)
        with open(encoder_path, 'rb') as f:
            self.label_encoder = pickle.load(f)
        print(f"Model loaded from {model_path}")


def create_subject_splits(all_subjects, random_seed=42):
    """Split subjects into train/val/test sets (80/10/10)"""
    np.random.seed(random_seed)
    subjects = np.array(all_subjects)
    np.random.shuffle(subjects)

    # Same splits as KNN for fair comparison
    train_subjects = subjects[:21].tolist()
    val_subjects = subjects[21:24].tolist()
    test_subjects = subjects[24:27].tolist()

    return train_subjects, val_subjects, test_subjects


def prepare_unsegmented_test_data(df_clean, test_subjects, classifier, window_size=100, overlap=50):
    """
    Prepare test data from full unsegmented files using sliding window

    Args:
        df_clean: DataFrame with full unsegmented data
        test_subjects: List of subject IDs for testing
        classifier: Classifier instance (for max_length)
        window_size: Number of timesteps in each window
        overlap: Number of overlapping timesteps

    Returns:
        X_test, y_test
    """
    print(f"\nPreparing unsegmented test data for subjects: {test_subjects}")
    print(f"Window size: {window_size}, Overlap: {overlap}")

    # Filter for test subjects and target exercises
    df_test = df_clean[df_clean['subject_id'].isin(test_subjects)]
    df_test = df_test[df_test['exercise'].isin(['Ankle Rotation', 'Calf Raises', 'Heel Walk'])]

    sequences = []
    labels = []

    # Group by subject, exercise, and file
    for (subject, exercise, file_path), group in df_test.groupby(['subject_id', 'exercise', 'file_path']):
        group = group.sort_values('time').reset_index(drop=True)

        # Skip if too few samples
        if len(group) < window_size:
            continue

        # Sliding window
        step_size = window_size - overlap
        for start_idx in range(0, len(group) - window_size + 1, step_size):
            window = group.iloc[start_idx:start_idx + window_size]

            # Extract sensor signals
            signals = []
            for signal_name in ['acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z']:
                signals.append(window[signal_name].values)

            # Stack into sequence
            sequence = np.column_stack(signals)
            sequences.append(sequence)
            labels.append(exercise)

    X_test = np.array(sequences)
    y_test = np.array(labels)

    print(f"Created {len(X_test)} test windows from unsegmented data")
    print(f"Shape: {X_test.shape}")

    return X_test, y_test


def main():
    """Main training and evaluation pipeline"""

    # Set random seeds for reproducibility
    np.random.seed(42)
    tf.random.set_seed(42)

    # Create output directories
    Path('results/lstm_model').mkdir(parents=True, exist_ok=True)

    print("="*60)
    print("LSTM Exercise Classifier - Training Pipeline")
    print("="*60)

    # Load data
    print("\nLoading data...")
    df_segmented = pd.read_csv('results/segmented_signals.csv')
    df_clean = pd.read_csv('results/clean_signals.csv')

    # Filter for target exercises
    target_exercises = ['Ankle Rotation', 'Calf Raises', 'Heel Walk']
    df_segmented = df_segmented[df_segmented['exercise'].isin(target_exercises)]

    print(f"Loaded {len(df_segmented)} segmented samples")
    print(f"Loaded {len(df_clean)} full data samples")

    # Create subject splits
    all_subjects = sorted(df_segmented['subject_id'].unique())
    train_subjects, val_subjects, test_subjects = create_subject_splits(all_subjects)

    print(f"\nSubject splits:")
    print(f"Train ({len(train_subjects)}): {train_subjects}")
    print(f"Val ({len(val_subjects)}): {val_subjects}")
    print(f"Test ({len(test_subjects)}): {test_subjects}")

    # Save splits
    splits = {
        'train': train_subjects,
        'val': val_subjects,
        'test': test_subjects
    }
    with open('results/lstm_model/subject_splits.json', 'w') as f:
        json.dump(splits, f, indent=2)

    # Prepare data
    print("\n" + "="*60)
    print("Preparing Training Data (Segmented)")
    print("="*60)

    df_train = df_segmented[df_segmented['subject_id'].isin(train_subjects)]
    df_val = df_segmented[df_segmented['subject_id'].isin(val_subjects)]

    # Create temporary classifier to prepare sequences
    temp_classifier = LSTMExerciseClassifier(
        input_shape=(None, 6),  # Will be updated
        num_classes=3
    )

    X_train, y_train, max_length = temp_classifier.prepare_sequences(df_train)
    X_val, y_val, _ = temp_classifier.prepare_sequences(df_val, max_length=max_length)

    print(f"\nClass distribution (train):\n{pd.Series(y_train).value_counts()}")
    print(f"\nClass distribution (val):\n{pd.Series(y_val).value_counts()}")

    # Build and train model
    print("\n" + "="*60)
    print("Building LSTM Model (Regularized to Reduce Overfitting)")
    print("="*60)

    classifier = LSTMExerciseClassifier(
        input_shape=(max_length, 6),  # 6 features: acc_x, acc_y, acc_z, gyr_x, gyr_y, gyr_z
        num_classes=3,
        lstm_units=[32],  # Simplified: single layer instead of [64, 32]
        dropout_rate=0.5,  # Increased from 0.3
        l2_reg=0.01  # Added L2 regularization
    )

    model = classifier.build_model()
    print(model.summary())

    # Train
    print("\n" + "="*60)
    print("Training LSTM Model")
    print("="*60)

    history = classifier.train(X_train, y_train, X_val, y_val, epochs=100, batch_size=32)

    # Plot training history
    classifier.plot_training_history('results/lstm_model/training_history.png')

    # Evaluate on training set
    print("\n" + "="*60)
    print("Training Set Performance")
    print("="*60)
    y_train_pred = classifier.evaluate(X_train, y_train, "Training")
    classifier.plot_confusion_matrix(y_train, y_train_pred,
                                    "Training Set Confusion Matrix",
                                    "results/lstm_model/confusion_matrix_train.png")

    # Evaluate on validation set
    y_val_pred = classifier.evaluate(X_val, y_val, "Validation")
    classifier.plot_confusion_matrix(y_val, y_val_pred,
                                    "Validation Set Confusion Matrix",
                                    "results/lstm_model/confusion_matrix_val.png")

    # Prepare test data (unsegmented)
    print("\n" + "="*60)
    print("Preparing Test Data (Full Unsegmented Files)")
    print("="*60)

    X_test, y_test = prepare_unsegmented_test_data(
        df_clean, test_subjects, classifier,
        window_size=100, overlap=50
    )

    print(f"\nClass distribution (test):\n{pd.Series(y_test).value_counts()}")

    # Evaluate on test set
    y_test_pred = classifier.evaluate(X_test, y_test, "Test (Unsegmented)")
    classifier.plot_confusion_matrix(y_test, y_test_pred,
                                    "Test Set Confusion Matrix (Unsegmented)",
                                    "results/lstm_model/confusion_matrix_test.png")

    # Save model
    classifier.save_model(
        'results/lstm_model/lstm_model.h5',
        'results/lstm_model/label_encoder.pkl'
    )

    # Save results summary
    results_summary = {
        'model_architecture': {
            'lstm_units': classifier.lstm_units,
            'dropout_rate': classifier.dropout_rate,
            'l2_regularization': classifier.l2_reg,
            'max_sequence_length': int(max_length),
            'num_features': 6,
            'improvements': 'Stronger regularization to reduce overfitting'
        },
        'train_accuracy': float(accuracy_score(y_train, y_train_pred)),
        'val_accuracy': float(accuracy_score(y_val, y_val_pred)),
        'test_accuracy': float(accuracy_score(y_test, y_test_pred)),
        'train_samples': int(len(X_train)),
        'val_samples': int(len(X_val)),
        'test_samples': int(len(X_test)),
        'classes': classifier.label_encoder.classes_.tolist(),
        'epochs_trained': len(history.history['loss'])
    }

    with open('results/lstm_model/results_summary.json', 'w') as f:
        json.dump(results_summary, f, indent=2)

    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print(f"Results saved to results/lstm_model/")
    print(f"\nFinal Results:")
    print(f"  Train Accuracy: {results_summary['train_accuracy']:.4f}")
    print(f"  Val Accuracy: {results_summary['val_accuracy']:.4f}")
    print(f"  Test Accuracy: {results_summary['test_accuracy']:.4f}")
    print(f"  Epochs Trained: {results_summary['epochs_trained']}")


if __name__ == "__main__":
    main()
