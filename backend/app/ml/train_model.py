"""
ML training and prediction module for UFIE flood-risk classification.

Supports XGBoost, Random Forest, and Gradient Boosting classifiers.
The continuous ``flood_probability`` target is binned into discrete risk
classes before training so that standard classification metrics (accuracy,
F1, AUC) can be used for evaluation.
"""

import logging
from typing import Optional

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.preprocessing import label_binarize

from .features import FEATURE_NAMES, extract_features_from_hotspots

logger = logging.getLogger(__name__)

# ── Module-level model cache ─────────────────────────────────────────────
_cached_model: Optional[object] = None
_cached_metrics: Optional[dict] = None

# ── Risk-level thresholds ────────────────────────────────────────────────
_RISK_THRESHOLDS: list[tuple[float, str]] = [
    (0.75, "Critical"),
    (0.50, "High"),
    (0.25, "Moderate"),
    (0.00, "Low"),
]

# Number of classification bins (maps to the four risk levels)
_N_BINS = 4


# ── Public API ───────────────────────────────────────────────────────────


def train_flood_model(
    hotspots_geojson: dict,
    model_type: str = "xgboost",
) -> dict:
    """Train a flood-risk classification model from hotspot GeoJSON.

    Parameters
    ----------
    hotspots_geojson : dict
        GeoJSON FeatureCollection with per-feature properties matching
        :pydata:`FEATURE_NAMES` and a ``flood_probability`` target.
    model_type : str
        One of ``"xgboost"``, ``"random_forest"``, or
        ``"gradient_boosting"``.

    Returns
    -------
    result : dict
        ``model`` -- fitted estimator
        ``metrics`` -- dict with *accuracy*, *f1*, *auc*
        ``feature_importances`` -- dict mapping feature name to importance
    """
    # ── Extract features and bin the target ──────────────────────────────
    X, y_prob = extract_features_from_hotspots(hotspots_geojson)

    if X.shape[0] == 0:
        raise ValueError(
            "No valid training samples found in the supplied GeoJSON."
        )

    y_class = _bin_probability(y_prob)

    # ── Build the estimator ──────────────────────────────────────────────
    model = _build_estimator(model_type)

    # ── Cross-validated predictions for metric estimation ────────────────
    n_classes = len(np.unique(y_class))
    n_splits = min(5, max(2, n_classes))  # at least 2 folds
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    # Guard against folds that would have classes with < 2 members
    try:
        y_pred_cv = cross_val_predict(model, X, y_class, cv=cv, method="predict")
        y_proba_cv = cross_val_predict(model, X, y_class, cv=cv, method="predict_proba")
    except ValueError:
        # Fall back to simple train-on-all if CV is impossible (tiny data)
        y_pred_cv = None
        y_proba_cv = None

    # ── Final fit on all data ────────────────────────────────────────────
    model.fit(X, y_class)

    # ── Metrics ──────────────────────────────────────────────────────────
    if y_pred_cv is not None and y_proba_cv is not None:
        metrics = _compute_metrics(y_class, y_pred_cv, y_proba_cv, n_classes)
    else:
        # Resubstitution metrics (optimistic, but better than nothing)
        y_pred_all = model.predict(X)
        y_proba_all = model.predict_proba(X)
        metrics = _compute_metrics(y_class, y_pred_all, y_proba_all, n_classes)
        metrics["note"] = "resubstitution (dataset too small for CV)"

    # ── Feature importances ──────────────────────────────────────────────
    importances = dict(zip(FEATURE_NAMES, model.feature_importances_))

    return {
        "model": model,
        "metrics": metrics,
        "feature_importances": importances,
    }


