// Central API client — all calls go through here
import axios from 'axios';

// Use relative URL in production (Vercel proxy), localhost in development
const baseURL = import.meta.env.DEV
  ? 'http://localhost:8000/api/v1'
  : '/api/v1';

const api = axios.create({
  baseURL,
  timeout: 15000,
});

// ── Analytics ──────────────────────────────────────────────────────────────
export const getOverview        = () => api.get('/analytics/overview');
export const getAgeAnalytics    = () => api.get('/analytics/age');
export const getGenderAnalytics = () => api.get('/analytics/gender');
export const getCholAnalytics   = () => api.get('/analytics/cholesterol');
export const getGlucoseAnalytics= () => api.get('/analytics/glucose');
export const getLifestyle       = () => api.get('/analytics/lifestyle');
export const getBMIAnalytics    = () => api.get('/analytics/bmi');
export const getBPAnalytics     = () => api.get('/analytics/blood-pressure');

// ── Patients ───────────────────────────────────────────────────────────────
export const getPatients = (params) => api.get('/patients', { params });
export const getPatient  = (id)     => api.get(`/patients/${id}`);
export const createPatient = (data) => api.post('/patients/', data);
export const updatePatient = (id, data) => api.put(`/patients/${id}`, data);
export const deletePatient = (id)   => api.delete(`/patients/${id}`);

// ── Query Lab ──────────────────────────────────────────────────────────────
export const getQueries  = () => api.get('/query-lab/queries');
export const runQuery    = (query_id) => api.post('/query-lab/run', { query_id });

// ── Prediction ─────────────────────────────────────────────────────────────
export const predict         = (data) => api.post('/predict', data);
export const getPredictions  = (params) => api.get('/predictions', { params });

// ── Model Info / Metrics ───────────────────────────────────────────────────
export const getModelInfo    = () => api.get('/model/info');
export const getModelMetrics = () => api.get('/model/metrics');

// ── Model Insights (Phase 5) ───────────────────────────────────────────────
export const getFeatureImportance = () => api.get('/model/feature-importance');
export const getExplainability    = () => api.get('/model/explainability');
export const getConfusionMatrix   = () => api.get('/model/confusion-matrix');
export const getRocCurve          = () => api.get('/model/roc-curve');
export const getPrecisionRecall   = () => api.get('/model/precision-recall');

// ── Database health ────────────────────────────────────────────────────────
export const getDbHealth   = () => api.get('/database/health');
export const getDbPipeline = () => api.get('/database/pipeline');
export const getDbStats    = () => api.get('/database/stats');

export default api;
