"""
LSTM Model trained on UNSEGMENTED data to match test distribution
This eliminates the train/test domain mismatch
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, regularizers
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import pickle
import json
import os

# Set random seeds
np.random.seed(42)
tf.random.set_seed(42)


def load_unsegmented_combined_data(df_clean, subject_ids, target_exercises):
    """
    Load unsegmented data with both sensors combined
    Each sample is a full exercise file (matches test distribution)
    """
    sequences = []
    labels = []

    # Filter data
    df_filtered = df_clean[
        (df_clean['subject_id'].isin(subject_ids)) &
        (df_clean['exercise'].isin(target_exercises))
    ]

    # Group by exercise file (without sensor_location to combine them)
    for (subject_id, exercise, exercise_set), group in df_filtered.groupby(
        ['subject_id', 'exercise', 'set']
    ):
        # Get foot and shank data
        foot_data = group[group['sensor_location'] == 'foot'].sort_values('time')
        shank_data = group[group['sensor_location'] == 'shank'].sort_values('time')

        # Skip if either sensor is missing
        if len(foot_data) == 0 or len(shank_data) == 0:
            continue

        # Align data
        min_length = min(len(foot_data), len(shank_data))
        foot_data = foot_data.iloc[:min_length]
        shank_data = shank_data.iloc[:min_length]

        # Skip if too short
        if min_length < 100:
            continue

        # Extract and combine sensor data
        foot_signals = foot_data[['acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z']].values
        shank_signals = shank_data[['acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z']].values

        # Combine: 12 features (6 from foot + 6 from shank)
        combined_sequence = np.column_stack([foot_signals, shank_signals])

        sequences.append(combined_sequence)
        labels.append(exercise)

    return sequences, labels


def pad_sequences_custom(sequences, max_length=None):
    """Pad sequences to the same length"""
    if max_length is None:
        max_length = max(len(seq) for seq in sequences)

    num_features = sequences[0].shape[1]
    padded = np.zeros((len(sequences), max_length, num_features))

    for i, seq in enumerate(sequences):
        length = min(len(seq), max_length)
        padded[i, :length] = seq[:length]

    return padded, max_length


class ImprovedLSTMClassifier:
    def __init__(self, input_shape, num_classes, lstm_units=[32],
                 dropout_rate=0.5, l2_reg=0.01):
        """
        LSTM trained on unsegmented data (matches test distribution)
        """
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.l2_reg = l2_reg
        self.model = None

    def build_model(self):
        """Build LSTM with moderate regularization"""
        model = keras.Sequential([
            layers.Input(shape=self.input_shape),

            # Bidirectional LSTM
            layers.Bidirectional(layers.LSTM(
                self.lstm_units[0],
                dropout=self.dropout_rate,
                recurrent_dropout=self.dropout_rate,
                kernel_regularizer=regularizers.l2(self.l2_reg),
                recurrent_regularizer=regularizers.l2(self.l2_reg)
            )),

            layers.BatchNormalization(),
            layers.Dropout(self.dropout_rate),

            # Dense layer
            layers.Dense(32, activation='relu',
                        kernel_regularizer=regularizers.l2(self.l2_reg)),
            layers.Dropout(self.dropout_rate),

            # Output
            layers.Dense(self.num_classes, activation='softmax')
        ])

        self.model = model
        return model

    def compile_model(self, learning_rate=0.0001):
        """Compile model"""
        optimizer = keras.optimizers.Adam(learning_rate=learning_rate, clipnorm=1.0)

        self.model.compile(
            optimizer=optimizer,
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )

        return self.model


def create_subject_splits(all_subjects, train_ratio=0.8, val_ratio=0.1):
    """Create train/val/test splits"""
    n_subjects = len(all_subjects)
    n_train = int(n_subjects * train_ratio)
    n_val = int(n_subjects * val_ratio)

    np.random.seed(42)
    shuffled = np.random.permutation(all_subjects)

    train_subjects = sorted(shuffled[:n_train].tolist())
    val_subjects = sorted(shuffled[n_train:n_train + n_val].tolist())
    test_subjects = sorted(shuffled[n_train + n_val:].tolist())

    return train_subjects, val_subjects, test_subjects


# ==============================================================================
# Main Training Pipeline
# ==============================================================================

if __name__ == "__main__":
    print("="*60)
    print("LSTM Classifier - UNSEGMENTED TRAINING")
    print("Trained on full exercise files (matches test distribution)")
    print("Combined sensors: foot + shank (12 features)")
    print("="*60)

    # Load data
    print("\nLoading unsegmented data...")
    df_clean = pd.read_csv('results/clean_signals.csv')

    target_exercises = ['Ankle Rotation', 'Calf Raises', 'Heel Walk']

    # Get all subjects
    all_subjects = sorted(df_clean['subject_id'].unique())

    # Create splits
    train_subjects, val_subjects, test_subjects = create_subject_splits(all_subjects)

    print(f"\nSubject splits:")
    print(f"Train ({len(train_subjects)}): {train_subjects}")
    print(f"Val ({len(val_subjects)}): {val_subjects}")
    print(f"Test ({len(test_subjects)}): {test_subjects}")

    # Load training data
    print("\n" + "="*60)
    print("Loading Training Data (Unsegmented)")
    print("="*60)
    train_sequences, train_labels = load_unsegmented_combined_data(
        df_clean, train_subjects, target_exercises
    )
    print(f"Loaded {len(train_sequences)} training sequences")
    print(f"Features per timestep: {train_sequences[0].shape[1]} (12: 6 foot + 6 shank)")

    # Load validation data
    print("\nLoading Validation Data (Unsegmented)...")
    val_sequences, val_labels = load_unsegmented_combined_data(
        df_clean, val_subjects, target_exercises
    )
    print(f"Loaded {len(val_sequences)} validation sequences")

    # Load test data
    print("\nLoading Test Data (Unsegmented)...")
    test_sequences, test_labels = load_unsegmented_combined_data(
        df_clean, test_subjects, target_exercises
    )
    print(f"Loaded {len(test_sequences)} test sequences")

    # Encode labels
    label_encoder = LabelEncoder()
    label_encoder.fit(train_labels)

    y_train = label_encoder.transform(train_labels)
    y_val = label_encoder.transform(val_labels)
    y_test = label_encoder.transform(test_labels)

    print(f"\nExercise classes: {label_encoder.classes_}")
    print(f"\nClass distribution (train):")
    for cls in label_encoder.classes_:
        count = sum(1 for l in train_labels if l == cls)
        print(f"  {cls}: {count}")

    # Pad sequences
    print("\nPadding sequences...")
    X_train, max_length = pad_sequences_custom(train_sequences)
    X_val, _ = pad_sequences_custom(val_sequences, max_length=max_length)
    X_test, _ = pad_sequences_custom(test_sequences, max_length=max_length)

    print(f"Sequence shape: {X_train.shape}")
    print(f"Max sequence length: {max_length}")

    # Normalize features
    print("\nNormalizing features...")
    train_mean = np.mean(X_train, axis=(0, 1), keepdims=True)
    train_std = np.std(X_train, axis=(0, 1), keepdims=True) + 1e-7

    X_train = (X_train - train_mean) / train_std
    X_val = (X_val - train_mean) / train_std
    X_test = (X_test - train_mean) / train_std

    # Build model
    print("\n" + "="*60)
    print("Building LSTM Model")
    print("="*60)

    input_shape = (max_length, 12)
    num_classes = len(label_encoder.classes_)

    classifier = ImprovedLSTMClassifier(
        input_shape=input_shape,
        num_classes=num_classes,
        lstm_units=[32],
        dropout_rate=0.5,
        l2_reg=0.01
    )

    model = classifier.build_model()
    model.summary()

    # Compile
    model = classifier.compile_model()

    # Create output directory
    os.makedirs('results/lstm_model', exist_ok=True)

    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
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
            'results/lstm_model/best_model_unsegmented.h5',
            monitor='val_accuracy',
            save_best_only=True,
            verbose=1
        )
    ]

    # Train
    print("\n" + "="*60)
    print("Training Model")
    print("="*60)

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=100,
        batch_size=8,  # Smaller batch size since sequences are longer
        callbacks=callbacks,
        verbose=1
    )

    # Plot training history
    plt.figure(figsize=(12, 4))

    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'], label='Train')
    plt.plot(history.history['val_accuracy'], label='Val')
    plt.title('Model Accuracy (Unsegmented Training)')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'], label='Train')
    plt.plot(history.history['val_loss'], label='Val')
    plt.title('Model Loss (Unsegmented Training)')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/lstm_model/training_history_unsegmented.png', dpi=300, bbox_inches='tight')
    print("Saved training history")

    # Evaluate
    print("\n" + "="*60)
    print("Evaluation Results")
    print("="*60)

    # Training set
    train_loss, train_acc = model.evaluate(X_train, y_train, verbose=0)
    print(f"\nTraining Set:")
    print(f"  Accuracy: {train_acc:.4f}")
    print(f"  Loss: {train_loss:.4f}")

    # Validation set
    val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
    print(f"\nValidation Set:")
    print(f"  Accuracy: {val_acc:.4f}")
    print(f"  Loss: {val_loss:.4f}")

    # Test set
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"\nTest Set:")
    print(f"  Accuracy: {test_acc:.4f}")
    print(f"  Loss: {test_loss:.4f}")

    # Detailed test results
    from sklearn.metrics import classification_report, confusion_matrix
    import seaborn as sns

    test_pred = model.predict(X_test, verbose=0)
    test_pred_labels = np.argmax(test_pred, axis=1)

    print(f"\n{'='*60}")
    print("Test Set - Classification Report")
    print(f"{'='*60}")
    print(classification_report(
        y_test,
        test_pred_labels,
        target_names=label_encoder.classes_
    ))

    # Confusion matrix
    cm = confusion_matrix(y_test, test_pred_labels)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=label_encoder.classes_,
                yticklabels=label_encoder.classes_)
    plt.title('Test Set - Confusion Matrix (Unsegmented Training)')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig('results/lstm_model/confusion_matrix_unsegmented.png', dpi=300, bbox_inches='tight')
    print("Saved confusion matrix")

    # Save results
    results_summary = {
        'model_type': 'LSTM trained on unsegmented data with combined sensors',
        'training_data': 'unsegmented (full exercise files)',
        'sensors_combined': True,
        'model_architecture': {
            'lstm_units': [32],
            'dropout_rate': 0.5,
            'l2_regularization': 0.01,
            'max_sequence_length': int(max_length),
            'num_features': 12
        },
        'train_accuracy': float(train_acc),
        'val_accuracy': float(val_acc),
        'test_accuracy': float(test_acc),
        'train_samples': int(len(train_sequences)),
        'val_samples': int(len(val_sequences)),
        'test_samples': int(len(test_sequences)),
        'classes': label_encoder.classes_.tolist(),
        'epochs_trained': len(history.history['loss'])
    }

    with open('results/lstm_model/results_summary_unsegmented.json', 'w') as f:
        json.dump(results_summary, f, indent=2)

    # Save model
    model.save('results/lstm_model/lstm_model_unsegmented.h5')
    with open('results/lstm_model/label_encoder_unsegmented.pkl', 'wb') as f:
        pickle.dump(label_encoder, f)

    # Save normalization params
    np.save('results/lstm_model/train_mean_unsegmented.npy', train_mean)
    np.save('results/lstm_model/train_std_unsegmented.npy', train_std)

    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print(f"\nFinal Results (Unsegmented Training):")
    print(f"  Training Accuracy: {train_acc:.4f}")
    print(f"  Validation Accuracy: {val_acc:.4f}")
    print(f"  Test Accuracy: {test_acc:.4f}")
    print(f"  Overfitting Gap: {(train_acc - test_acc)*100:.2f}%")
    print(f"\nModel saved to results/lstm_model/")
