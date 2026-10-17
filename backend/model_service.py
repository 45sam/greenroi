
from pathlib import Path
import json
import logging
import math

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


from backend.gemini_service import explain_greenroi_result

# --------------------------------------------------
# 1. Configuration and paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "greenroi_energy_model_B.joblib"
)

INTERVENTIONS_PATH = (
    PROJECT_ROOT
    / "knowledge_base"
    / "greenroi_poc_interventions.csv"
)

EVIDENCE_PATH = (
    PROJECT_ROOT
    / "knowledge_base"
    / "greenroi_56_intervention_evidence.csv"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("greenroi")


# --------------------------------------------------
# 2. Load model and knowledge bases
# --------------------------------------------------

try:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Model file not found: {MODEL_PATH}"
        )

    model = joblib.load(MODEL_PATH)

    if not hasattr(model, "predict"):
        raise TypeError(
            "The loaded model does not support predict()."
        )

except Exception as exc:
    raise RuntimeError(
        f"Could not load ML model from {MODEL_PATH}: {exc}"
    ) from exc


try:
    if not INTERVENTIONS_PATH.is_file():
        raise FileNotFoundError(
            f"Intervention catalog not found: {INTERVENTIONS_PATH}"
        )

    interventions_df = pd.read_csv(INTERVENTIONS_PATH)

except Exception as exc:
    raise RuntimeError(
        f"Could not load intervention catalog: {exc}"
    ) from exc


try:
    if not EVIDENCE_PATH.is_file():
        raise FileNotFoundError(
            f"Evidence catalog not found: {EVIDENCE_PATH}"
        )

    evidence_df = pd.read_csv(EVIDENCE_PATH)

except Exception as exc:
    raise RuntimeError(
        f"Could not load intervention evidence: {exc}"
    ) from exc


logger.info("GreenROI ML model loaded successfully.")
logger.info("Intervention records loaded: %s", len(interventions_df))
logger.info("Evidence records loaded: %s", len(evidence_df))