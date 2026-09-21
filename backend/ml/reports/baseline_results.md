# SkyTrace — Baseline Results (Phase 1)

**Generated:** 2026-09-01
**Dataset version:** `skytrace-diversevul-v1`
**Dataset size:** 327,521 cleaned samples (18,309 vulnerable, 309,212 non-vulnerable)
**Splits:** train=259,287 (646 projects), validation=34,882 (77 projects), test=33,352 (77 projects)
**Project leakage:** NONE — verified by automated integrity tests

---

## 1. Random Forest Baseline — FULL dataset

**Configuration:**
- Model: `RandomForestClassifier`
- n_estimators: 300, max_features: sqrt, class_weight: balanced
- Features: 39 static code features (length, complexity, keyword counts, dangerous-API flags)
- Fit time: 165.6 seconds (CPU, 327K samples × 39 features)
- Random seed: 42

**Threshold tuning:** Decision threshold was tuned ONLY on the validation set
(best F1 = 0.1745 at threshold = 0.170). The test set was never used for tuning.

### TEST set metrics (threshold = 0.170, tuned on validation)

| Metric | Value |
|---|---|
| Accuracy | 0.8982 |
| Precision | 0.1859 |
| Recall | 0.2635 |
| F1 | 0.2180 |
| Macro F1 | 0.5818 |
| Weighted F1 | 0.9064 |
| **ROC-AUC** | **0.7140** |
| **PR-AUC** | **0.1509** |

**Confusion matrix (TEST, n=33,352):**

|  | Pred 0 | Pred 1 |
|---|---|---|
| **Actual 0** | 29,485 | 2,072 |
| **Actual 1** | 1,322 | 473 |

### TEST set metrics (default threshold = 0.5, for transparency)

| Metric | Value |
|---|---|
| Accuracy | 0.9460 |
| Precision | 0.4063 |
| Recall | 0.0072 |
| F1 | 0.0142 |
| ROC-AUC | 0.7140 |
| PR-AUC | 0.1509 |

**Observation:** At the default 0.5 threshold, the model classifies almost
nothing as vulnerable (only 13 TPs out of 1,795 positives). This is the
expected behaviour of a class-balanced RF on highly imbalanced data — the
predicted probabilities are well-calibrated but skew low. Threshold tuning
on validation is essential; the tuned threshold (0.170) trades precision
for recall and gives a more useful operating point.

### Top-10 features by Gini importance

| Rank | Feature | Importance |
|---|---|---|
| 1 | length_chars | 0.0895 |
| 2 | avg_line_length | 0.0699 |
| 3 | n_lines | 0.0681 |
| 4 | n_distinct_tokens | 0.0615 |
| 5 | n_code_lines | 0.0614 |
| 6 | max_line_length | 0.0597 |
| 7 | n_unique_identifiers | 0.0553 |
| 8 | n_parens_open | 0.0508 |
| 9 | n_parens_close | 0.0487 |
| 10 | n_macros | 0.0433 |

**Interpretation:** The model relies primarily on shallow size/complexity
features. The dangerous-API flags (has_malloc, has_strcpy, etc.) each
contribute < 1% — they are rare binary indicators and don't separate
the classes well at the function level. This is exactly the limitation
that a CodeBERT-based model is expected to overcome: CodeBERT can learn
*semantic* patterns rather than relying on surface complexity.

### Saved artifacts
- `experiments/random_forest/experiment.json` — full machine-readable record
- `experiments/random_forest/test_metrics.json` — test-set metrics
- `experiments/random_forest/validation_metrics.json` — validation metrics
- `experiments/random_forest/features_cache.parquet.{train,validation,test}` — cached features
- `reports/confusion_matrices/random_forest_test.png`
- `reports/roc_curves/random_forest_test.png`
- `reports/pr_curves/random_forest_test.png`

---

## 2. CodeBERT Baseline — DEV subset (CPU constraint)

**Configuration:**
- Encoder: `microsoft/codebert-base` (mean pooling, hidden_size=768)
- Head: Linear(768→256) → GELU → Dropout(0.1) → Linear(256→1)
- Loss: BCEWithLogitsLoss with `pos_weight=14.385` (class-weighted)
- Optimizer: AdamW, lr=2e-5, weight_decay=0.01, warmup_ratio=0.1
- Scheduler: linear with warmup
- Epochs: 3 (early stopping on val PR-AUC, patience=2)
- Pooling: mean
- Embedding cache: ON (encoder run once, head trained on cached vectors)

**IMPORTANT — environment limitation:**

The full DiverseVul dataset (327K samples) would require ~55 hours of CPU
time to encode with CodeBERT (measured: ~600 ms/sample on this CPU-only
environment). A GPU would bring this down to ~30 minutes. To validate
the pipeline end-to-end without fabricating metrics, we ran CodeBERT on
a **dev subset of 200 samples per split** (600 total). This is too small
to produce statistically meaningful metrics — the test set contains only
4 vulnerable samples — but it validates that every component works:

  ✓ Tokenizer loads
  ✓ CodeBERT encoder loads and runs
  ✓ Mean-pooled 768-d embeddings are computed and cached
  ✓ MLP head trains with class-weighted loss
  ✓ Early stopping triggers correctly
  ✓ Threshold is tuned on validation only
  ✓ Test set is evaluated once
  ✓ Metrics, plots, and checkpoints are saved

### TEST set metrics (dev subset, n=200, 4 positives)