def predict_flood_risk(model, features: np.ndarray) -> dict:
    """Predict flood probability and risk level for a feature vector.

    Parameters
    ----------
    model : fitted sklearn-compatible estimator
        A classifier previously returned by :func:`train_flood_model`.
    features : np.ndarray, shape (1, n_features)
        Feature row produced by
        :func:`features.extract_features_for_prediction`.

    Returns
    -------
    result : dict
        ``probability`` -- float in [0, 1]
        ``risk_level`` -- one of Critical / High / Moderate / Low
        ``contributing_factors`` -- dict mapping each feature name to its
        relative contribution to the prediction
    """
    features = np.atleast_2d(features)

    # Class probabilities -> scalar flood probability
    proba = model.predict_proba(features)[0]
    # Weighted average of bin centres gives a continuous probability
    bin_centres = np.linspace(0, 1, len(proba))
    flood_probability = float(np.dot(proba, bin_centres))
    flood_probability = float(np.clip(flood_probability, 0.0, 1.0))

    risk_level = _classify_risk(flood_probability)

    # ── Per-feature contribution (importance * normalised feature value) ─
    importances = model.feature_importances_
    feature_values = features[0]

    # Normalise feature values to [0, 1] using simple min-max vs. defaults
    safe_max = np.where(np.abs(feature_values) > 1e-9, np.abs(feature_values), 1.0)
    normalised = np.abs(feature_values) / safe_max

    raw_contributions = importances * normalised
    total = raw_contributions.sum()
    if total > 0:
        contributions = raw_contributions / total
    else:
        contributions = np.full_like(raw_contributions, 1.0 / len(FEATURE_NAMES))

    contributing_factors = {
        name: round(float(contrib), 4)
        for name, contrib in zip(FEATURE_NAMES, contributions)
    }

    return {
        "probability": round(flood_probability, 4),
        "risk_level": risk_level,
        "contributing_factors": contributing_factors,
    }


def get_or_train_model(
    hotspots_geojson: dict,
) -> tuple:
    """Return a cached model or train a new one.

    Parameters
    ----------
    hotspots_geojson : dict
        GeoJSON FeatureCollection (passed to :func:`train_flood_model`
        only when no cached model exists).

    Returns
    -------
    model : fitted estimator
    metrics : dict
    """
    global _cached_model, _cached_metrics

    if _cached_model is not None and _cached_metrics is not None:
        logger.info("Returning cached flood-risk model.")
        return _cached_model, _cached_metrics

    logger.info("No cached model found -- training a new flood-risk model.")
    result = train_flood_model(hotspots_geojson)
    _cached_model = result["model"]
    _cached_metrics = result["metrics"]
    return _cached_model, _cached_metrics


# ── Private helpers ──────────────────────────────────────────────────────


def _classify_risk(probability: float) -> str:
    """Map a continuous flood probability to a discrete risk label.

    Thresholds
    ----------
    >= 0.75  -> Critical
    >= 0.50  -> High
    >= 0.25  -> Moderate
    <  0.25  -> Low
    """
    for threshold, label in _RISK_THRESHOLDS:
        if probability >= threshold:
            return label
    return "Low"


def _bin_probability(y_prob: np.ndarray) -> np.ndarray:
    """Bin continuous probabilities [0, 1] into *_N_BINS* integer classes.

    Bin edges: [0, 0.25), [0.25, 0.50), [0.50, 0.75), [0.75, 1.0]
    which map to labels  0 (Low), 1 (Moderate), 2 (High), 3 (Critical).
    """
    bins = np.linspace(0.0, 1.0, _N_BINS + 1)
    # np.digitize returns 1-based indices; subtract 1 and clip to valid range
    classes = np.digitize(y_prob, bins[1:-1])  # values in {0, 1, ..., _N_BINS-1}
    return classes.astype(np.int32)


def _build_estimator(model_type: str):
    """Instantiate the requested classifier."""
    model_type = model_type.lower().strip()

    if model_type == "xgboost":
        try:
            from xgboost import XGBClassifier

            return XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                use_label_encoder=False,
                eval_metric="mlogloss",
                random_state=42,
            )
        except ImportError:
            logger.warning(
                "xgboost is not installed -- falling back to "
                "GradientBoostingClassifier."
            )
            return GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            )

    if model_type == "random_forest":
        return RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

    if model_type == "gradient_boosting":
        return GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
        )

    raise ValueError(
        f"Unsupported model_type '{model_type}'. "
        f"Choose from: xgboost, random_forest, gradient_boosting."
    )


def _compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    n_classes: int,
) -> dict:
    """Compute accuracy, macro-F1, and macro-AUC."""
    acc = float(accuracy_score(y_true, y_pred))
    f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

    # AUC requires binarised true labels when n_classes > 2
    try:
        if n_classes == 2:
            auc = float(roc_auc_score(y_true, y_proba[:, 1]))
        else:
            y_true_bin = label_binarize(y_true, classes=np.arange(n_classes))
            # Trim or pad proba columns to match binarised label width
            proba_trimmed = y_proba[:, :n_classes]
            auc = float(
                roc_auc_score(
                    y_true_bin,
                    proba_trimmed,
                    multi_class="ovr",
                    average="macro",
                )
            )
    except ValueError:
        auc = None  # AUC undefined (e.g., single-class fold)

    return {"accuracy": round(acc, 4), "f1": round(f1, 4), "auc": round(auc, 4) if auc is not None else None}
