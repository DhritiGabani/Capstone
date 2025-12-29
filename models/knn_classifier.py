"""
Improved KNN Model for Exercise Classification
Addresses overfitting with:
- Hyperparameter tuning via cross-validation
- Distance weighting
- Feature selection
- Regularization
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


class ImprovedKNNExerciseClassifier:
    def __init__(self, n_neighbors=5, weights='distance', n_features=None):
        self.n_neighbors = n_neighbors
        self.weights = weights
        self.n_features = n_features
        self.knn = KNeighborsClassifier(
            n_neighbors=n_neighbors, weights=weights)
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_selector = None
        self.best_params = None

    def extract_features_from_segment(self, segment_data):
        """
        Extract statistical features from a time-series segment
        Reduced feature set to avoid overfitting
        """
        features = []

        # Sensor signals to extract features from
        signals = ['acc_x', 'acc_y', 'acc_z', 'gyr_x',
                   'gyr_y', 'gyr_z', 'roll', 'pitch']

        for signal in signals:
            if signal in segment_data and segment_data[signal] is not None:
                # Parse the array from string format
                if isinstance(segment_data[signal], str):
                    clean_str = segment_data[signal].strip(
                        '[]').replace('\n', ' ')
                    values = np.fromstring(clean_str, sep=' ')
                else:
                    values = np.array(segment_data[signal])

                # Reduced statistical features (avoiding redundancy)
                features.extend([
                    np.mean(values),           # Mean
                    np.std(values),            # Standard deviation
                    np.percentile(values, 25),  # 25th percentile
                    np.percentile(values, 75),  # 75th percentile
                ])

                # Add gradient features
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
        """Prepare features and labels from segmented data"""
        X = []
        y = []

        print(f"Processing {len(df)} segments...")
        for idx, row in df.iterrows():
            features = self.extract_features_from_segment(row)
            X.append(features)
            y.append(row['exercise'])

        return np.array(X), np.array(y)

    def tune_hyperparameters(self, X_train, y_train, X_val, y_val):
        """
        Tune hyperparameters using grid search with cross-validation
        """
        print("\n" + "="*60)
        print("Hyperparameter Tuning")
        print("="*60)

        # Encode labels
        y_train_encoded = self.label_encoder.fit_transform(y_train)
        y_val_encoded = self.label_encoder.transform(y_val)

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # Parameter grid
        param_grid = {
            'n_neighbors': [3, 5, 7, 9, 11, 15, 21],
            'weights': ['uniform', 'distance'],
            'metric': ['euclidean', 'manhattan', 'minkowski']
        }

        print(
            f"Testing {np.prod([len(v) for v in param_grid.values()])} parameter combinations...")

        # Grid search with cross-validation
        grid_search = GridSearchCV(
            KNeighborsClassifier(),
            param_grid,
            cv=5,
            scoring='accuracy',
            n_jobs=-1,
            verbose=1
        )

        grid_search.fit(X_train_scaled, y_train_encoded)

        self.best_params = grid_search.best_params_
        print(f"\nBest parameters: {self.best_params}")
        print(f"Best CV score: {grid_search.best_score_:.4f}")

        # Evaluate on validation set
        val_score = grid_search.score(X_val_scaled, y_val_encoded)
        print(f"Validation score with best params: {val_score:.4f}")

        # Update model with best parameters
        self.n_neighbors = self.best_params['n_neighbors']
        self.weights = self.best_params['weights']
        self.knn = grid_search.best_estimator_

        return grid_search

    def select_features(self, X_train, y_train, n_features='auto'):
        """
        Select top K features using statistical tests
        """
        print("\n" + "="*60)
        print("Feature Selection")
        print("="*60)

        y_train_encoded = self.label_encoder.transform(y_train)

        if n_features == 'auto':
            # Select top 50% of features
            n_features = max(10, X_train.shape[1] // 2)

        print(f"Selecting top {n_features} features out of {X_train.shape[1]}")

        # Use mutual information for feature selection
        self.feature_selector = SelectKBest(mutual_info_classif, k=n_features)
        X_train_selected = self.feature_selector.fit_transform(
            X_train, y_train_encoded)

        # Get feature scores
        scores = self.feature_selector.scores_
        selected_indices = self.feature_selector.get_support(indices=True)

        print(f"Selected features: {selected_indices}")
        print(f"Feature scores (top 10): {sorted(scores, reverse=True)[:10]}")

        return X_train_selected

    def train(self, X_train, y_train, X_val=None, y_val=None, tune=True, select_features=True):
        """Train the KNN classifier with improvements"""
        print(f"Training with {len(X_train)} samples...")

        # Encode labels
        y_train_encoded = self.label_encoder.fit_transform(y_train)

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)

        # Feature selection
        if select_features:
            X_train_processed = self.select_features(
                X_train_scaled, y_train, n_features='auto')
        else:
            X_train_processed = X_train_scaled

        # Hyperparameter tuning
        if tune and X_val is not None and y_val is not None:
            # For tuning, we need to apply same preprocessing to validation set
            y_val_encoded = self.label_encoder.transform(y_val)
            X_val_scaled = self.scaler.transform(X_val)
            if select_features and self.feature_selector is not None:
                X_val_processed = self.feature_selector.transform(X_val_scaled)
            else:
                X_val_processed = X_val_scaled

            # Retune with processed features
            param_grid = {
                'n_neighbors': [3, 5, 7, 9, 11, 15, 21, 31],
                'weights': ['uniform', 'distance'],
                'metric': ['euclidean', 'manhattan']
            }

            print("\n" + "="*60)
            print("Hyperparameter Tuning (on preprocessed features)")
            print("="*60)

            grid_search = GridSearchCV(
                KNeighborsClassifier(),
                param_grid,
                cv=5,
                scoring='accuracy',
                n_jobs=-1,
                verbose=1
            )

            grid_search.fit(X_train_processed, y_train_encoded)

            self.best_params = grid_search.best_params_
            self.knn = grid_search.best_estimator_

            print(f"\nBest parameters: {self.best_params}")
            print(f"Best CV score: {grid_search.best_score_:.4f}")

            val_score = grid_search.score(X_val_processed, y_val_encoded)
            print(f"Validation score: {val_score:.4f}")
        else:
            # Train with default or preset parameters
            if not hasattr(self, 'knn') or self.knn is None:
                self.knn = KNeighborsClassifier(
                    n_neighbors=self.n_neighbors,
                    weights=self.weights
                )
            self.knn.fit(X_train_processed, y_train_encoded)

        print(f"Training complete. Classes: {self.label_encoder.classes_}")

    def predict(self, X):
        """Make predictions on new data"""
        X_scaled = self.scaler.transform(X)
        if self.feature_selector is not None:
            X_scaled = self.feature_selector.transform(X_scaled)
        y_pred_encoded = self.knn.predict(X_scaled)
        return self.label_encoder.inverse_transform(y_pred_encoded)

    def predict_proba(self, X):
        """Get prediction probabilities"""
        X_scaled = self.scaler.transform(X)
        if self.feature_selector is not None:
            X_scaled = self.feature_selector.transform(X_scaled)
        return self.knn.predict_proba(X_scaled)

    def evaluate(self, X, y, dataset_name="Validation"):
        """Evaluate the model and print metrics"""
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
        cm = confusion_matrix(
            y_true, y_pred, labels=self.label_encoder.classes_)

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

    def save_model(self, filepath):
        """Save the trained model"""
        model_data = {
            'knn': self.knn,
            'scaler': self.scaler,
            'label_encoder': self.label_encoder,
            'feature_selector': self.feature_selector,
            'n_neighbors': self.n_neighbors,
            'weights': self.weights,
            'best_params': self.best_params
        }
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        print(f"Model saved to {filepath}")

    def load_model(self, filepath):
        """Load a trained model"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        self.knn = model_data['knn']
        self.scaler = model_data['scaler']
        self.label_encoder = model_data['label_encoder']
        self.feature_selector = model_data.get('feature_selector')
        self.n_neighbors = model_data['n_neighbors']
        self.weights = model_data['weights']
        self.best_params = model_data.get('best_params')
        print(f"Model loaded from {filepath}")


