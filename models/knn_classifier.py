"""
FIXED KNN Model for Exercise Classification
Now properly combines data from BOTH sensors (foot + shank)
"""

import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import json
from pathlib import Path


def combine_sensors(df_segmented):
    """
    Combine foot and shank sensor data for each repetition
    Each rep should have features from BOTH sensors

    Returns: DataFrame where each row has data from both sensors combined
    """
    print("\nCombining foot and shank sensor data...")

    # Sensors to combine
    sensor_signals = ['acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z', 'roll', 'pitch']

    # Get foot and shank data separately
    df_foot = df_segmented[df_segmented['sensor_location'] == 'foot'].copy()
    df_shank = df_segmented[df_segmented['sensor_location'] == 'shank'].copy()

    # Rename columns to distinguish sensors
    for signal in sensor_signals:
        df_foot.rename(columns={signal: f'{signal}_foot'}, inplace=True)
        df_shank.rename(columns={signal: f'{signal}_shank'}, inplace=True)

    # Merge on the grouping keys
    merge_keys = ['subject_id', 'exercise', 'set', 'rep']
    df_combined = df_foot.merge(
        df_shank[merge_keys + [f'{s}_shank' for s in sensor_signals]],
        on=merge_keys,
        how='inner'
    )

    print(f"Original segments: {len(df_segmented)}")
    print(f"Combined segments (foot+shank): {len(df_combined)}")
    print(f"Reduction factor: {len(df_segmented) / len(df_combined):.1f}x (should be ~2.0)")

    return df_combined


