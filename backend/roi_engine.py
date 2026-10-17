"""
GreenROI ROI Engine
-------------------
Calculates energy savings, financial savings, payback period,
and five-year ROI for an intervention.

Important:
- Energy-saving percentages are estimates, not guarantees.
- Missing or simulated catalog values must be disclosed.
- Baseline daily energy should come from measured data or Model B.
"""

from pathlib import Path
import math

import pandas as pd


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

DEFAULT_CATALOG_PATH = (
    BASE_DIR
    / "knowledge_base"
    / "greenroi_poc_interventions.csv"
)

# Illustrative PoC assumptions only.
# Replace these with evidence-backed ranges before deployment.
FALLBACK_RANGES = {
    "CNC": (5.0, 15.0),
    "Conveyor": (5.0, 15.0),
    "Injection Molding": (5.0, 15.0),
    "Air Compressor": (5.0, 20.0),
    "Electric Motor": (5.0, 12.0),
    "Robotic Arm": (5.0, 15.0),
}

MACHINE_ALIASES = {
    "cnc": "CNC",
    "cnc machine": "CNC",
    "conveyor": "Conveyor",
    "conveyor belt": "Conveyor",
    "injection molding": "Injection Molding",
    "injection molding machine": "Injection Molding",
    "injection moulding": "Injection Molding",
    "injection moulding machine": "Injection Molding",
    "robotic arm": "Robotic Arm",
    "robot arm": "Robotic Arm",
    "air compressor": "Air Compressor",
    "compressor": "Air Compressor",
    "electric motor": "Electric Motor",
    "motor": "Electric Motor",
}


# ---------------------------------------------------------
# VALIDATION AND COLUMN HELPERS
# ---------------------------------------------------------

def normalize_machine(machine: str) -> str:
    """Normalize supported machine names."""

    key = str(machine).strip().lower()

    if key not in MACHINE_ALIASES:
        raise ValueError(
            f"Unsupported machine: {machine!r}. "
            f"Supported machines: {sorted(set(MACHINE_ALIASES.values()))}"
        )

    return MACHINE_ALIASES[key]


