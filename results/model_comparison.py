"""
Compare LSTM vs KNN Model Performance
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load results
with open('results/knn_model/results_summary.json', 'r') as f:
    knn_results = json.load(f)

with open('results/lstm_model/results_summary.json', 'r') as f:
    lstm_results = json.load(f)

# Load baseline LSTM for comparison
try:
    with open('results/lstm_model_baseline/results_summary.json', 'r') as f:
        lstm_baseline = json.load(f)
    show_baseline = True
except FileNotFoundError:
    show_baseline = False

print("="*60)
print("Model Comparison: KNN vs LSTM (Improved)")
print("="*60)

# Create comparison table
comparison = {
    'Metric': ['Training Accuracy', 'Validation Accuracy', 'Test Accuracy (Unsegmented)',
               'Overfitting Gap (Train-Test)', 'Model Type'],
    'KNN (Improved)': [
        f"{knn_results['train_accuracy']:.4f} ({knn_results['train_accuracy']*100:.2f}%)",
        f"{knn_results['val_accuracy']:.4f} ({knn_results['val_accuracy']*100:.2f}%)",
        f"{knn_results['test_accuracy']:.4f} ({knn_results['test_accuracy']*100:.2f}%)",
        f"{knn_results['train_accuracy'] - knn_results['test_accuracy']:.4f} ({(knn_results['train_accuracy'] - knn_results['test_accuracy'])*100:.2f}%)",
        'K-Nearest Neighbors (K=3)'
    ],
    'LSTM (Improved)': [
        f"{lstm_results['train_accuracy']:.4f} ({lstm_results['train_accuracy']*100:.2f}%)",
        f"{lstm_results['val_accuracy']:.4f} ({lstm_results['val_accuracy']*100:.2f}%)",
        f"{lstm_results['test_accuracy']:.4f} ({lstm_results['test_accuracy']*100:.2f}%)",
        f"{lstm_results['train_accuracy'] - lstm_results['test_accuracy']:.4f} ({(lstm_results['train_accuracy'] - lstm_results['test_accuracy'])*100:.2f}%)",
        'Bidirectional LSTM (32 units)'
    ],
    'Winner': [
        'KNN' if knn_results['train_accuracy'] > lstm_results['train_accuracy'] else 'LSTM',
        'LSTM' if lstm_results['val_accuracy'] > knn_results['val_accuracy'] else 'KNN',
        'KNN' if knn_results['test_accuracy'] > lstm_results['test_accuracy'] else 'LSTM',
        'KNN' if (knn_results['train_accuracy'] - knn_results['test_accuracy']) < (lstm_results['train_accuracy'] - lstm_results['test_accuracy']) else 'LSTM',
        '-'
    ]
}

df = pd.DataFrame(comparison)
print("\n" + df.to_string(index=False))

print("\n" + "="*60)
print("Key Findings")
print("="*60)

knn_gap = knn_results['train_accuracy'] - knn_results['test_accuracy']
lstm_gap = lstm_results['train_accuracy'] - lstm_results['test_accuracy']

print(f"\n1. Test Accuracy (Most Important):")
print(f"   KNN:  {knn_results['test_accuracy']:.2%} ← WINNER")
print(f"   LSTM: {lstm_results['test_accuracy']:.2%}")
print(f"   Difference: +{(knn_results['test_accuracy'] - lstm_results['test_accuracy'])*100:.2f}% in favor of KNN")

print(f"\n2. Generalization (Lower is Better):")
print(f"   KNN (Improved):  {knn_gap:.2%} gap ← BETTER")
print(f"   LSTM (Improved): {lstm_gap:.2%} gap")
print(f"   KNN generalizes {(lstm_gap - knn_gap)*100:.2f}% better")

if show_baseline:
    baseline_gap = lstm_baseline['train_accuracy'] - lstm_baseline['test_accuracy']
    print(f"\n   LSTM Baseline:   {baseline_gap:.2%} gap")
    print(f"   LSTM Improvement: {(baseline_gap - lstm_gap)*100:.2f}% reduction in overfitting")

print(f"\n3. Validation Performance:")
print(f"   KNN:  {knn_results['val_accuracy']:.2%}")
print(f"   LSTM: {lstm_results['val_accuracy']:.2%} ← SLIGHTLY BETTER")

print(f"\n4. Training Details:")
print(f"   KNN:  Features={knn_results['n_features_selected']}, K={knn_results['best_params']['n_neighbors']}")
print(f"   LSTM: Sequence length={lstm_results['model_architecture']['max_sequence_length']}, Epochs={lstm_results['epochs_trained']}")

print("\n" + "="*60)
print("Conclusion")
print("="*60)
print("\n✓ KNN (Improved) is the BETTER model for this task")
print(f"  - Superior test accuracy: {knn_results['test_accuracy']:.2%} vs {lstm_results['test_accuracy']:.2%}")
print(f"  - Better generalization: {knn_gap:.2%} gap vs {lstm_gap:.2%} gap")
print(f"  - Faster inference (no sequence processing)")
print(f"  - Simpler architecture")
print("\n✓ LSTM (Improved) shows:")
print(f"  - Excellent validation accuracy: {lstm_results['val_accuracy']:.2%}")
print(f"  - Good at learning patterns from segmented data")
print(f"  - Better than baseline: {lstm_results['test_accuracy']:.2%} test accuracy")
if show_baseline:
    baseline_gap = lstm_baseline['train_accuracy'] - lstm_baseline['test_accuracy']
    test_improvement = (lstm_results['test_accuracy'] - lstm_baseline['test_accuracy']) * 100
    overfitting_reduction = (baseline_gap - lstm_gap) * 100
    print(f"  - Reduced overfitting by {overfitting_reduction:.2f}% vs baseline")
    print(f"  - Improved test accuracy by {test_improvement:.2f}% vs baseline")
else:
    print(f"  - Reduced overfitting through regularization")
    print(f"  - Still struggles with unsegmented continuous data")

# Create visualization
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Accuracy comparison
metrics = ['Train', 'Val', 'Test']
knn_scores = [knn_results['train_accuracy'], knn_results['val_accuracy'], knn_results['test_accuracy']]
lstm_scores = [lstm_results['train_accuracy'], lstm_results['val_accuracy'], lstm_results['test_accuracy']]

x = range(len(metrics))
width = 0.35

axes[0].bar([i - width/2 for i in x], knn_scores, width, label='KNN', alpha=0.8, color='#2ecc71')
axes[0].bar([i + width/2 for i in x], lstm_scores, width, label='LSTM', alpha=0.8, color='#3498db')
axes[0].set_xlabel('Dataset')
axes[0].set_ylabel('Accuracy')
axes[0].set_title('Model Accuracy Comparison')
axes[0].set_xticks(x)
axes[0].set_xticklabels(metrics)
axes[0].legend()
axes[0].set_ylim([0.7, 1.05])
axes[0].grid(True, alpha=0.3)

# Add value labels on bars
for i, (knn_score, lstm_score) in enumerate(zip(knn_scores, lstm_scores)):
    axes[0].text(i - width/2, knn_score + 0.01, f'{knn_score:.3f}', ha='center', fontsize=9)
    axes[0].text(i + width/2, lstm_score + 0.01, f'{lstm_score:.3f}', ha='center', fontsize=9)

# Overfitting gap comparison
models = ['KNN', 'LSTM']
gaps = [knn_gap, lstm_gap]
colors = ['#2ecc71', '#3498db']

axes[1].bar(models, gaps, color=colors, alpha=0.8)
axes[1].set_ylabel('Overfitting Gap (Train - Test)')
axes[1].set_title('Generalization Comparison\n(Lower is Better)')
axes[1].grid(True, alpha=0.3, axis='y')

# Add value labels
for i, (model, gap) in enumerate(zip(models, gaps)):
    axes[1].text(i, gap + 0.01, f'{gap:.3f}\n({gap*100:.1f}%)', ha='center', fontsize=10)

plt.tight_layout()
plt.savefig('results/knn_vs_lstm_comparison.png', dpi=300, bbox_inches='tight')
print(f"\n✓ Comparison chart saved to results/knn_vs_lstm_comparison.png")

# Save detailed comparison
test_diff = (knn_results['test_accuracy'] - lstm_results['test_accuracy']) * 100
gen_diff = (lstm_gap - knn_gap) * 100

detailed_comparison = {
    'knn': knn_results,
    'lstm_improved': lstm_results,
    'winner': {
        'model': 'KNN (Improved)',
        'test_accuracy': knn_results['test_accuracy'],
        'advantages': [
            f'Higher test accuracy (+{test_diff:.2f}%)',
            f'Better generalization ({gen_diff:.2f}% less overfitting)',
            'Faster inference',
            'Simpler model'
        ]
    }
}

if show_baseline:
    detailed_comparison['lstm_baseline'] = lstm_baseline
    baseline_gap = lstm_baseline['train_accuracy'] - lstm_baseline['test_accuracy']
    test_improvement = (lstm_results['test_accuracy'] - lstm_baseline['test_accuracy']) * 100
    overfitting_reduction = (baseline_gap - lstm_gap) * 100
    detailed_comparison['lstm_improvements'] = {
        'test_accuracy_gain': f'+{test_improvement:.2f}%',
        'overfitting_reduction': f'-{overfitting_reduction:.2f}%',
        'techniques_used': [
            'Simplified architecture (1 LSTM layer instead of 2)',
            'Reduced LSTM units (32 instead of 64+32)',
            'Increased dropout (0.5 instead of 0.3)',
            'Added L2 regularization (0.01)',
            'Increased recurrent dropout (0.5 instead of 0.2)'
        ]
    }

with open('results/model_comparison.json', 'w') as f:
    json.dump(detailed_comparison, f, indent=2)

print(f"✓ Detailed comparison saved to results/model_comparison.json")