class FixedKNNExerciseClassifier:
    def __init__(self, n_neighbors=5, weights='distance', n_features=None):
        self.n_neighbors = n_neighbors
        self.weights = weights
        self.n_features = n_features
        self.knn = KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights)
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_selector = None
        self.best_params = None

    def extract_features_from_combined_segment(self, segment_data):
        """
        Extract features from BOTH sensors (foot and shank)
        This doubles the feature count compared to single sensor
        """
        features = []

        # Extract features from foot sensor (only raw signals, not roll/pitch)
        foot_signals = ['acc_x_foot', 'acc_y_foot', 'acc_z_foot',
                       'gyr_x_foot', 'gyr_y_foot', 'gyr_z_foot']

        for signal in foot_signals:
            if signal in segment_data and segment_data[signal] is not None:
                # Parse the array from string format
                if isinstance(segment_data[signal], str):
                    clean_str = segment_data[signal].strip('[]').replace('\n', ' ')
                    values = np.fromstring(clean_str, sep=' ')
                else:
                    values = np.array(segment_data[signal])

                # Statistical features
                features.extend([
                    np.mean(values),
                    np.std(values),
                    np.percentile(values, 25),
                    np.percentile(values, 75),
                ])

                # Gradient features
                if len(values) > 1:
                    gradient = np.gradient(values)
                    features.extend([
                        np.mean(gradient),
                        np.std(gradient),
                    ])
                else:
                    features.extend([0, 0])

        # Extract features from shank sensor (only raw signals, not roll/pitch)
        shank_signals = ['acc_x_shank', 'acc_y_shank', 'acc_z_shank',
                        'gyr_x_shank', 'gyr_y_shank', 'gyr_z_shank']

        for signal in shank_signals:
            if signal in segment_data and segment_data[signal] is not None:
                # Parse the array from string format
                if isinstance(segment_data[signal], str):
                    clean_str = segment_data[signal].strip('[]').replace('\n', ' ')
                    values = np.fromstring(clean_str, sep=' ')
                else:
                    values = np.array(segment_data[signal])

                # Statistical features
                features.extend([
                    np.mean(values),
                    np.std(values),
                    np.percentile(values, 25),
                    np.percentile(values, 75),
                ])

                # Gradient features
                if len(values) > 1:
                    gradient = np.gradient(values)
                    features.extend([
                        np.mean(gradient),
                        np.std(gradient),
                    ])
                else:
                    features.extend([0, 0])

        return np.array(features)

    def prepare_segmented_data(self, df):
        """Prepare features and labels from combined segmented data"""
        X = []
        y = []

        print(f"Processing {len(df)} combined segments...")
        for idx, row in df.iterrows():
            features = self.extract_features_from_combined_segment(row)
            X.append(features)
            y.append(row['exercise'])

        return np.array(X), np.array(y)

    def tune_hyperparameters(self, X_train, y_train, X_val, y_val):
        """Tune hyperparameters using grid search with cross-validation"""
        print("\n" + "="*60)
        print("Hyperparameter Tuning")
        print("="*60)

        # Encode labels
        y_train_encoded = self.label_encoder.fit_transform(y_train)
        y_val_encoded = self.label_encoder.transform(y_val)

        # Define parameter grid
        param_grid = {
            'n_neighbors': [3, 5, 7, 9, 11, 15, 21, 31],
            'weights': ['uniform', 'distance']
        }

        # Grid search with cross-validation
        grid_search = GridSearchCV(
            KNeighborsClassifier(),
            param_grid,
            cv=5,
            scoring='accuracy',
            n_jobs=-1,
            verbose=1
        )

        grid_search.fit(X_train, y_train_encoded)

        self.best_params = grid_search.best_params_
        print(f"\nBest parameters: {self.best_params}")
        print(f"Best CV score: {grid_search.best_score_:.4f}")

        # Update model with best parameters
        self.knn = grid_search.best_estimator_
        self.n_neighbors = self.best_params['n_neighbors']
        self.weights = self.best_params['weights']

        # Validate on validation set
        val_score = self.knn.score(X_val, y_val_encoded)
        print(f"Validation score: {val_score:.4f}")

        return grid_search

    def select_best_features(self, X_train, y_train, k='auto'):
        """Select k best features using mutual information"""
        print("\n" + "="*60)
        print("Feature Selection")
        print("="*60)

        # Encode labels
        y_train_encoded = self.label_encoder.transform(y_train)

        # If k is 'auto', use cross-validation to find best k
        if k == 'auto':
            k_values = [10, 15, 20, 24, 30, 40, 50, 60, 75, 96]
            k_values = [k for k in k_values if k <= X_train.shape[1]]
            best_score = 0
            best_k = k_values[0]

            for k_val in k_values:
                selector = SelectKBest(mutual_info_classif, k=k_val)
                X_selected = selector.fit_transform(X_train, y_train_encoded)
                score = cross_val_score(self.knn, X_selected, y_train_encoded, cv=5).mean()

                if score > best_score:
                    best_score = score
                    best_k = k_val

            print(f"Best k: {best_k} features (CV score: {best_score:.4f})")
            k = best_k

        # Select k best features
        self.feature_selector = SelectKBest(mutual_info_classif, k=k)
        self.feature_selector.fit(X_train, y_train_encoded)

        print(f"Selected {k} features out of {X_train.shape[1]}")

        return self.feature_selector

    def train(self, X_train, y_train, X_val, y_val, tune=True, select_features=True):
        """Train the KNN classifier with optional tuning and feature selection"""

        # Encode labels
        y_train_encoded = self.label_encoder.fit_transform(y_train)
        y_val_encoded = self.label_encoder.transform(y_val)

        # Standardize features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # Hyperparameter tuning
        if tune:
            self.tune_hyperparameters(X_train_scaled, y_train, X_val_scaled, y_val)

        # Feature selection
        if select_features:
            self.select_best_features(X_train_scaled, y_train, k='auto')
            X_train_scaled = self.feature_selector.transform(X_train_scaled)
            X_val_scaled = self.feature_selector.transform(X_val_scaled)

        # Train final model
        print("\n" + "="*60)
        print("Training Final Model")
        print("="*60)
        self.knn.fit(X_train_scaled, y_train_encoded)

        # Evaluate
        train_score = self.knn.score(X_train_scaled, y_train_encoded)
        val_score = self.knn.score(X_val_scaled, y_val_encoded)

        print(f"Training accuracy: {train_score:.4f}")
        print(f"Validation accuracy: {val_score:.4f}")

    def predict(self, X):
        """Make predictions"""
        X_scaled = self.scaler.transform(X)
        if self.feature_selector is not None:
            X_scaled = self.feature_selector.transform(X_scaled)
        y_pred_encoded = self.knn.predict(X_scaled)
        return self.label_encoder.inverse_transform(y_pred_encoded)

    def evaluate(self, X, y_true, dataset_name=""):
        """Evaluate model on a dataset"""
        y_pred = self.predict(X)
        accuracy = accuracy_score(y_true, y_pred)

        print(f"\n{dataset_name} Set Results:")
        print(f"Accuracy: {accuracy:.4f}")
        print("\nClassification Report:")
        print(classification_report(y_true, y_pred))

        return y_pred

    def plot_confusion_matrix(self, y_true, y_pred, title, save_path):
        """Plot and save confusion matrix"""
        cm = confusion_matrix(y_true, y_pred)

        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=self.label_encoder.classes_,
                   yticklabels=self.label_encoder.classes_)
        plt.title(title)
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()

        # Create directory if it doesn't exist
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Confusion matrix saved to {save_path}")

    def save_model(self, path):
        """Save the trained model"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(self, f)
        print(f"\nModel saved to {path}")

    @staticmethod
    def load_model(path):
        """Load a trained model"""
        with open(path, 'rb') as f:
            return pickle.load(f)


def prepare_unsegmented_test_data_combined(df_clean, test_subjects, classifier,
                                          window_size=100, overlap=50):
    """
    Prepare test data from unsegmented files
    Combines foot and shank sensors for each window
    """
    print("\nPreparing unsegmented test data with combined sensors...")

    # Filter for test subjects and target exercises
    target_exercises = ['Ankle Rotation', 'Calf Raises', 'Heel Walk']
    df_test = df_clean[
        (df_clean['subject_id'].isin(test_subjects)) &
        (df_clean['exercise'].isin(target_exercises))
    ]

    X_test = []
    y_test = []

    # Group by exercise file (without sensor_location to keep them together)
    file_groups = df_test.groupby(['subject_id', 'exercise', 'set'])

    for (subject_id, exercise, exercise_set), group in file_groups:
        # Get foot and shank data separately
        foot_data = group[group['sensor_location'] == 'foot']
        shank_data = group[group['sensor_location'] == 'shank']

        # Check if both sensors exist
        if len(foot_data) == 0 or len(shank_data) == 0:
            print(f"Warning: Missing sensor data for Subject {subject_id}, {exercise}, Set {exercise_set}")
            continue

        # Align the data (they should have the same length)
        min_length = min(len(foot_data), len(shank_data))
        foot_data = foot_data.iloc[:min_length]
        shank_data = shank_data.iloc[:min_length]

        # Sliding window approach
        step = window_size - overlap
        for i in range(0, len(foot_data) - window_size + 1, step):
            window_foot = foot_data.iloc[i:i + window_size]
            window_shank = shank_data.iloc[i:i + window_size]

            # Extract features from both sensors
            features = []

            # Foot sensor features
            for signal in ['acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z']:
                values = window_foot[signal].values
                features.extend([
                    np.mean(values),
                    np.std(values),
                    np.percentile(values, 25),
                    np.percentile(values, 75),
                ])
                if len(values) > 1:
                    gradient = np.gradient(values)
                    features.extend([np.mean(gradient), np.std(gradient)])
                else:
                    features.extend([0, 0])

            # Shank sensor features
            for signal in ['acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z']:
                values = window_shank[signal].values
                features.extend([
                    np.mean(values),
                    np.std(values),
                    np.percentile(values, 25),
                    np.percentile(values, 75),
                ])
                if len(values) > 1:
                    gradient = np.gradient(values)
                    features.extend([np.mean(gradient), np.std(gradient)])
                else:
                    features.extend([0, 0])

            X_test.append(features)
            y_test.append(exercise)

    return np.array(X_test), np.array(y_test)


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
    print("FIXED KNN Exercise Classifier - Training Pipeline")
    print("Now combines BOTH sensors (foot + shank)")
    print("="*60)

    # Load data
    print("\nLoading data...")
    df_segmented = pd.read_csv('results/segmented_signals.csv')
    df_clean = pd.read_csv('results/clean_signals.csv')

    # Filter for target exercises
    target_exercises = ['Ankle Rotation', 'Calf Raises', 'Heel Walk']
    df_segmented = df_segmented[df_segmented['exercise'].isin(target_exercises)]

    print(f"Loaded {len(df_segmented)} segmented samples (before combining sensors)")

    # CRITICAL FIX: Combine sensors BEFORE feature extraction
    df_combined = combine_sensors(df_segmented)

    # Create subject splits
    all_subjects = sorted(df_combined['subject_id'].unique())
    train_subjects, val_subjects, test_subjects = create_subject_splits(all_subjects)

    print(f"\nSubject splits:")
    print(f"Train ({len(train_subjects)}): {train_subjects}")
    print(f"Val ({len(val_subjects)}): {val_subjects}")
    print(f"Test ({len(test_subjects)}): {test_subjects}")

    # Prepare training data
    print("\n" + "="*60)
    print("Preparing Training Data (Combined Sensors)")
    print("="*60)
    df_train = df_combined[df_combined['subject_id'].isin(train_subjects)]
    classifier = FixedKNNExerciseClassifier()
    X_train, y_train = classifier.prepare_segmented_data(df_train)

    print(f"Training set: {X_train.shape}")
    print(f"Features per sample: {X_train.shape[1]} (doubled from single sensor)")
    print(f"Class distribution:\n{pd.Series(y_train).value_counts()}")

    # Prepare validation data
    print("\n" + "="*60)
    print("Preparing Validation Data (Combined Sensors)")
    print("="*60)
    df_val = df_combined[df_combined['subject_id'].isin(val_subjects)]
    X_val, y_val = classifier.prepare_segmented_data(df_val)

    print(f"Validation set: {X_val.shape}")
    print(f"Class distribution:\n{pd.Series(y_val).value_counts()}")

    # Train model with improvements
    print("\n" + "="*60)
    print("Training Fixed KNN Model")
    print("="*60)
    classifier.train(X_train, y_train, X_val, y_val, tune=True, select_features=True)

    # Evaluate on training set
    print("\n" + "="*60)
    print("Training Set Performance")
    print("="*60)
    y_train_pred = classifier.evaluate(X_train, y_train, "Training")
    classifier.plot_confusion_matrix(y_train, y_train_pred,
                                    "Training Set Confusion Matrix (Fixed)",
                                    "results/knn_model/confusion_matrix_train.png")

    # Evaluate on validation set
    y_val_pred = classifier.evaluate(X_val, y_val, "Validation")
    classifier.plot_confusion_matrix(y_val, y_val_pred,
                                    "Validation Set Confusion Matrix (Fixed)",
                                    "results/knn_model/confusion_matrix_val.png")

    # Prepare test data (unsegmented full files with combined sensors)
    print("\n" + "="*60)
    print("Preparing Test Data (Full Unsegmented Files with Combined Sensors)")
    print("="*60)
    X_test, y_test = prepare_unsegmented_test_data_combined(
        df_clean, test_subjects, classifier, window_size=100, overlap=50
    )

    print(f"Test set: {X_test.shape}")
    print(f"Class distribution:\n{pd.Series(y_test).value_counts()}")

    # Evaluate on test set
    y_test_pred = classifier.evaluate(X_test, y_test, "Test (Unsegmented)")
    classifier.plot_confusion_matrix(y_test, y_test_pred,
                                    "Test Set Confusion Matrix (Fixed)",
                                    "results/knn_model/confusion_matrix_test.png")

    # Save model
    classifier.save_model('results/knn_model/knn_classifier_fixed.pkl')

    # Save results summary
    results_summary = {
        'model_type': 'KNN with Combined Sensors (foot + shank)',
        'sensors_combined': True,
        'best_params': classifier.best_params,
        'n_features_selected': int(X_train.shape[1] if classifier.feature_selector is None
                                   else classifier.feature_selector.get_support().sum()),
        'total_features': int(X_train.shape[1]),
        'train_accuracy': float(accuracy_score(y_train, y_train_pred)),
        'val_accuracy': float(accuracy_score(y_val, y_val_pred)),
        'test_accuracy': float(accuracy_score(y_test, y_test_pred)),
        'train_samples': int(len(X_train)),
        'val_samples': int(len(X_val)),
        'test_samples': int(len(X_test)),
        'classes': classifier.label_encoder.classes_.tolist()
    }

    with open('results/knn_model/results_summary.json', 'w') as f:
        json.dump(results_summary, f, indent=2)

    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print(f"\nFinal Results (with BOTH sensors combined):")
    print(f"  Training Accuracy: {results_summary['train_accuracy']:.4f}")
    print(f"  Validation Accuracy: {results_summary['val_accuracy']:.4f}")
    print(f"  Test Accuracy: {results_summary['test_accuracy']:.4f}")
    print(f"\nModel saved to results/knn_model/")