def validate_number(
    value,
    name: str,
    minimum: float = 0.0,
) -> float:
    """Validate a finite numeric input."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be numeric.")

    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite.")

    if number < minimum:
        raise ValueError(f"{name} must be >= {minimum}.")

    return number


def find_column(
    df: pd.DataFrame,
    candidates: list,
    required: bool = True,
):
    """Find a column while tolerating spaces and case differences."""

    normalized = {
        str(col).strip().lower().replace(" ", "_"): col
        for col in df.columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower().replace(" ", "_")

        if key in normalized:
            return normalized[key]

    if required:
        raise ValueError(
            f"Could not find any of {candidates}. "
            f"Available columns: {list(df.columns)}"
        )

    return None


def parse_optional_number(value):
    """Return a finite non-negative number, or None if missing."""

    if pd.isna(value):
        return None

    try:
        cleaned = (
            str(value)
            .strip()
            .replace(",", "")
            .replace("%", "")
        )

        if cleaned.lower() in {
            "", "nan", "none", "null", "n/a", "na", "-"
        }:
            return None

        number = float(cleaned)

        if not math.isfinite(number) or number < 0:
            return None

        return number

    except (TypeError, ValueError):
        return None


def normalize_percentage(value: float) -> float:
    """
    Interpret values between 0 and 1 as fractions.
    Example: 0.10 -> 10%.

    Use percentage points such as 10 for 10% otherwise.
    """

    if 0 < value <= 1:
        return value * 100

    return value


# ---------------------------------------------------------
# CATALOG LOADING
# ---------------------------------------------------------

def load_intervention_catalog(
    catalog_path=DEFAULT_CATALOG_PATH,
) -> pd.DataFrame:
    """Load the intervention catalog from CSV."""

    path = Path(catalog_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Intervention catalog not found: {path}"
        )

    catalog = pd.read_csv(path)

    if catalog.empty:
        raise ValueError("The intervention catalog is empty.")

    return catalog


# ---------------------------------------------------------
# INTERVENTION LOOKUP
# ---------------------------------------------------------

def get_intervention(
    machine: str,
    intervention_name: str,
    catalog: pd.DataFrame,
) -> dict:
    """Find an intervention for a specific machine."""

    machine = normalize_machine(machine)

    machine_col = find_column(
        catalog,
        ["machine_type", "machine", "machine_category"],
    )

    intervention_col = find_column(
        catalog,
        [
            "intervention",
            "intervention_name",
            "recommendation",
            "action",
        ],
    )

    def safe_normalize(value):
        try:
            return normalize_machine(value)
        except ValueError:
            return str(value).strip()

    machine_rows = catalog[
        catalog[machine_col].apply(safe_normalize) == machine
    ]

    matches = machine_rows[
        machine_rows[intervention_col]
        .astype(str)
        .str.strip()
        .str.casefold()
        == str(intervention_name).strip().casefold()
    ]

    if matches.empty:
        available = (
            machine_rows[intervention_col]
            .dropna()
            .astype(str)
            .tolist()
        )

        raise ValueError(
            f"Intervention {intervention_name!r} was not found "
            f"for {machine}. Available interventions: {available[:30]}"
        )

    item = matches.iloc[0]

    low_col = find_column(
        catalog,
        [
            "energy_saving_pct_low",
            "energy_savings_pct_low",
            "energy_reduction_pct_low",
            "energy_saving_low_pct",
        ],
        required=False,
    )

    high_col = find_column(
        catalog,
        [
            "energy_saving_pct_high",
            "energy_savings_pct_high",
            "energy_reduction_pct_high",
            "energy_saving_high_pct",
        ],
        required=False,
    )

    cost_col = find_column(
        catalog,
        [
            "investment_inr",
            "investment",
            "investment_cost_inr",
            "implementation_cost_inr",
            "cost_inr",
        ],
        required=False,
    )

    low = (
        parse_optional_number(item[low_col])
        if low_col else None
    )

    high = (
        parse_optional_number(item[high_col])
        if high_col else None
    )

    source = "catalog"

    if low is None and high is None:
        low, high = FALLBACK_RANGES[machine]
        source = "illustrative_poc_fallback"

    elif low is None:
        low = high
        source = "catalog_single_bound"

    elif high is None:
        high = low
        source = "catalog_single_bound"

    low = normalize_percentage(low)
    high = normalize_percentage(high)

    if high < low:
        raise ValueError(
            "The upper energy-saving percentage cannot be "
            "below the lower percentage."
        )

    if high > 100:
        raise ValueError(
            "Energy-saving percentage cannot exceed 100%."
        )

    investment = (
        parse_optional_number(item[cost_col])
        if cost_col else None
    )

    return {
        "machine_type": machine,
        "intervention": str(item[intervention_col]).strip(),
        "energy_saving_low_pct": low,
        "energy_saving_high_pct": high,
        "catalog_investment_inr": investment,
        "saving_range_source": source,
    }


# ---------------------------------------------------------
# ROI CALCULATION
# ---------------------------------------------------------

def calculate_roi(
    baseline_daily_energy_kwh: float,
    operating_days_per_year: float,
    tariff_inr_per_kwh: float,
    investment_inr: float,
    energy_saving_low_pct: float,
    energy_saving_high_pct: float,
    intervention_name: str = "Unspecified intervention",
    machine_type: str = "Unspecified",
    measured_daily_energy_kwh=None,
    annual_maintenance_cost_inr: float = 0.0,
    analysis_years: int = 5,
    saving_range_source: str = "user_supplied",
) -> dict:
    """
    Calculate a simple energy-only ROI.

    The baseline is daily kWh from Model B or a measurement.
    Investment is a one-time upfront cost.
    Annual maintenance is an additional recurring cost.

    Payback uses annual net savings.
    ROI uses cumulative net savings over analysis_years.
    """

    predicted_kwh = validate_number(
        baseline_daily_energy_kwh,
        "Baseline daily energy",
    )

    if measured_daily_energy_kwh is not None:
        daily_kwh = validate_number(
            measured_daily_energy_kwh,
            "Measured daily energy",
        )
        energy_basis = "measured"
    else:
        daily_kwh = predicted_kwh
        energy_basis = "model_prediction"

    operating_days = validate_number(
        operating_days_per_year,
        "Operating days per year",
        minimum=1,
    )

    if operating_days > 366:
        raise ValueError("Operating days cannot exceed 366.")

    tariff = validate_number(
        tariff_inr_per_kwh,
        "Electricity tariff",
    )

    investment = validate_number(
        investment_inr,
        "Investment",
    )

    maintenance = validate_number(
        annual_maintenance_cost_inr,
        "Annual maintenance cost",
    )

    if (
        not isinstance(analysis_years, int)
        or isinstance(analysis_years, bool)
        or analysis_years < 1
        or analysis_years > 50
    ):
        raise ValueError("Analysis years must be an integer from 1 to 50.")

    low_pct = normalize_percentage(
        validate_number(energy_saving_low_pct, "Low saving percentage")
    )

    high_pct = normalize_percentage(
        validate_number(energy_saving_high_pct, "High saving percentage")
    )

    if low_pct > high_pct:
        raise ValueError(
            "Low saving percentage cannot exceed high saving percentage."
        )

    if high_pct > 100:
        raise ValueError("Energy savings cannot exceed 100%.")

    # Baseline annual energy and energy cost.
    annual_energy_kwh = daily_kwh * operating_days
    annual_energy_cost = annual_energy_kwh * tariff

    # Gross annual energy savings.
    annual_kwh_saving_low = annual_energy_kwh * low_pct / 100
    annual_kwh_saving_high = annual_energy_kwh * high_pct / 100

    gross_saving_low = annual_kwh_saving_low * tariff
    gross_saving_high = annual_kwh_saving_high * tariff

    # Net savings account for the supplied annual maintenance cost.
    net_saving_low = gross_saving_low - maintenance
    net_saving_high = gross_saving_high - maintenance

    def payback_months(annual_net_saving):
        if investment == 0:
            return 0.0

        if annual_net_saving <= 0:
            return None

        return investment / annual_net_saving * 12

    payback_best = payback_months(net_saving_high)
    payback_worst = payback_months(net_saving_low)

    # Simple cumulative ROI; assumes annual savings remain constant.
    total_net_low = net_saving_low * analysis_years
    total_net_high = net_saving_high * analysis_years

    roi_low = (
        (total_net_low - investment) / investment * 100
        if investment > 0 else None
    )

    roi_high = (
        (total_net_high - investment) / investment * 100
        if investment > 0 else None
    )

    return {
        "machine_type": machine_type,
        "intervention": intervention_name,
        "energy_basis_for_roi": energy_basis,
        "saving_range_source": saving_range_source,
        "baseline_daily_energy_kwh": daily_kwh,
        "annual_energy_kwh": annual_energy_kwh,
        "tariff_inr_per_kwh": tariff,
        "annual_energy_cost_inr": annual_energy_cost,
        "energy_saving_low_pct": low_pct,
        "energy_saving_high_pct": high_pct,
        "annual_energy_saving_low_kwh": annual_kwh_saving_low,
        "annual_energy_saving_high_kwh": annual_kwh_saving_high,
        "annual_gross_savings_low_inr": gross_saving_low,
        "annual_gross_savings_high_inr": gross_saving_high,
        "annual_maintenance_cost_inr": maintenance,
        "annual_net_savings_low_inr": net_saving_low,
        "annual_net_savings_high_inr": net_saving_high,
        "investment_inr": investment,
        "payback_best_case_months": payback_best,
        "payback_worst_case_months": payback_worst,
        "analysis_years": analysis_years,
        "cumulative_net_savings_low_inr": total_net_low,
        "cumulative_net_savings_high_inr": total_net_high,
        "roi_low_pct": roi_low,
        "roi_high_pct": roi_high,
        "is_profitable_in_low_case": total_net_low > investment,
        "is_profitable_in_high_case": total_net_high > investment,
        "disclaimer": (
            "Estimates depend on the supplied baseline, tariff, "
            "investment, maintenance cost, and savings assumptions. "
            "Validate with measured operating data."
        ),
    }


# ---------------------------------------------------------
# CONVENIENCE FUNCTION: CATALOG + ROI
# ---------------------------------------------------------

def evaluate_intervention(
    machine_type: str,
    intervention_name: str,
    baseline_daily_energy_kwh: float,
    operating_days_per_year: float,
    tariff_inr_per_kwh: float,
    investment_inr=None,
    measured_daily_energy_kwh=None,
    annual_maintenance_cost_inr: float = 0.0,
    analysis_years: int = 5,
    catalog=None,
    catalog_path=DEFAULT_CATALOG_PATH,
) -> dict:
    """
    Look up an intervention and calculate its ROI.

    Explicit investment_inr overrides the catalog investment.
    If neither exists, fail rather than silently invent a cost.
    """

    if catalog is None:
        catalog = load_intervention_catalog(catalog_path)

    intervention = get_intervention(
        machine_type,
        intervention_name,
        catalog,
    )

    investment = investment_inr

    if investment is None:
        investment = intervention["catalog_investment_inr"]

    if investment is None:
        raise ValueError(
            f"No investment cost was supplied for {intervention_name!r}. "
            "Provide investment_inr or add a cost to the catalog."
        )

    return calculate_roi(
        baseline_daily_energy_kwh=baseline_daily_energy_kwh,
        operating_days_per_year=operating_days_per_year,
        tariff_inr_per_kwh=tariff_inr_per_kwh,
        investment_inr=investment,
        energy_saving_low_pct=intervention[
            "energy_saving_low_pct"
        ],
        energy_saving_high_pct=intervention[
            "energy_saving_high_pct"
        ],
        intervention_name=intervention_name,
        machine_type=intervention["machine_type"],
        measured_daily_energy_kwh=measured_daily_energy_kwh,
        annual_maintenance_cost_inr=annual_maintenance_cost_inr,
        analysis_years=analysis_years,
        saving_range_source=intervention["saving_range_source"],
    )