def create_subject_splits(all_subjects, random_seed=42):
    """Split subjects into train/val/test sets"""
    np.random.seed(random_seed)
    subjects = np.array(all_subjects)
    np.random.shuffle(subjects)

    train_subjects = subjects[:21].tolist()
    val_subjects = subjects[21:24].tolist()
    test_subjects = subjects[24:27].tolist()

    return train_subjects, val_subjects, test_subjects


def prepare_unsegmented_test_data(df_clean, test_subjects, classifier, window_size=100, overlap=50):
    """
    Prepare test data from full unsegmented files using sliding window
    """
    print(f"\nPreparing unsegmented test data for subjects: {test_subjects}")
    print(f"Window size: {window_size}, Overlap: {overlap}")

    # Filter for test subjects and target exercises
    df_test = df_clean[df_clean['subject_id'].isin(test_subjects)]
    df_test = df_test[df_test['exercise'].isin(
        ['Ankle Rotation', 'Calf Raises', 'Heel Walk'])]

    X_test = []
    y_test = []

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

            # Create segment-like data structure
            segment_data = {
                'acc_x': window['acc_x'].values,
                'acc_y': window['acc_y'].values,
                'acc_z': window['acc_z'].values,
                'gyr_x': window['gyr_x'].values,
                'gyr_y': window['gyr_y'].values,
                'gyr_z': window['gyr_z'].values,
                'roll': np.zeros(len(window)),
                'pitch': np.zeros(len(window))
            }

            # Extract features
            features = classifier.extract_features_from_segment(segment_data)

            X_test.append(features)
            y_test.append(exercise)

    print(f"Created {len(X_test)} test windows from unsegmented data")
    return np.array(X_test), np.array(y_test)