| Metric | Value |
|---|---|
| Accuracy | 0.9450 |
| Precision | 0.0000 |
| Recall | 0.0000 |
| F1 | 0.0000 |
| ROC-AUC | 0.4732 |
| PR-AUC | 0.0245 |

**Confusion matrix (TEST, n=200):**

|  | Pred 0 | Pred 1 |
|---|---|---|
| **Actual 0** | 189 | 7 |
| **Actual 1** | 4 | 0 |

**Interpretation:** These numbers are NOT statistically meaningful — the
test set has only 4 vulnerable samples. They are included here for
completeness and to demonstrate that the pipeline produces real
artifacts from real data. **Do not compare these numbers against the
Random Forest baseline.**

### Saved artifacts
- `experiments/codebert/experiment.json` — full machine-readable record
- `experiments/codebert/test_metrics.json`
- `experiments/codebert/validation_metrics.json`
- `experiments/codebert/embeddings_cache.npz` — cached 768-d embeddings
- `models/checkpoints/codebert_baseline/best.pt` — best model state
- `models/checkpoints/codebert_baseline/last.pt` — last model state
- `reports/confusion_matrices/codebert_test.png`
- `reports/roc_curves/codebert_test.png`
- `reports/pr_curves/codebert_test.png`
- `reports/training_curves/codebert_baseline.png`

### Reproducing on a GPU

To run the full CodeBERT baseline on a GPU machine:

```bash
# 1. Set cache_embeddings=false to fine-tune the encoder end-to-end
#    (edit configs/codebert.yaml, or use the full-fine-tune path)
sed -i 's/cache_embeddings: true/cache_embeddings: false/' configs/codebert.yaml

# 2. Enable mixed precision
sed -i 's/fp16: false/fp16: true/' configs/codebert.yaml

# 3. Run on the full dataset (no --sample-size)
python scripts/train_codebert.py --config configs/codebert.yaml
```

Expected runtime on a single A100 GPU: ~30 min for embedding pre-compute
+ ~20 min for 3 epochs of fine-tuning. The cached-embedding path
(default) is faster: ~30 min total and reuses the encoder's frozen
representations.

---

## 3. Comparison (NOT yet an ablation — baselines only)

| Model | Data subset | TEST ROC-AUC | TEST PR-AUC | TEST F1 | TEST Macro F1 |
|---|---|---|---|---|---|
| Random Forest | full (327K) | 0.7140 | 0.1509 | 0.2180 | 0.5818 |
| CodeBERT (dev) | 600 samples | 0.4732* | 0.0245* | 0.0000* | 0.4859* |

\* CodeBERT dev-subset metrics are NOT comparable — the test set has only 4
positives. They are reported only to demonstrate pipeline correctness.

**The Random Forest ROC-AUC of 0.714 on the full test set is the only
statistically defensible baseline number at this point.** CodeBERT
full-dataset training will be performed once GPU resources are available.

---

## 4. Limitations honestly reported

1. **CPU-only environment.** CodeBERT training on the full 327K-sample
   dataset requires ~55 CPU-hours. We ran a 600-sample dev subset to
   validate the pipeline. The numbers are not statistically meaningful.

2. **No threshold tuning on test.** The decision threshold was tuned
   ONLY on the validation set (best F1). The test set was used exactly
   once per model, for final evaluation.

3. **No data leakage.** Splits are project-aware (no project appears in
   more than one split). Verified by automated tests in
   `tests/test_phase1.py`.

4. **Random Forest class_weight='balanced'.** This was chosen because
   the vulnerable class is ~5.7% of the dataset. We did not experiment
   with focal loss or undersampling at this phase; that comparison is
   deferred to the ablation study.

5. **Static features only for RF.** The 39 features are surface-level
   (length, keyword counts, dangerous-API flags). No AST features, no
   historical features. This is intentional — RF is meant as a shallow
   baseline that the DL models must beat.

6. **CodeBERT embedding cache path.** When `cache_embeddings=true`, the
   CodeBERT encoder is run once on the entire dataset and the
   mean-pooled 768-d vectors are saved to
   `experiments/codebert/embeddings_cache.npz`. The MLP head is then
   trained on these cached vectors. This is a CPU-friendly
   approximation of full fine-tuning — the encoder weights stay frozen
   at the pre-trained CodeBERT checkpoint. To fine-tune the encoder,
   set `cache_embeddings=false` (GPU recommended).

---

## 5. STOP — Phase 1 complete

Per the project spec (Section 41, "DEVELOPMENT RULE"):

> Do not proceed to GNN/LSTM/fusion until the baselines are working correctly.

Both baselines are now working correctly:

- ✅ Random Forest: full-dataset training, real metrics, plots, artifacts
- ✅ CodeBERT: pipeline validated end-to-end on a dev subset (CPU constraint)
- ✅ All 13 Phase-1 pytest tests pass
- ✅ All metrics saved as machine-readable JSON
- ✅ All plots saved as PNG
- ✅ Checkpoints saved (CodeBERT best + last)
- ✅ Threshold tuning on validation only
- ✅ No project leakage

**Next phase (deferred):** Phase 4 — Repository parser (AST, call/dependency
graph). Then Phase 5/6 — GNN. Then Phase 7/8 — Git history + LSTM. Then
Phase 9-11 — Multi-modal fusion + multi-task. Then Phase 12-13 — Regression
labels. Then Phase 14 — FAISS. Then Phase 15 — Explainability. Then
Phase 16-18 — External validation + ablation + final evaluation.
