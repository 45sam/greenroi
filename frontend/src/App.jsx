
import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Clock3,
  Cpu,
  Database,
  Factory,
  Gauge,
  Leaf,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Zap,
} from 'lucide-react'

const initialForm = {
  machine_type: 'CNC',
  machine_age_years: 7,
  rated_power_kw: 15,
  condition_score: 72,
  operating_hours: 8,
  vibration_mm_s: 3.5,
  motor_load_pct: 65,
  motor_efficiency_pct: 88,
  maintenance_hours: 1.5,
}

// Optional financial assumptions reviewed by Gemini.
const initialCostingForm = {
  intervention_investment_cost: '',
  implementation_cost: '',
  estimated_annual_energy_savings_kwh: '',
  estimated_annual_monetary_savings: '',
  electricity_tariff_per_kwh: '',
  annual_maintenance_cost: '',
  payback_period_years: '',
  roi_5_year_pct: '',
}

const costingFields = [
  { name: 'intervention_investment_cost', label: 'Intervention investment', unit: '₹', step: 0.01 },
  { name: 'implementation_cost', label: 'Implementation cost', unit: '₹', step: 0.01 },
  { name: 'estimated_annual_energy_savings_kwh', label: 'Estimated annual energy savings', unit: 'kWh/year', step: 0.01 },
  { name: 'estimated_annual_monetary_savings', label: 'Estimated annual monetary savings', unit: '₹/year', step: 0.01 },
  { name: 'electricity_tariff_per_kwh', label: 'Electricity tariff', unit: '₹/kWh', step: 0.01 },
  { name: 'annual_maintenance_cost', label: 'Annual maintenance cost', unit: '₹/year', step: 0.01 },
  { name: 'payback_period_years', label: 'Payback period', unit: 'years', step: 0.1 },
  { name: 'roi_5_year_pct', label: 'Five-year ROI', unit: '%', step: 0.1 },
]

const fields = [
  { name: 'machine_age_years', label: 'Machine age', unit: 'years', min: 0, max: 80, step: 1 },
  { name: 'rated_power_kw', label: 'Rated power', unit: 'kW', min: 0.01, max: 100000, step: 0.5 },
  { name: 'condition_score', label: 'Condition score', unit: '/ 100', min: 0, max: 100, step: 1 },
  { name: 'operating_hours', label: 'Operating hours', unit: 'hours/day', min: 0.01, max: 24, step: 0.5 },
  { name: 'vibration_mm_s', label: 'Vibration', unit: 'mm/s', min: 0, max: 1000, step: 0.1 },
  { name: 'motor_load_pct', label: 'Motor load', unit: '%', min: 0, max: 100, step: 1 },
  { name: 'motor_efficiency_pct', label: 'Motor efficiency', unit: '%', min: 0.01, max: 100, step: 1 },
  { name: 'maintenance_hours', label: 'Maintenance hours', unit: 'hours', min: 0, max: 10000, step: 0.5 },
]

function Metric({ icon: Icon, label, value, hint, tone = 'green' }) {
  return (
    <article className="metric-card">
      <div className={`metric-icon ${tone}`}>
        <Icon size={18} />
      </div>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-hint">{hint}</div>
    </article>
  )
}

function ProfileMetric({ icon: Icon, label, value, percent }) {
  return (
    <div className="profile-metric">
      <div className="profile-metric-heading">
        <span><Icon size={16} /> {label}</span>
        <strong>{value}</strong>
      </div>
      {percent !== undefined && (
        <div
          className="profile-track"
          role="progressbar"
          aria-label={label}
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="profile-track-fill"
            style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
          />
        </div>
      )}
    </div>
  )
}