def main():
    """Main training and evaluation pipeline"""

    # Create output directories
    Path('results/knn_model_improved').mkdir(parents=True, exist_ok=True)

    print("="*60)
    print("Improved KNN Exercise Classifier - Training Pipeline")
    print("="*60)

    # Load data
    print("\nLoading data...")
    df_segmented = pd.read_csv('results/segmented_signals.csv')
    df_clean = pd.read_csv('results/clean_signals.csv')

    # Filter for target exercises
    target_exercises = ['Ankle Rotation', 'Calf Raises', 'Heel Walk']
    df_segmented = df_segmented[df_segmented['exercise'].isin(
        target_exercises)]

    print(f"Loaded {len(df_segmented)} segmented samples")
    print(f"Loaded {len(df_clean)} full data samples")

    # Create subject splits (same as before for fair comparison)
    all_subjects = sorted(df_segmented['subject_id'].unique())
    train_subjects, val_subjects, test_subjects = create_subject_splits(
        all_subjects)

    print(f"\nSubject splits:")
    print(f"Train ({len(train_subjects)}): {train_subjects}")
    print(f"Val ({len(val_subjects)}): {val_subjects}")
    print(f"Test ({len(test_subjects)}): {test_subjects}")

    # Prepare training data
    print("\n" + "="*60)
    print("Preparing Training Data (Segmented)")
    print("="*60)
    df_train = df_segmented[df_segmented['subject_id'].isin(train_subjects)]
    classifier = ImprovedKNNExerciseClassifier()
    X_train, y_train = classifier.prepare_segmented_data(df_train)

    print(f"Training set: {X_train.shape}")
    print(f"Class distribution:\n{pd.Series(y_train).value_counts()}")

    # Prepare validation data
    print("\n" + "="*60)
    print("Preparing Validation Data (Segmented)")
    print("="*60)
    df_val = df_segmented[df_segmented['subject_id'].isin(val_subjects)]
    X_val, y_val = classifier.prepare_segmented_data(df_val)

    print(f"Validation set: {X_val.shape}")
    print(f"Class distribution:\n{pd.Series(y_val).value_counts()}")

    # Train model with improvements
    print("\n" + "="*60)
    print("Training Improved KNN Model")
    print("="*60)
    classifier.train(X_train, y_train, X_val, y_val,
                     tune=True, select_features=True)

    # Evaluate on training set
    print("\n" + "="*60)
    print("Training Set Performance")
    print("="*60)
    y_train_pred = classifier.evaluate(X_train, y_train, "Training")
    classifier.plot_confusion_matrix(y_train, y_train_pred,
                                     "Training Set Confusion Matrix (Improved)",
                                     "results/knn_model_improved/confusion_matrix_train.png")

    # Evaluate on validation set
    y_val_pred = classifier.evaluate(X_val, y_val, "Validation")
    classifier.plot_confusion_matrix(y_val, y_val_pred,
                                     "Validation Set Confusion Matrix (Improved)",
                                     "results/knn_model_improved/confusion_matrix_val.png")

    # Prepare test data (unsegmented full files)
    print("\n" + "="*60)
    print("Preparing Test Data (Full Unsegmented Files)")
    print("="*60)
    X_test, y_test = prepare_unsegmented_test_data(df_clean, test_subjects, classifier,
                                                   window_size=100, overlap=50)

    print(f"Test set: {X_test.shape}")
    print(f"Class distribution:\n{pd.Series(y_test).value_counts()}")

    # Evaluate on test set
    y_test_pred = classifier.evaluate(X_test, y_test, "Test (Unsegmented)")
    classifier.plot_confusion_matrix(y_test, y_test_pred,
                                     "Test Set Confusion Matrix (Improved)",
                                     "results/knn_model_improved/confusion_matrix_test.png")

    # Save model
    classifier.save_model(
        'results/knn_model_improved/knn_classifier_improved.pkl')

    # Save results summary
    results_summary = {
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

    with open('results/knn_model_improved/results_summary.json', 'w') as f:
        json.dump(results_summary, f, indent=2)

    # Load baseline results for comparison
    try:
        with open('results/knn_model/results_summary.json', 'r') as f:
            baseline_results = json.load(f)

        print("\n" + "="*60)
        print("Comparison: Baseline vs Improved")
        print("="*60)
        print(f"{'Metric':<20} {'Baseline':<12} {'Improved':<12} {'Change':<12}")
        print("-" * 60)
        print(f"{'Train Accuracy':<20} {baseline_results['train_accuracy']:<12.4f} "
              f"{results_summary['train_accuracy']:<12.4f} "
              f"{results_summary['train_accuracy'] - baseline_results['train_accuracy']:+.4f}")
        print(f"{'Val Accuracy':<20} {baseline_results['val_accuracy']:<12.4f} "
              f"{results_summary['val_accuracy']:<12.4f} "
              f"{results_summary['val_accuracy'] - baseline_results['val_accuracy']:+.4f}")
        print(f"{'Test Accuracy':<20} {baseline_results['test_accuracy']:<12.4f} "
              f"{results_summary['test_accuracy']:<12.4f} "
              f"{results_summary['test_accuracy'] - baseline_results['test_accuracy']:+.4f}")
        print(f"{'Gap (Train-Test)':<20} "
              f"{baseline_results['train_accuracy'] - baseline_results['test_accuracy']:<12.4f} "
              f"{results_summary['train_accuracy'] - results_summary['test_accuracy']:<12.4f} "
              f"{(results_summary['train_accuracy'] - results_summary['test_accuracy']) - (baseline_results['train_accuracy'] - baseline_results['test_accuracy']):+.4f}")
    except:
        pass

    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print(f"Results saved to results/knn_model_improved/")
    print(f"\nFinal Results:")
    print(f"  Best params: {results_summary['best_params']}")
    print(
        f"  Features: {results_summary['n_features_selected']}/{results_summary['total_features']}")
    print(f"  Train Accuracy: {results_summary['train_accuracy']:.4f}")
    print(f"  Val Accuracy: {results_summary['val_accuracy']:.4f}")
    print(f"  Test Accuracy: {results_summary['test_accuracy']:.4f}")
    print(
        f"  Overfitting Gap (Train-Test): {results_summary['train_accuracy'] - results_summary['test_accuracy']:.4f}")


if __name__ == "__main__":
    main()


'''Final Performance

  - Training: 100.00%
  - Validation: 99.35%
  - Test: 85.39%
'''
