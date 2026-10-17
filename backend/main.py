
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


# --------------------------------------------------
# 3. Create FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="GreenROI Backend",
    description=(
        "Industrial energy prediction and intervention "
        "decision-support API with Gemini-generated reports."
    ),
    version="0.3.0",
)


# --------------------------------------------------
# 4. Machine input validation
# --------------------------------------------------

class MachineInput(BaseModel):
    machine_type: str = Field(min_length=1)
    machine_age_years: float = Field(ge=0, le=100)
    rated_power_kw: float = Field(gt=0)
    condition_score: float = Field(ge=0, le=100)
    operating_hours: float = Field(gt=0, le=24)
    vibration_mm_s: float = Field(ge=0)
    motor_load_pct: float = Field(ge=0, le=100)
    motor_efficiency_pct: float = Field(gt=0, le=100)
    maintenance_hours: float = Field(ge=0)

    # Cost and ROI values supplied by the frontend
    costing_data: dict = Field(default_factory=dict)
    
# --------------------------------------------------
# 5. Helper functions
# --------------------------------------------------

def dataframe_to_records(
    dataframe: pd.DataFrame,
    limit: int,
) -> list[dict]:
    """
    Convert a limited number of CSV rows to JSON-safe records.
    Missing CSV values become JSON null values.
    """
    records_json = dataframe.head(limit).to_json(
        orient="records",
        date_format="iso",
    )

    return json.loads(records_json)


def prepare_model_features(
    machine_data: dict,
) -> pd.DataFrame:
    """
    Prepare machine inputs in the feature order expected
    by the saved model.
    """
    if hasattr(model, "feature_names_in_"):
        feature_columns = list(model.feature_names_in_)

        missing_features = [
            column
            for column in feature_columns
            if column not in machine_data
        ]

        if missing_features:
            raise ValueError(
                "Required model features are missing: "
                f"{missing_features}"
            )

        return pd.DataFrame(
            [[machine_data[column] for column in feature_columns]],
            columns=feature_columns,
        )

    # Fallback when the model does not expose feature_names_in_.
    return pd.DataFrame([machine_data])


# --------------------------------------------------
# 6. Health and knowledge-base endpoints
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "GreenROI backend is running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "interventions_loaded": not interventions_df.empty,
        "evidence_loaded": not evidence_df.empty,
        "intervention_rows": len(interventions_df),
        "evidence_rows": len(evidence_df),
    }


@app.get("/knowledge-base")
def knowledge_base():
    return {
        "interventions": {
            "rows": len(interventions_df),
            "columns": interventions_df.columns.tolist(),
        },
        "evidence": {
            "rows": len(evidence_df),
            "columns": evidence_df.columns.tolist(),
        },
    }


# --------------------------------------------------
# 7. Prediction endpoint with Gemini report
# --------------------------------------------------

@app.post("/predict")
def predict(machine: MachineInput):
    # Step 1: Convert validated inputs to a dictionary.
    machine_data = machine.model_dump()

    # Step 2: Run the ML prediction.
    try:
        features = prepare_model_features(machine_data)
        model_output = model.predict(features)

        if len(model_output) != 1:
            raise ValueError(
                "Expected exactly one prediction for one machine."
            )

        prediction = float(model_output[0])

        if not math.isfinite(prediction) or prediction < 0:
            raise ValueError(
                "The model returned an invalid prediction."
            )

    except Exception as exc:
        logger.exception("GreenROI model prediction failed.")

        raise HTTPException(
            status_code=500,
            detail=(
                "Prediction failed. Check model feature names, "
                f"preprocessing, and input schema. Details: {exc}"
            ),
        ) from exc

    # Step 3: Prepare knowledge-base context for Gemini.
    try:
        intervention_records = dataframe_to_records(
            interventions_df,
            limit=10,
        )

        evidence_records = dataframe_to_records(
            evidence_df,
            limit=20,
        )

    except Exception:
        logger.exception(
            "Could not prepare GreenROI knowledge-base context."
        )

        intervention_records = []
        evidence_records = []

    # Step 4: Explicitly indicate that ROI has not been calculated.
    # Replace this placeholder when your ROI engine is connected.
    roi_results = {
        "status": "not_calculated",
        "message": (
            "ROI, energy savings, implementation costs, and "
            "payback have not yet been calculated by the application."
        ),
    }

    # Include evidence alongside the intervention catalog.
    # These are catalog records, not machine-specific recommendations.
    interventions_for_report = [
        {
            "record_type": "catalog_entry",
            **record,
        }
        for record in intervention_records
    ]

    evidence_for_report = evidence_records

    # Step 5: Generate the Gemini explanation.
    # Keep the ML prediction even if the Gemini service fails.
    try:
        report = explain_greenroi_result(
            machine_data=machine_data,
            predicted_energy_kwh=prediction,
            roi_results={
                **roi_results,
                "available_evidence_records": evidence_for_report,
            },
            interventions=interventions_for_report,
        )

        if not isinstance(report, str) or not report.strip():
            raise ValueError(
                "Gemini returned an empty report."
            )

        report = report.strip()
        report_status = "returned"

    except Exception:
        logger.exception(
            "Gemini report generation failed."
        )

        report = (
            "The ML prediction succeeded, but Gemini could not "
            "generate the report. Check GEMINI_API_KEY, the "
            "configured model name, network access, and backend logs."
        )
        report_status = "failed"

    # Step 6: Return the prediction and report to React.
    return {
        "status": "success",
        "machine_type": machine.machine_type,
        "prediction": prediction,

        # Do not claim units until the training target is verified.
        "prediction_unit": "unverified",
        "prediction_period": "unverified",

        "interpretation": (
            "The model generated an estimate from the supplied "
            "machine parameters. Confirm the training target and "
            "validate the result against measured data."
        ),

        "machine_profile": machine_data,

        "validation": {
            "measured_energy_provided": False,
            "accuracy_verified": False,
            "message": (
                "This is a model prediction, not a verified "
                "energy measurement."
            ),
        },

        # React can render this field directly.
        "report": report,
        "report_status": report_status,

        # Transparently expose what has not been calculated.
        "roi_status": "not_calculated",
        "intervention_catalog_records": len(intervention_records),
        "evidence_records_provided": len(evidence_for_report),
    }