function GeminiReportContent({ text }) {
  const lines = String(text)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  return (
    <div className="gemini-report-content">
      {lines.map((line, index) => {
        if (/^#{1,3}\s/.test(line)) {
          return (
            <h3 className="gemini-report-section-title" key={index}>
              {line.replace(/^#{1,3}\s*/, '')}
            </h3>
          )
        }

        if (/^[-*]\s/.test(line)) {
          return (
            <div className="gemini-report-bullet" key={index}>
              <span aria-hidden="true">•</span>
              <span>{line.replace(/^[-*]\s*/, '')}</span>
            </div>
          )
        }

        if (/^\d+[.)]\s/.test(line)) {
          return (
            <p className="gemini-report-numbered" key={index}>
              {line}
            </p>
          )
        }

        return <p key={index}>{line}</p>
      })}
    </div>
  )
}

function App() {
  const [form, setForm] = useState(initialForm)
  const [costingForm, setCostingForm] = useState(initialCostingForm)
  const [health, setHealth] = useState(null)
  const [kb, setKb] = useState(null)
  const [prediction, setPrediction] = useState(null)
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')
  const [lastRun, setLastRun] = useState(null)

  const apiCheck = useCallback(async () => {
    setChecking(true)

    try {
      const [healthRes, kbRes] = await Promise.all([
        fetch('/api/health'),
        fetch('/api/knowledge-base'),
      ])

      if (!healthRes.ok || !kbRes.ok) {
        throw new Error('Backend returned an unsuccessful response.')
      }

      setHealth(await healthRes.json())
      setKb(await kbRes.json())
      setError('')
    } catch (err) {
      setHealth(null)
      setKb(null)
      setError(
        `Cannot connect to GreenROI. Start FastAPI on port 8000. ${err.message}`
      )
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    apiCheck()
  }, [apiCheck])

  const ready = Boolean(
    health?.model_loaded &&
    health?.interventions_loaded &&
    health?.evidence_loaded
  )

  const updateField = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
  }

  const updateCostingField = (name, value) => {
    setCostingForm((current) => ({ ...current, [name]: value }))
  }

  const runPrediction = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setPrediction(null)
    setLastRun(null)

    try {
      const costingData = Object.fromEntries(
        Object.entries(costingForm)
          .filter(([, value]) => value !== '' && value !== null && value !== undefined)
          .map(([key, value]) => [key, Number(value)])
          .filter(([, value]) => Number.isFinite(value))
      )

      const payload = {
        machine_type: form.machine_type,
        ...Object.fromEntries(
          fields.map((field) => [field.name, Number(form[field.name])])
        ),
        // Optional supplied financial assumptions for Gemini's review.
        // These are passed through; this frontend does not calculate ROI.
        costing_data: costingData,
      }

      const response = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await response.json()

      if (!response.ok) {
        const detail =
          typeof data.detail === 'string'
            ? data.detail
            : JSON.stringify(data.detail ?? data)

        throw new Error(detail)
      }

      if (typeof data.prediction !== 'number' ||
          !Number.isFinite(data.prediction)) {
        throw new Error('The API did not return a valid numeric prediction.')
      }

      setPrediction(data)
      setLastRun(new Date())
    } catch (err) {
      setError(`Prediction failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const clearPrediction = () => {
    setPrediction(null)
    setLastRun(null)
    setError('')
  }

  const predictionDisplay =
    typeof prediction?.prediction === 'number'
      ? prediction.prediction.toLocaleString(undefined, {
          maximumFractionDigits: 2,
        })
      : '—'

  const predictionUnit = prediction?.prediction_unit || 'Unverified units'

  const profile = prediction?.machine_profile || form

  const unitConfirmed =
    prediction?.prediction_unit &&
    prediction.prediction_unit !== 'unverified'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Leaf size={23} strokeWidth={2.2} />
          </div>
          <div>
            <div className="brand-name">greenroi</div>
            <div className="brand-subtitle">ENERGY INTELLIGENCE</div>
          </div>
        </div>

        <div className="workspace-label">WORKSPACE</div>
        <div className="nav-item active">
          <Activity size={17} /> Overview <span className="nav-dot" />
        </div>
        <div className="nav-item">
          <Factory size={17} /> Machine assessment
        </div>
        <div className="nav-item">
          <Database size={17} /> Knowledge base
        </div>

        <div className="sidebar-bottom">
          <div className="sidebar-status">
            <span className={`status-dot ${ready ? 'online' : 'offline'}`} />
            <div>
              <strong>{ready ? 'Backend connected' : 'Backend unavailable'}</strong>
              <small>{ready ? 'Model and data loaded' : 'Check API connection'}</small>
            </div>
          </div>
          <div className="sidebar-foot">GREENROI · LOCAL PROTOTYPE</div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} /> <strong>Overview</strong>
          </div>
          <div className="topbar-right">
            <span className="environment-pill">
              <span /> LOCAL ENVIRONMENT
            </span>
            <div className="avatar">GR</div>
          </div>
        </header>

        <section className="page-heading">
          <div>
            <div className="eyebrow">
              <span className="eyebrow-line" />
              INDUSTRIAL SUSTAINABILITY PLATFORM
            </div>
            <h1>
              Energy intelligence,
              <br />
              <em>built for better decisions.</em>
            </h1>
            <p className="heading-copy">
              Turn machine parameters into interpretable model predictions
              and prepare for evidence-based energy interventions.
            </p>
          </div>

          <div className="heading-art" aria-hidden="true">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="art-core"><Leaf size={38} /></div>
            <div className="art-chip chip-one"><Zap size={15} /></div>
            <div className="art-chip chip-two"><Activity size={15} /></div>
          </div>
        </section>

        {error && (
          <div className="alert error-alert" role="alert">
            <AlertCircle size={18} />
            <span>{error}</span>
            <button
              className="alert-close"
              onClick={() => setError('')}
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        )}

        <section className="metrics-grid">
          <Metric
            icon={Cpu}
            label="ML MODEL"
            value={health?.model_loaded ? 'Loaded' : 'Not loaded'}
            hint="Saved model artifact"
            tone={health?.model_loaded ? 'green' : 'orange'}
          />
          <Metric
            icon={Database}
            label="INTERVENTION RECORDS"
            value={health?.intervention_rows ?? '—'}
            hint="Catalog rows available"
            tone="blue"
          />
          <Metric
            icon={CheckCircle2}
            label="EVIDENCE RECORDS"
            value={health?.evidence_rows ?? '—'}
            hint="Evidence rows available"
            tone="purple"
          />
          <Metric
            icon={Activity}
            label="LATEST PREDICTION"
            value={prediction ? 'Complete' : 'Not run'}
            hint={lastRun ? lastRun.toLocaleTimeString() : 'Awaiting assessment'}
            tone={prediction ? 'green' : 'orange'}
          />
        </section>

        <div className="content-grid">
          <section className="panel assessment-panel">
            <div className="panel-heading">
              <div>
                <div className="section-kicker">MODEL INFERENCE</div>
                <h2>Machine assessment</h2>
                <p>Enter machine parameters to generate a model prediction.</p>
              </div>
              <div className="panel-icon"><Cpu size={19} /></div>
            </div>

            <form onSubmit={runPrediction}>
              <label className="field-label" htmlFor="machine_type">
                Machine type
              </label>
              <select
                id="machine_type"
                value={form.machine_type}
                onChange={(e) => updateField('machine_type', e.target.value)}
                className="machine-select"
              >
                <option>CNC</option>
                <option>Conveyor</option>
                <option>Injection Molding</option>
                <option>Air Compressor</option>
                <option>Electric Motor</option>
                <option>Robotic Arm</option>
              </select>

              <div className="form-grid">
                {fields.map((field) => (
                  <label className="input-field" key={field.name}>
                    <span>{field.label}</span>
                    <div className="input-wrap">
                      <input
                        type="number"
                        required
                        min={field.min}
                        max={field.max}
                        step={field.step}
                        value={form[field.name]}
                        onChange={(e) => updateField(field.name, e.target.value)}
                      />
                      <small>{field.unit}</small>
                    </div>
                  </label>
                ))}
              </div>

              <section className="costing-section" aria-labelledby="costing-title">
                <div className="panel-heading">
                  <div>
                    <div className="section-kicker">OPTIONAL FINANCIAL INPUTS</div>
                    <h3 id="costing-title">Costing and ROI review</h3>
                    <p>
                      Add estimates you already have. Gemini will review the supplied
                      values and assumptions; it will not invent missing figures.
                    </p>
                  </div>
                </div>

                <div className="form-grid">
                  {costingFields.map((field) => (
                    <label className="input-field" key={field.name}>
                      <span>{field.label}</span>
                      <div className="input-wrap">
                        <input
                          type="number"
                          min="0"
                          step={field.step}
                          value={costingForm[field.name]}
                          onChange={(e) => updateCostingField(field.name, e.target.value)}
                          placeholder="Optional"
                        />
                        <small>{field.unit}</small>
                      </div>
                    </label>
                  ))}
                </div>
                <p className="form-note">
                  Financial values are optional. Only filled fields are sent to the backend.
                  ROI and payback are not calculated by this form.
                </p>
              </section>

              <div className="form-footer">
                <div className="form-note">
                  <CircleHelp size={15} />
                  Use real machine readings when available.
                </div>
                <button
                  className="primary-button"
                  type="submit"
                  disabled={loading || !ready}
                >
                  {loading ? (
                    <>
                      <LoaderCircle className="spin" size={17} />
                      Generating report...
                    </>
                  ) : (
                    <>Run prediction <ArrowUpRight size={17} /></>
                  )}
                </button>
              </div>

              {!ready && (
                <p className="disabled-hint">
                  Prediction is disabled until the backend health check passes.
                </p>
              )}
            </form>
          </section>

          <section className="panel result-panel">
            <div className="panel-heading result-heading">
              <div>
                <div className="section-kicker">ENERGY INTELLIGENCE</div>
                <h2>Prediction report</h2>
                <p>Interpret your saved model's output.</p>
              </div>
              <div className="result-symbol"><Zap size={21} /></div>
            </div>

            {prediction ? (
              <>
                <div className="result-status">
                  <span className="status-dot online" />
                  PREDICTION GENERATED
                </div>

                <div className="prediction-hero">
                  <div className="prediction-hero-label">
                    Estimated model output
                  </div>
                  <div className="prediction-hero-value">
                    {predictionDisplay}
                  </div>
                  <div className="prediction-hero-unit">
                    {predictionUnit}
                  </div>
                  <div className="prediction-hero-caption">
                    {prediction.machine_type || form.machine_type}
                    {' · '}Model inference
                  </div>
                </div>

                <div className="prediction-summary-card">
                  <div className="summary-icon">
                    <Sparkles size={18} />
                  </div>
                  <div>
                    <strong>What does this prediction mean?</strong>
                    <p>
                      {prediction.interpretation ||
                        'The model generated an estimate from the supplied machine parameters. Confirm the target units and validate the result against measured data.'}
                    </p>
                  </div>
                </div>

                <h3 className="insight-subtitle">Machine operating profile</h3>

                <div className="profile-metrics">
                  <ProfileMetric
                    icon={Activity}
                    label="Machine condition"
                    value={`${profile.condition_score}/100`}
                    percent={Number(profile.condition_score)}
                  />
                  <ProfileMetric
                    icon={Gauge}
                    label="Motor load"
                    value={`${profile.motor_load_pct}%`}
                    percent={Number(profile.motor_load_pct)}
                  />
                  <ProfileMetric
                    icon={Zap}
                    label="Motor efficiency"
                    value={`${profile.motor_efficiency_pct}%`}
                    percent={Number(profile.motor_efficiency_pct)}
                  />
                  <ProfileMetric
                    icon={Clock3}
                    label="Operating hours"
                    value={`${profile.operating_hours} h/day`}
                  />
                </div>

                <div className="snapshot-grid">
                  <div className="snapshot-item">
                    <Cpu size={16} />
                    <span>Rated power</span>
                    <strong>{profile.rated_power_kw} kW</strong>
                  </div>
                  <div className="snapshot-item">
                    <Clock3 size={16} />
                    <span>Machine age</span>
                    <strong>{profile.machine_age_years} years</strong>
                  </div>
                  <div className="snapshot-item">
                    <Activity size={16} />
                    <span>Vibration</span>
                    <strong>{profile.vibration_mm_s} mm/s</strong>
                  </div>
                  <div className="snapshot-item">
                    <RefreshCw size={16} />
                    <span>Maintenance</span>
                    <strong>{profile.maintenance_hours} hours</strong>
                  </div>
                </div>

                <div className="validation-note">
                  <ShieldCheck size={17} />
                  <span>
                    {prediction.validation?.message ||
                      'This is a model output, not a verified measurement. Validate against independent measured data.'}
                  </span>
                </div>

                <section className="gemini-report-card" aria-labelledby="gemini-report-title">
                  <div className="gemini-report-heading">
                    <div className="gemini-report-icon">
                      <Sparkles size={19} />
                    </div>
                    <div>
                      <div className="section-kicker">AI-GENERATED ANALYSIS</div>
                      <h3 id="gemini-report-title">Gemini prediction report</h3>
                      <p>
                        A readable explanation based on the machine inputs and
                        results returned by the GreenROI backend.
                      </p>
                    </div>
                  </div>

                  {prediction.report ? (
                    <div
                      className="gemini-report-scroll"
                      role="region"
                      aria-label="Scrollable Gemini prediction report"
                      tabIndex={0}
                      style={{
                        maxHeight: '420px',
                        overflowY: 'auto',
                        overflowX: 'hidden',
                        paddingRight: '10px',
                        overscrollBehavior: 'contain',
                      }}
                    >
                      <GeminiReportContent text={prediction.report} />
                    </div>
                  ) : (
                    <div className="gemini-report-unavailable" role="status">
                      <CircleHelp size={18} />
                      <div>
                        <strong>Gemini report not returned</strong>
                        <p>
                          The model prediction succeeded, but the API response
                          did not include a <code>report</code> field. Check that
                          your FastAPI endpoint calls
                          <code> explain_greenroi_result()</code> and returns
                          its result as <code>report</code>.
                        </p>
                      </div>
                    </div>
                  )}
                </section>

                {!unitConfirmed && (
                  <div className="result-callout">
                    <div className="callout-icon"><CircleHelp size={17} /></div>
                    <div>
                      <strong>Confirm prediction units</strong>
                      <p>
                        The training target and its units have not been
                        confirmed. Monthly consumption, annual consumption,
                        energy savings and ROI are therefore not calculated
                        from this number.
                      </p>
                    </div>
                  </div>
                )}

                <button className="secondary-button" onClick={clearPrediction}>
                  Clear prediction <ArrowDownRight size={16} />
                </button>
              </>
            ) : (
              <div className="empty-result">
                <div className="empty-illustration"><Activity size={28} /></div>
                <h3>Your energy insights start here</h3>
                <p>
                  Submit your machine parameters to generate a model prediction,
                  machine profile, and Gemini-generated explanation.
                </p>
                <div className="empty-checks">
                  <div><CheckCircle2 size={15} /> Machine parameters</div>
                  <div><CheckCircle2 size={15} /> Saved ML model</div>
                  <div><CheckCircle2 size={15} /> Gemini prediction report</div>
                </div>
              </div>
            )}

            <div className="result-bottom">
              <div><span className="mini-dot" /> API endpoint</div>
              <code>POST /predict</code>
            </div>
          </section>
        </div>

        <section className="panel system-panel">
          <div className="system-header">
            <div>
              <div className="section-kicker">SYSTEM STATUS</div>
              <h2>Connected components</h2>
            </div>
            <button
              className="refresh-button"
              onClick={apiCheck}
              disabled={checking}
            >
              {checking
                ? <LoaderCircle size={15} className="spin" />
                : <RefreshCw size={15} />}
              Refresh status
            </button>
          </div>

          <div className="system-grid">
            <div className="system-item">
              <div className="system-item-icon"><Cpu size={18} /></div>
              <div className="system-item-copy">
                <strong>FastAPI backend</strong>
                <span>Local API · port 8000</span>
              </div>
              <span className={`system-state ${health ? 'ok' : 'bad'}`}>
                {health ? 'Connected' : 'Offline'}
              </span>
            </div>

            <div className="system-item">
              <div className="system-item-icon"><Database size={18} /></div>
              <div className="system-item-copy">
                <strong>Intervention knowledge base</strong>
                <span>{kb?.interventions?.columns?.length ?? 0} columns detected</span>
              </div>
              <span className={`system-state ${health?.interventions_loaded ? 'ok' : 'bad'}`}>
                {health?.interventions_loaded ? 'Loaded' : 'Unavailable'}
              </span>
            </div>

            <div className="system-item">
              <div className="system-item-icon"><Activity size={18} /></div>
              <div className="system-item-copy">
                <strong>Evidence catalog</strong>
                <span>{kb?.evidence?.columns?.length ?? 0} columns detected</span>
              </div>
              <span className={`system-state ${health?.evidence_loaded ? 'ok' : 'bad'}`}>
                {health?.evidence_loaded ? 'Loaded' : 'Unavailable'}
              </span>
            </div>
          </div>

          <div className="roadmap-note">
            <div className="roadmap-mark"><Leaf size={17} /></div>
            <div>
              <strong>Next build milestone</strong>
              <span>
                Gemini report display is connected to the API response.
                Connect the intervention engine and ROI calculations to include
                evidence-based recommendations and financial results.
              </span>
            </div>
            <ChevronRight size={18} />
          </div>
        </section>

        <footer className="footer">
          <span>© GreenROI · Local prototype</span>
          <span>Predictions are model outputs, not verified energy savings.</span>
        </footer>
      </main>
    </div>
  )
}

export default App
