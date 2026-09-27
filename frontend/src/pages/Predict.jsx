import React, { useState } from 'react';
import { Brain, AlertTriangle, TrendingUp, TrendingDown, Loader2, Info } from 'lucide-react';
import { predict } from '../api/client';

const INITIAL_FORM = {
  age_years: '',
  gender: '',
  height: '',
  weight: '',
  systolic_bp: '',
  diastolic_bp: '',
  cholesterol: '',
  glucose: '',
  smoking: '',
  alcohol: '',
  physical_activity: '',
};

const CHOL_OPTIONS = [
  { value: 1, label: 'Normal' },
  { value: 2, label: 'Above Normal' },
  { value: 3, label: 'Well Above Normal' },
];

const BINARY_OPTIONS = [
  { value: 0, label: 'No' },
  { value: 1, label: 'Yes' },
];

function Spinner() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="spinner w-10 h-10" />
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
    </div>
  );
}

export default function Predict() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (field) => (e) => {
    const val = e.target.value;
    setForm((f) => ({ ...f, [field]: val === '' ? '' : Number(val) }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload = {
        age_years: Number(form.age_years),
        gender: Number(form.gender),
        height: Number(form.height),
        weight: Number(form.weight),
        systolic_bp: Number(form.systolic_bp),
        diastolic_bp: Number(form.diastolic_bp),
        cholesterol: Number(form.cholesterol),
        glucose: Number(form.glucose),
        smoking: Number(form.smoking),
        alcohol: Number(form.alcohol),
        physical_activity: Number(form.physical_activity),
      };

      const res = await predict(payload);
      setResult(res.data?.data || res.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (detail?.message) {
        setError(detail.message);
      } else {
        setError('Prediction failed. Please check your inputs and try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const isPositive = result?.prediction === 1;
  const probability = result?.probability ?? 0;
  const probabilityPct = (probability * 100).toFixed(1);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">AI <span className="gradient-text">Prediction</span></h1>
        <p className="section-sub">Cardiovascular disease risk assessment using XGBoost ML model</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Form */}
        <div className="card p-6">
          <h3 className="font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Brain size={18} className="text-primary-400" />
            Patient Parameters
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Age (years)">
                <input type="number" className="input" placeholder="e.g. 55" min="1" max="120"
                  value={form.age_years} onChange={handleChange('age_years')} required />
              </Field>
              <Field label="Gender">
                <select className="select" value={form.gender} onChange={handleChange('gender')} required>
                  <option value="">Select</option>
                  <option value={1}>Female</option>
                  <option value={2}>Male</option>
                </select>
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Height (cm)">
                <input type="number" className="input" placeholder="e.g. 170" min="50" max="250"
                  value={form.height} onChange={handleChange('height')} required />
              </Field>
              <Field label="Weight (kg)">
                <input type="number" className="input" placeholder="e.g. 80" min="10" max="300"
                  value={form.weight} onChange={handleChange('weight')} required />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Systolic BP (mmHg)">
                <input type="number" className="input" placeholder="e.g. 130" min="60" max="300"
                  value={form.systolic_bp} onChange={handleChange('systolic_bp')} required />
              </Field>
              <Field label="Diastolic BP (mmHg)">
                <input type="number" className="input" placeholder="e.g. 85" min="40" max="200"
                  value={form.diastolic_bp} onChange={handleChange('diastolic_bp')} required />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Cholesterol">
                <select className="select" value={form.cholesterol} onChange={handleChange('cholesterol')} required>
                  <option value="">Select</option>
                  {CHOL_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
              <Field label="Glucose">
                <select className="select" value={form.glucose} onChange={handleChange('glucose')} required>
                  <option value="">Select</option>
                  {CHOL_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <Field label="Smoking">
                <select className="select" value={form.smoking} onChange={handleChange('smoking')} required>
                  <option value="">Select</option>
                  {BINARY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
              <Field label="Alcohol">
                <select className="select" value={form.alcohol} onChange={handleChange('alcohol')} required>
                  <option value="">Select</option>
                  {BINARY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
              <Field label="Physical Activity">
                <select className="select" value={form.physical_activity} onChange={handleChange('physical_activity')} required>
                  <option value="">Select</option>
                  {BINARY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
              {loading ? <><Loader2 size={18} className="animate-spin" /> Analyzing...</> : <><Brain size={18} /> Predict Risk</>}
            </button>
          </form>
        </div>

        {/* Results Panel */}
        <div className="space-y-6">
          {error && (
            <div className="bg-danger-500/10 border border-danger-500/20 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle size={20} className="text-danger-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-danger-500 font-medium">Prediction Error</p>
                <p className="text-sm text-slate-400 mt-1">{error}</p>
              </div>
            </div>
          )}

          {loading && <Spinner />}

          {!loading && !result && !error && (
            <div className="card p-12 flex flex-col items-center justify-center text-slate-500">
              <Brain size={48} className="mb-4 opacity-30" />
              <p>Fill in the patient parameters and click "Predict Risk" to see results.</p>
            </div>
          )}

          {result && (
            <>
              {/* Prediction Result Card */}
              <div className={`card p-6 ${isPositive ? 'border-danger-500/30' : 'border-success-500/30'}`}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-slate-200">Prediction Result</h3>
                  <span className={`badge-${isPositive ? 'red' : 'green'} text-sm`}>
                    {isPositive ? 'CVD Risk Detected' : 'No CVD Risk'}
                  </span>
                </div>

                {/* Probability Gauge */}
                <div className="mb-4">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-slate-400">CVD Probability</span>
                    <span className={`text-2xl font-bold ${isPositive ? 'text-danger-500' : 'text-success-500'}`}>
                      {probabilityPct}%
                    </span>
                  </div>
                  <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${isPositive ? 'bg-danger-500' : 'bg-success-500'}`}
                      style={{ width: `${probabilityPct}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-slate-500 mt-1">
                    <span>0%</span>
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-slate-800/50 rounded-lg p-3">
                    <p className="text-slate-500 text-xs">Model Version</p>
                    <p className="text-slate-200 font-medium">{result.model_version || 'v1.0'}</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3">
                    <p className="text-slate-500 text-xs">Prediction ID</p>
                    <p className="text-slate-200 font-mono text-xs">{result.prediction_id || '—'}</p>
                  </div>
                </div>
              </div>

              {/* SHAP Explanation */}
              {result.explanation?.available && (
                <div className="card p-6">
                  <h3 className="font-semibold text-slate-200 mb-1 flex items-center gap-2">
                    <Info size={18} className="text-primary-400" />
                    SHAP Explanation
                  </h3>
                  <p className="text-xs text-slate-500 mb-4">
                    Feature contributions to this prediction (SHAP TreeExplainer)
                  </p>

                  {/* Positive Contributors */}
                  {result.explanation.top_positive_contributors?.length > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-semibold text-danger-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                        <TrendingUp size={14} /> Increases CVD Risk
                      </p>
                      <div className="space-y-2">
                        {result.explanation.top_positive_contributors.map((c) => (
                          <div key={c.feature} className="flex items-center justify-between bg-danger-500/5 border border-danger-500/10 rounded-lg px-3 py-2">
                            <span className="text-sm text-slate-300">{c.feature}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-slate-500">{c.value}</span>
                              <span className="text-sm font-mono text-danger-400">+{c.contribution.toFixed(4)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Negative Contributors */}
                  {result.explanation.top_negative_contributors?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-success-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                        <TrendingDown size={14} /> Decreases CVD Risk
                      </p>
                      <div className="space-y-2">
                        {result.explanation.top_negative_contributors.map((c) => (
                          <div key={c.feature} className="flex items-center justify-between bg-success-500/5 border border-success-500/10 rounded-lg px-3 py-2">
                            <span className="text-sm text-slate-300">{c.feature}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-slate-500">{c.value}</span>
                              <span className="text-sm font-mono text-success-400">{c.contribution.toFixed(4)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Disclaimer */}
              <div className="bg-warning-500/5 border border-warning-500/20 rounded-xl p-4 flex items-start gap-3">
                <AlertTriangle size={18} className="text-warning-500 mt-0.5 shrink-0" />
                <p className="text-xs text-slate-400">
                  <strong className="text-warning-500">Medical Disclaimer:</strong> This prediction is for
                  educational and software demonstration purposes only. It is NOT a medical diagnosis.
                  Always consult a qualified healthcare professional for medical advice.
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
