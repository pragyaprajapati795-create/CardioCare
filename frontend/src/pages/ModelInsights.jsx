import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts';
import { Activity, BarChart3, Target, TrendingUp } from 'lucide-react';
import {
  getModelMetrics,
  getFeatureImportance,
  getConfusionMatrix,
  getRocCurve,
  getPrecisionRecall,
} from '../api/client';

const TT = {
  contentStyle: { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12 },
  labelStyle: { color: '#94a3b8' },
};

function Spinner() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="spinner w-10 h-10" />
    </div>
  );
}

function MetricCard({ label, value, color = 'primary' }) {
  const colorMap = {
    primary: 'text-primary-400',
    green: 'text-success-500',
    red: 'text-danger-500',
    purple: 'text-accent-500',
  };
  return (
    <div className="card p-5 text-center">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-3xl font-extrabold ${colorMap[color]}`}>{value}</p>
    </div>
  );
}

export default function ModelInsights() {
  const [metrics, setMetrics] = useState(null);
  const [featureImportance, setFeatureImportance] = useState([]);
  const [confusionMatrix, setConfusionMatrix] = useState(null);
  const [rocCurve, setRocCurve] = useState(null);
  const [precisionRecall, setPrecisionRecall] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      getModelMetrics(),
      getFeatureImportance(),
      getConfusionMatrix(),
      getRocCurve(),
      getPrecisionRecall(),
    ])
      .then(([m, fi, cm, roc, pr]) => {
        setMetrics(m.data?.data || m.data);
        setFeatureImportance(fi.data?.data?.features || fi.data?.features || []);
        setConfusionMatrix(cm.data?.data || cm.data);
        setRocCurve(roc.data?.data || roc.data);
        setPrecisionRecall(pr.data?.data || pr.data);
      })
      .catch(() => setError('Failed to load model insights data. Is the backend running?'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error) {
    return (
      <div className="text-danger-500 bg-danger-500/10 border border-danger-500/20 rounded-xl p-6">
        {error}
      </div>
    );
  }

  // Prepare chart data
  const fiData = featureImportance.map((f) => ({
    feature: f.feature,
    importance: f.importance,
  }));

  const rocData = rocCurve?.fpr?.map((fpr, i) => ({
    fpr,
    tpr: rocCurve.tpr[i],
  })) || [];

  const prData = precisionRecall?.precision?.map((prec, i) => ({
    recall: precisionRecall.recall[i],
    precision: prec,
  })) || [];

  const cm = confusionMatrix;
  const cmTotal = cm ? cm.true_negative + cm.false_positive + cm.false_negative + cm.true_positive : 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Model <span className="gradient-text">Insights</span></h1>
        <p className="section-sub">XGBoost model performance, feature importance, and evaluation metrics</p>
      </div>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <MetricCard label="Accuracy" value={metrics.accuracy != null ? `${(metrics.accuracy * 100).toFixed(1)}%` : '—'} />
          <MetricCard label="Precision" value={metrics.precision != null ? `${(metrics.precision * 100).toFixed(1)}%` : '—'} color="green" />
          <MetricCard label="Recall" value={metrics.recall != null ? `${(metrics.recall * 100).toFixed(1)}%` : '—'} color="red" />
          <MetricCard label="F1 Score" value={metrics.f1_score != null ? `${(metrics.f1_score * 100).toFixed(1)}%` : '—'} color="purple" />
          <MetricCard label="ROC AUC" value={metrics.roc_auc != null ? `${(metrics.roc_auc * 100).toFixed(1)}%` : '—'} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Feature Importance */}
        <div className="card p-6">
          <h3 className="font-semibold text-slate-200 mb-1 flex items-center gap-2">
            <BarChart3 size={18} className="text-primary-400" />
            Feature Importance
          </h3>
          <p className="text-xs text-slate-500 mb-4">XGBoost gain-based importance scores</p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={fiData} layout="vertical" margin={{ top: 5, right: 20, left: 80, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis type="category" dataKey="feature" tick={{ fill: '#94a3b8', fontSize: 11 }} width={80} />
              <Tooltip {...TT} />
              <Bar dataKey="importance" name="Importance" radius={[0, 4, 4, 0]}>
                {fiData.map((_, i) => (
                  <Cell key={i} fill={i < 3 ? '#38bdf8' : '#334155'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Confusion Matrix */}
        <div className="card p-6">
          <h3 className="font-semibold text-slate-200 mb-1 flex items-center gap-2">
            <Target size={18} className="text-primary-400" />
            Confusion Matrix
          </h3>
          <p className="text-xs text-slate-500 mb-4">Held-out test set evaluation (20% of data)</p>
          {cm ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-success-500/10 border border-success-500/20 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">True Negative</p>
                  <p className="text-2xl font-bold text-success-500">{cm.true_negative?.toLocaleString()}</p>
                  <p className="text-xs text-slate-500">{cmTotal > 0 ? ((cm.true_negative / cmTotal) * 100).toFixed(1) : 0}%</p>
                </div>
                <div className="bg-danger-500/10 border border-danger-500/20 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">False Positive</p>
                  <p className="text-2xl font-bold text-danger-500">{cm.false_positive?.toLocaleString()}</p>
                  <p className="text-xs text-slate-500">{cmTotal > 0 ? ((cm.false_positive / cmTotal) * 100).toFixed(1) : 0}%</p>
                </div>
                <div className="bg-danger-500/10 border border-danger-500/20 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">False Negative</p>
                  <p className="text-2xl font-bold text-danger-500">{cm.false_negative?.toLocaleString()}</p>
                  <p className="text-xs text-slate-500">{cmTotal > 0 ? ((cm.false_negative / cmTotal) * 100).toFixed(1) : 0}%</p>
                </div>
                <div className="bg-success-500/10 border border-success-500/20 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">True Positive</p>
                  <p className="text-2xl font-bold text-success-500">{cm.true_positive?.toLocaleString()}</p>
                  <p className="text-xs text-slate-500">{cmTotal > 0 ? ((cm.true_positive / cmTotal) * 100).toFixed(1) : 0}%</p>
                </div>
              </div>
              <p className="text-xs text-slate-500 text-center">
                Total test samples: {cmTotal.toLocaleString()}
              </p>
            </div>
          ) : (
            <p className="text-slate-500 text-center py-8">Confusion matrix data unavailable</p>
          )}
        </div>

        {/* ROC Curve */}
        <div className="card p-6">
          <h3 className="font-semibold text-slate-200 mb-1 flex items-center gap-2">
            <TrendingUp size={18} className="text-primary-400" />
            ROC Curve
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            {rocCurve?.auc ? `AUC = ${rocCurve.auc.toFixed(4)}` : 'Receiver Operating Characteristic'}
          </p>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={rocData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="pr" tick={{ fill: '#64748b', fontSize: 11 }} label={{ value: 'False Positive Rate', position: 'insideBottom', offset: -5, fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }} />
              <Tooltip {...TT} />
              <Line type="monotone" dataKey="tpr" stroke="#38bdf8" strokeWidth={2} dot={false} name="TPR" />
              <Line type="monotone" dataKey={() => null} stroke="transparent" legendType="none" />
              {/* Diagonal reference line */}
              <Line
                data={[{ fpr: 0, tpr: 0 }, { fpr: 1, tpr: 1 }]}
                dataKey="tpr"
                stroke="#475569"
                strokeDasharray="5 5"
                strokeWidth={1}
                dot={false}
                name="Random"
                legendType="none"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Precision-Recall Curve */}
        <div className="card p-6">
          <h3 className="font-semibold text-slate-200 mb-1 flex items-center gap-2">
            <Activity size={18} className="text-primary-400" />
            Precision-Recall Curve
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            {precisionRecall?.auc ? `AUC = ${precisionRecall.auc.toFixed(4)}` : 'Precision vs Recall'}
          </p>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={prData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="recall" tick={{ fill: '#64748b', fontSize: 11 }} label={{ value: 'Recall', position: 'insideBottom', offset: -5, fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} label={{ value: 'Precision', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }} />
              <Tooltip {...TT} />
              <Line type="monotone" dataKey="precision" stroke="#8b5cf6" strokeWidth={2} dot={false} name="Precision" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-warning-500/5 border border-warning-500/20 rounded-xl p-4 flex items-start gap-3">
        <Activity size={18} className="text-warning-500 mt-0.5 shrink-0" />
        <p className="text-xs text-slate-400">
          <strong className="text-warning-500">Disclaimer:</strong> Feature importance and SHAP values reflect
          model behavior, not medical causation. This model is an educational/software demonstration and is NOT
          a medical diagnostic system.
        </p>
      </div>
    </div>
  );
}
