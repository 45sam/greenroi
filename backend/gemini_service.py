import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

logger = logging.getLogger("greenroi.gemini")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_MODEL = "gemini-3.8-flash"


def _compact_records(records, limit=3):
    """Keep prompt context small so the report stays focused and faster."""
    if not isinstance(records, list):
        return []
    return records[:limit]


def explain_greenroi_result(
    machine_data: dict,
    predicted_energy_kwh: float,
    roi_results: dict,
    interventions: list,
) -> str:
    """
    Generate a concise, decision-focused GreenROI report from supplied data.
    Financial values are reviewed as supplied; this function does not calculate ROI.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from the project-root .env file."
        )

    roi_results = roi_results if isinstance(roi_results, dict) else {}
    evidence_records = _compact_records(
        roi_results.get("available_evidence_records", []), limit=4
    )
    costing_data = roi_results.get("costing_data", {})

    # Do not send a large catalog dump: give Gemini a small, relevant context.
    compact_interventions = _compact_records(interventions, limit=4)

    context = {
        "machine_inputs": machine_data,
        "model_prediction": {
            "value": predicted_energy_kwh,
            "unit": "unverified",
            "period": "unverified",
            "meaning": "Model estimate, not a measured energy reading.",
        },
        "financial_data_supplied_by_user": costing_data or {},
        "financial_data_status": roi_results.get("status", "not_calculated"),
        "financial_notes": roi_results.get("message", ""),
        "intervention_catalog_examples": compact_interventions,
        "evidence_examples": evidence_records,
    }

    prompt = f"""
You are GreenROI's industrial energy analyst. Write a useful, readable report for a
plant manager who needs to understand what the machine readings could mean in daily
factory operations.

The report MUST contain at least 3 substantive paragraphs of explanation, not just
a short sentence or a list. Aim for 250–350 words. Explain real-world implications
in clear, practical language, while distinguishing facts from hypotheses.

Use these headings in this order:
## Executive summary
## What this could mean on the factory floor
## Financial review
## Risks and missing information
## Recommended next steps

CONTENT REQUIREMENTS:
1. Executive summary: 2–3 sentences that identify the main observations and what
   should be checked first.
2. Factory-floor explanation: write 2–3 full paragraphs. Explain how the supplied
   machine age, condition score, motor load, motor efficiency, operating hours,
   vibration, and maintenance hours could relate to real operations. For example,
   explain that partial loading may mean the machine is not being used near its
   intended capacity, but do not claim this necessarily wastes energy without
   measurement. Explain that vibration can justify checking alignment, bearings,
   mounting, and maintenance history, but do not diagnose a fault from vibration
   alone. Explain what an operator or maintenance engineer could observe or measure.
3. Financial review: discuss only the costing values actually supplied. Explain
   their practical meaning, assumptions, and limitations. If no financial data was
   supplied, say that financial viability cannot yet be assessed and name the most
   important missing values.
4. Risks and missing information: clearly identify unknown prediction units/time
   period, missing metered energy readings, uncertain baselines, and any missing
   cost or operating assumptions that affect the conclusion.
5. Recommended next steps: provide 3–5 prioritized, actionable checks or measurements
   that a real plant team could perform.

STRICT ACCURACY RULES:
- Use only supplied values and reasonable general engineering explanations.
- Never invent machine readings, thresholds, faults, energy consumption, energy
  savings, costs, payback, ROI, emissions reductions, or measured results.
- The model prediction is an estimate. Its unit and time period are unverified;
  never call it measured energy consumption or verified savings.
- Treat catalog/evidence rows as reference material, not confirmed machine-specific
  recommendations. Do not claim an intervention is installed or validated.
- Financial values are supplied assumptions. Review them but do not invent, modify,
  or silently calculate missing values.
- Use cautious wording such as "could indicate", "worth checking", and "to confirm".
  Do not turn a possible explanation into a diagnosis.
- Do not merely restate the input values. Explain why each important value matters
  in real operation and what evidence would confirm the interpretation.
- Plain Markdown. Write full paragraphs; bullets may be used only for the final
  recommended actions. Do not add greetings or generic sustainability filler.

DATA:
{json.dumps(context, ensure_ascii=False, default=str)}
""".strip()

    start_time = time.perf_counter()
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4900,
            ),
        )

        report = getattr(response, "text", None)
        if not report or not report.strip():
            raise RuntimeError("Gemini returned an empty report.")

        return report.strip()

    except Exception:
        logger.exception("Gemini report generation failed.")
        raise

    finally:
        logger.info(
            "Gemini request completed in %.2f seconds",
            time.perf_counter() - start_time,
        )