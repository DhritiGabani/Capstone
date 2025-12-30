"""
FIXED CNN-BiLSTM Model for Exercise Classification and Repetition Counting
Now properly combines data from BOTH sensors (foot + shank)
Multi-task learning:
  1. Exercise classification (Ankle Rotation, Calf Raises, Heel Walk)
  2. Repetition counting (predict number of reps in the sequence)
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models, regularizers
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import json
import os
from scipy.signal import find_peaks
from collections import Counter

# Set random seeds
np.random.seed(42)
tf.random.set_seed(42)

class CNNBiLSTMRepCounter:
    def __init__(self, input_shape, num_classes,
                 cnn_filters=[64, 128], kernel_size=5,
                 lstm_units=64, dropout_rate=0.3, l2_reg=0.001):
        """
        CNN-BiLSTM architecture for exercise classification and rep counting

        Args:
            input_shape: (sequence_length, num_features)
            num_classes: Number of exercise classes
            cnn_filters: List of filter sizes for CNN layers
            kernel_size: Kernel size for 1D convolutions
            lstm_units: Number of LSTM units
            dropout_rate: Dropout rate for regularization
            l2_reg: L2 regularization factor
        """
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.cnn_filters = cnn_filters
        self.kernel_size = kernel_size
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.l2_reg = l2_reg
        self.model = None

    def build_model(self):
        """Build CNN-BiLSTM model with dual outputs"""

        # Input layer
        inputs = layers.Input(shape=self.input_shape, name='input')

        # CNN layers for feature extraction
        x = inputs
        for i, filters in enumerate(self.cnn_filters):
            x = layers.Conv1D(
                filters=filters,
                kernel_size=self.kernel_size,
                padding='same',
                activation='relu',
                kernel_regularizer=regularizers.l2(self.l2_reg),
                name=f'conv1d_{i+1}'
            )(x)
            x = layers.BatchNormalization(name=f'bn_conv_{i+1}')(x)
            x = layers.MaxPooling1D(pool_size=2, name=f'maxpool_{i+1}')(x)
            x = layers.Dropout(self.dropout_rate, name=f'dropout_conv_{i+1}')(x)

        # BiLSTM layers for temporal modeling
        x = layers.Bidirectional(
            layers.LSTM(
                self.lstm_units,
                return_sequences=True,
                dropout=self.dropout_rate,
                recurrent_dropout=self.dropout_rate,
                kernel_regularizer=regularizers.l2(self.l2_reg),
                recurrent_regularizer=regularizers.l2(self.l2_reg)
            ),
            name='bilstm_1'
        )(x)
        x = layers.BatchNormalization(name='bn_lstm_1')(x)

        # Second BiLSTM layer (returns sequences for better temporal understanding)
        x = layers.Bidirectional(
            layers.LSTM(
                self.lstm_units // 2,
                return_sequences=False,
                dropout=self.dropout_rate,
                recurrent_dropout=self.dropout_rate,
                kernel_regularizer=regularizers.l2(self.l2_reg),
                recurrent_regularizer=regularizers.l2(self.l2_reg)
            ),
            name='bilstm_2'
        )(x)
        x = layers.BatchNormalization(name='bn_lstm_2')(x)

        # Shared dense layer
        shared = layers.Dense(
            128,
            activation='relu',
            kernel_regularizer=regularizers.l2(self.l2_reg),
            name='shared_dense'
        )(x)
        shared = layers.Dropout(self.dropout_rate, name='dropout_shared')(shared)

        # Output 1: Exercise Classification
        classification = layers.Dense(
            64,
            activation='relu',
            kernel_regularizer=regularizers.l2(self.l2_reg),
            name='classification_dense'
        )(shared)
        classification = layers.Dropout(self.dropout_rate, name='dropout_classification')(classification)
        classification_output = layers.Dense(
            self.num_classes,
            activation='softmax',
            name='exercise_classification'
        )(classification)

        # Output 2: Repetition Counting (regression)
        counting = layers.Dense(
            64,
            activation='relu',
            kernel_regularizer=regularizers.l2(self.l2_reg),
            name='counting_dense'
        )(shared)
        counting = layers.Dropout(self.dropout_rate, name='dropout_counting')(counting)
        counting_output = layers.Dense(
            1,
            activation='linear',  # Linear activation for regression
            name='repetition_count'
        )(counting)

        # Build model
        self.model = models.Model(
            inputs=inputs,
            outputs=[classification_output, counting_output],
            name='CNN_BiLSTM_RepCounter'
        )

        return self.model

    def compile_model(self, learning_rate=0.0001,
                     classification_weight=1.0,
                     counting_weight=0.01):
        """Compile model with multi-task loss"""

        optimizer = keras.optimizers.Adam(
            learning_rate=learning_rate,
            clipnorm=1.0  # Gradient clipping to prevent explosion
        )

        self.model.compile(
            optimizer=optimizer,
            loss={
                'exercise_classification': 'sparse_categorical_crossentropy',
                'repetition_count': 'mae'  # Use MAE instead of MSE to avoid large gradients
            },
            loss_weights={
                'exercise_classification': classification_weight,
                'repetition_count': counting_weight
            },
            metrics={
                'exercise_classification': ['accuracy'],
                'repetition_count': ['mae', 'mse']  # Mean absolute error
            }
        )

        return self.model

def load_and_prepare_data(data_path, metadata_path=None):
    """
    Load unsegmented data and prepare for training
    Each file should contain 10 reps according to protocol
    Only includes: Ankle Rotation, Calf Raises, Heel Walk
    """
    print("Loading data...")
    df = pd.read_csv(data_path)

    # Filter to only include the 3 target exercises
    target_exercises = ['Ankle Rotation', 'Calf Raises', 'Heel Walk']
    df = df[df['exercise'].isin(target_exercises)]
    print(f"Filtered to target exercises: {target_exercises}")

    # FIXED: Group by file WITHOUT sensor_location to combine sensors
    file_groups = df.groupby(['subject_id', 'exercise', 'set'])

    sequences = []
    labels = []
    rep_counts = []
    subject_ids = []
    exercise_names = []

    for (subject_id, exercise, exercise_set), group in file_groups:
        # Get foot and shank data separately
        foot_data = group[group['sensor_location'] == 'foot'].sort_values('time')
        shank_data = group[group['sensor_location'] == 'shank'].sort_values('time')

        # Skip if either sensor is missing
        if len(foot_data) == 0 or len(shank_data) == 0:
            continue

        # Align data to same length
        min_length = min(len(foot_data), len(shank_data))
        foot_data = foot_data.iloc[:min_length]
        shank_data = shank_data.iloc[:min_length]

        # Skip if too short
        if min_length < 100:
            continue

        # Extract sensor data from both sensors and combine
        foot_signals = foot_data[['acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z']].values
        shank_signals = shank_data[['acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z']].values

        # Combine: [foot features, shank features] = 12 features total
        combined_data = np.column_stack([foot_signals, shank_signals])

        sequences.append(combined_data)
        labels.append(exercise)
        rep_counts.append(10)  # According to protocol, each file has 10 reps
        subject_ids.append(subject_id)
        exercise_names.append(exercise)

    print(f"Loaded {len(sequences)} exercise sequences")
    print(f"Unique exercises: {set(exercise_names)}")

    # Check for NaN values in sequences
    nan_count = sum(1 for seq in sequences if np.isnan(seq).any())
    if nan_count > 0:
        print(f"WARNING: {nan_count} sequences contain NaN values")
        # Remove sequences with NaN
        valid_indices = [i for i, seq in enumerate(sequences) if not np.isnan(seq).any()]
        sequences = [sequences[i] for i in valid_indices]
        labels = [labels[i] for i in valid_indices]
        rep_counts = [rep_counts[i] for i in valid_indices]
        subject_ids = [subject_ids[i] for i in valid_indices]
        exercise_names = [exercise_names[i] for i in valid_indices]
        print(f"Removed {nan_count} sequences with NaN. Remaining: {len(sequences)}")

    return sequences, labels, rep_counts, subject_ids

def pad_sequences_custom(sequences, max_length=None, padding='post'):
    """Pad sequences to same length"""
    if max_length is None:
        max_length = max(len(seq) for seq in sequences)

    padded = np.zeros((len(sequences), max_length, sequences[0].shape[1]))

    for i, seq in enumerate(sequences):
        length = min(len(seq), max_length)
        if padding == 'post':
            padded[i, :length] = seq[:length]
        else:  # pre
            padded[i, -length:] = seq[:length]

    return padded, max_length

def create_subject_splits(subject_ids, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1):
    """Create train/val/test splits based on subjects (80/10/10)"""
    unique_subjects = sorted(set(subject_ids))
    n_subjects = len(unique_subjects)

    n_train = int(n_subjects * train_ratio)
    n_val = int(n_subjects * val_ratio)

    # Shuffle subjects
    np.random.shuffle(unique_subjects)

    train_subjects = unique_subjects[:n_train]
    val_subjects = unique_subjects[n_train:n_train + n_val]
    test_subjects = unique_subjects[n_train + n_val:]

    print(f"\nSubject splits:")
    print(f"Train ({len(train_subjects)}): {sorted(train_subjects)}")
    print(f"Val ({len(val_subjects)}): {sorted(val_subjects)}")
    print(f"Test ({len(test_subjects)}): {sorted(test_subjects)}")

    return train_subjects, val_subjects, test_subjects

# ==============================================================================
# Main Training Pipeline
# ==============================================================================

if __name__ == "__main__":

    print("="*60)
    print("CNN-BiLSTM Exercise Classifier and Rep Counter")
    print("="*60)

    # Load data
    data_path = 'results/clean_signals.csv'
    sequences, labels, rep_counts, subject_ids = load_and_prepare_data(data_path)

    # Create subject splits
    train_subjects, val_subjects, test_subjects = create_subject_splits(
        subject_ids, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1
    )

    # Split data by subjects
    train_idx = [i for i, sid in enumerate(subject_ids) if sid in train_subjects]
    val_idx = [i for i, sid in enumerate(subject_ids) if sid in val_subjects]
    test_idx = [i for i, sid in enumerate(subject_ids) if sid in test_subjects]

    train_sequences = [sequences[i] for i in train_idx]
    val_sequences = [sequences[i] for i in val_idx]
    test_sequences = [sequences[i] for i in test_idx]

    train_labels = [labels[i] for i in train_idx]
    val_labels = [labels[i] for i in val_idx]
    test_labels = [labels[i] for i in test_idx]

    train_reps = [rep_counts[i] for i in train_idx]
    val_reps = [rep_counts[i] for i in val_idx]
    test_reps = [rep_counts[i] for i in test_idx]

    print(f"\nDataset sizes:")
    print(f"Train: {len(train_sequences)} sequences")
    print(f"Val: {len(val_sequences)} sequences")
    print(f"Test: {len(test_sequences)} sequences")

    # Encode labels
    label_encoder = LabelEncoder()
    label_encoder.fit(train_labels)

    train_labels_encoded = label_encoder.transform(train_labels)
    val_labels_encoded = label_encoder.transform(val_labels)
    test_labels_encoded = label_encoder.transform(test_labels)

    print(f"\nExercise classes: {label_encoder.classes_}")

    # Normalize sequences BEFORE padding
    print("\nNormalizing input features...")
    # Calculate mean and std from all training data points
    all_train_data = np.vstack([seq for seq in train_sequences])
    train_mean = np.mean(all_train_data, axis=0, keepdims=True)
    train_std = np.std(all_train_data, axis=0, keepdims=True) + 1e-7

    print(f"Feature means: {train_mean.flatten()}")
    print(f"Feature stds: {train_std.flatten()}")

    # Normalize each sequence
    train_sequences_norm = [(seq - train_mean) / train_std for seq in train_sequences]
    val_sequences_norm = [(seq - train_mean) / train_std for seq in val_sequences]
    test_sequences_norm = [(seq - train_mean) / train_std for seq in test_sequences]

    # Now pad the normalized sequences
    print("\nPadding sequences...")
    X_train, max_length = pad_sequences_custom(train_sequences_norm)
    X_val, _ = pad_sequences_custom(val_sequences_norm, max_length=max_length)
    X_test, _ = pad_sequences_custom(test_sequences_norm, max_length=max_length)

    print(f"Sequence shape: {X_train.shape}")
    print(f"Max sequence length: {max_length}")

    # Convert to numpy arrays
    y_train_class = np.array(train_labels_encoded)
    y_val_class = np.array(val_labels_encoded)
    y_test_class = np.array(test_labels_encoded)

    # Normalize repetition counts (scale to 0-1 range)
    # Max expected reps is 15 (some headroom above the typical 10)
    MAX_REPS = 15.0
    y_train_count = np.array(train_reps, dtype=np.float32) / MAX_REPS
    y_val_count = np.array(val_reps, dtype=np.float32) / MAX_REPS
    y_test_count = np.array(test_reps, dtype=np.float32) / MAX_REPS

    print(f"\nRep count normalization:")
    print(f"  Original range: [{min(train_reps)}, {max(train_reps)}]")
    print(f"  Normalized range: [{np.min(y_train_count):.4f}, {np.max(y_train_count):.4f}]")

    print(f"\nClass distribution (train):")
    print(pd.Series(train_labels).value_counts())

    # Build model
    print("\n" + "="*60)
    print("Building CNN-BiLSTM Model")
    print("="*60)

    input_shape = (max_length, 12)  # 12 features: 6 from foot + 6 from shank
    num_classes = len(label_encoder.classes_)

    classifier = CNNBiLSTMRepCounter(
        input_shape=input_shape,
        num_classes=num_classes,
        cnn_filters=[64, 128],
        kernel_size=5,
        lstm_units=64,
        dropout_rate=0.3,
        l2_reg=0.001
    )

    model = classifier.build_model()
    model.summary()

    # Compile model (using defaults: lr=0.0001, counting_weight=0.01, gradient clipping=1.0)
    model = classifier.compile_model()

    # Create output directory
    os.makedirs('results/cnn_bilstm_model', exist_ok=True)

    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_exercise_classification_accuracy',
            patience=15,
            restore_best_weights=True,
            verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1
        ),
        keras.callbacks.ModelCheckpoint(
            'results/cnn_bilstm_model/best_model.h5',
            monitor='val_exercise_classification_accuracy',
            save_best_only=True,
            verbose=1
        )
    ]

    # Train model
    print("\n" + "="*60)
    print("Training Model")
    print("="*60)

    history = model.fit(
        X_train,
        {
            'exercise_classification': y_train_class,
            'repetition_count': y_train_count
        },
        validation_data=(
            X_val,
            {
                'exercise_classification': y_val_class,
                'repetition_count': y_val_count
            }
        ),
        epochs=100,
        batch_size=16,
        callbacks=callbacks,
        verbose=1
    )

    # Save training history
    plt.figure(figsize=(15, 10))

    # Classification accuracy
    plt.subplot(2, 3, 1)
    plt.plot(history.history['exercise_classification_accuracy'], label='Train')
    plt.plot(history.history['val_exercise_classification_accuracy'], label='Val')
    plt.title('Classification Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Classification loss
    plt.subplot(2, 3, 2)
    plt.plot(history.history['exercise_classification_loss'], label='Train')
    plt.plot(history.history['val_exercise_classification_loss'], label='Val')
    plt.title('Classification Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Counting MAE
    plt.subplot(2, 3, 3)
    plt.plot(history.history['repetition_count_mae'], label='Train')
    plt.plot(history.history['val_repetition_count_mae'], label='Val')
    plt.title('Repetition Count MAE')
    plt.xlabel('Epoch')
    plt.ylabel('MAE')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Counting loss
    plt.subplot(2, 3, 4)
    plt.plot(history.history['repetition_count_loss'], label='Train')
    plt.plot(history.history['val_repetition_count_loss'], label='Val')
    plt.title('Repetition Count Loss (MSE)')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Total loss
    plt.subplot(2, 3, 5)
    plt.plot(history.history['loss'], label='Train')
    plt.plot(history.history['val_loss'], label='Val')
    plt.title('Total Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/cnn_bilstm_model/training_history.png', dpi=300, bbox_inches='tight')
    print("Saved training history to results/cnn_bilstm_model/training_history.png")

    # Evaluate on all sets
    print("\n" + "="*60)
    print("Evaluation Results")
    print("="*60)

    # Training set
    train_pred_class, train_pred_count = model.predict(X_train, verbose=0)
    train_pred_labels = np.argmax(train_pred_class, axis=1)
    train_class_acc = np.mean(train_pred_labels == y_train_class)
    # Denormalize predictions for MAE calculation
    train_count_mae = np.mean(np.abs(train_pred_count.flatten() * MAX_REPS - y_train_count * MAX_REPS))

    print(f"\nTraining Set:")
    print(f"  Classification Accuracy: {train_class_acc:.4f}")
    print(f"  Rep Count MAE: {train_count_mae:.4f} reps")

    # Validation set
    val_pred_class, val_pred_count = model.predict(X_val, verbose=0)
    val_pred_labels = np.argmax(val_pred_class, axis=1)
    val_class_acc = np.mean(val_pred_labels == y_val_class)
    # Denormalize predictions for MAE calculation
    val_count_mae = np.mean(np.abs(val_pred_count.flatten() * MAX_REPS - y_val_count * MAX_REPS))

    print(f"\nValidation Set:")
    print(f"  Classification Accuracy: {val_class_acc:.4f}")
    print(f"  Rep Count MAE: {val_count_mae:.4f} reps")

    # Test set
    test_pred_class, test_pred_count = model.predict(X_test, verbose=0)
    test_pred_labels = np.argmax(test_pred_class, axis=1)
    test_class_acc = np.mean(test_pred_labels == y_test_class)
    # Denormalize predictions for MAE calculation
    test_count_mae = np.mean(np.abs(test_pred_count.flatten() * MAX_REPS - y_test_count * MAX_REPS))

    print(f"\nTest Set:")
    print(f"  Classification Accuracy: {test_class_acc:.4f}")
    print(f"  Rep Count MAE: {test_count_mae:.4f} reps")

    # Detailed test results
    from sklearn.metrics import classification_report, confusion_matrix

    print(f"\n{'='*60}")
    print("Test Set - Classification Report")
    print(f"{'='*60}")
    print(classification_report(
        y_test_class,
        test_pred_labels,
        target_names=label_encoder.classes_
    ))

    # Confusion matrix
    cm = confusion_matrix(y_test_class, test_pred_labels)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=label_encoder.classes_,
                yticklabels=label_encoder.classes_)
    plt.title('Test Set - Confusion Matrix (Exercise Classification)')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig('results/cnn_bilstm_model/confusion_matrix_test.png', dpi=300, bbox_inches='tight')
    print("\nSaved confusion matrix to results/cnn_bilstm_model/confusion_matrix_test.png")

    # Rep counting error analysis
    print(f"\n{'='*60}")
    print("Test Set - Repetition Counting Analysis")
    print(f"{'='*60}")

    # Denormalize for error analysis
    test_count_errors = (test_pred_count.flatten() * MAX_REPS) - (y_test_count * MAX_REPS)
    print(f"\nRep Count Statistics:")
    print(f"  Mean Error: {np.mean(test_count_errors):.4f} reps")
    print(f"  Mean Absolute Error: {test_count_mae:.4f} reps")
    print(f"  Std Error: {np.std(test_count_errors):.4f} reps")
    print(f"  Min Error: {np.min(test_count_errors):.4f} reps")
    print(f"  Max Error: {np.max(test_count_errors):.4f} reps")

    # Plot rep count predictions (denormalized)
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.scatter(y_test_count * MAX_REPS, test_pred_count.flatten() * MAX_REPS, alpha=0.5)
    plt.plot([0, 12], [0, 12], 'r--', label='Perfect prediction')
    plt.xlabel('True Rep Count')
    plt.ylabel('Predicted Rep Count')
    plt.title('Repetition Count: Predicted vs True')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.hist(test_count_errors, bins=20, edgecolor='black')
    plt.xlabel('Prediction Error (reps)')
    plt.ylabel('Frequency')
    plt.title('Distribution of Rep Count Errors')
    plt.axvline(x=0, color='r', linestyle='--', label='Zero error')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/cnn_bilstm_model/rep_count_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved rep count analysis to results/cnn_bilstm_model/rep_count_analysis.png")

    # Save results
    results_summary = {
        'model_architecture': {
            'cnn_filters': [64, 128],
            'kernel_size': 5,
            'lstm_units': 64,
            'dropout_rate': 0.3,
            'l2_regularization': 0.001,
            'max_sequence_length': int(max_length),
            'num_features': 6,
            'num_classes': int(num_classes)
        },
        'normalization': {
            'feature_mean': train_mean.flatten().tolist(),
            'feature_std': train_std.flatten().tolist(),
            'max_reps': float(MAX_REPS)
        },
        'training': {
            'train_samples': int(len(train_sequences)),
            'val_samples': int(len(val_sequences)),
            'test_samples': int(len(test_sequences)),
            'epochs_trained': len(history.history['loss']),
            'learning_rate': 0.0001,
            'gradient_clipping': 1.0
        },
        'classification_results': {
            'train_accuracy': float(train_class_acc),
            'val_accuracy': float(val_class_acc),
            'test_accuracy': float(test_class_acc)
        },
        'counting_results': {
            'train_mae': float(train_count_mae),
            'val_mae': float(val_count_mae),
            'test_mae': float(test_count_mae),
            'test_mean_error': float(np.mean(test_count_errors)),
            'test_std_error': float(np.std(test_count_errors))
        },
        'classes': label_encoder.classes_.tolist()
    }

    with open('results/cnn_bilstm_model/results_summary.json', 'w') as f:
        json.dump(results_summary, f, indent=2)

    # Save model and encoder
    model.save('results/cnn_bilstm_model/cnn_bilstm_model.h5')
    with open('results/cnn_bilstm_model/label_encoder.pkl', 'wb') as f:
        pickle.dump(label_encoder, f)

    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print("\nFinal Results:")
    print(f"  Test Classification Accuracy: {test_class_acc:.4f}")
    print(f"  Test Rep Count MAE: {test_count_mae:.4f} reps")
    print(f"\nModel saved to results/cnn_bilstm_model/")
