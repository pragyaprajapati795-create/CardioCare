import React, { useState, useEffect, useCallback } from 'react';
import { History, ChevronLeft, ChevronRight, Brain, Clock, User } from 'lucide-react';
import { getPredictions } from '../api/client';

function Spinner() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="spinner w-10 h-10" />
    </div>
  );
}

export default function PredictionHistory() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const limit = 20;

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getPredictions({ page, limit });
      const d = res.data?.data || res.data;
      setData(d);
    } catch (err) {
      setError('Failed to load prediction history. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Prediction <span className="gradient-text">History</span></h1>
          <p className="section-sub">
            {total > 0 ? `${total.toLocaleString()} predictions · Page ${page} of ${totalPages}` : 'Loading...'}
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="table-header">
                <th className="table-cell">Prediction ID</th>
                <th className="table-cell">Patient ID</th>
                <th className="table-cell">Result</th>
                <th className="table-cell">Probability</th>
                <th className="table-cell">Model</th>
                <th className="table-cell">Timestamp</th>
                <th className="table-cell">Input Summary</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="7"><Spinner /></td></tr>
              ) : error ? (
                <tr><td colSpan="7" className="table-cell text-danger-500 text-center">{error}</td></tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan="7" className="table-cell text-slate-500 text-center py-12">
                    <Brain size={32} className="mx-auto mb-3 opacity-30" />
                    No predictions yet. Use the AI Prediction page to make your first prediction.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.prediction_id} className="table-row">
                    <td className="table-cell font-mono text-primary-400 text-xs">{item.prediction_id || '—'}</td>
                    <td className="table-cell">
                      {item.patient_id ? (
                        <span className="flex items-center gap-1 text-slate-300">
                          <User size={12} className="text-slate-500" />
                          {item.patient_id}
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="table-cell">
                      {item.prediction === 1 ? (
                        <span className="badge-red">CVD Risk</span>
                      ) : (
                        <span className="badge-green">No CVD</span>
                      )}
                    </td>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${item.prediction === 1 ? 'bg-danger-500' : 'bg-success-500'}`}
                            style={{ width: `${((item.probability || 0) * 100).toFixed(0)}%` }}
                          />
                        </div>
                        <span className="text-sm font-mono text-slate-300">
                          {((item.probability || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="table-cell text-xs text-slate-500">{item.model_version || 'v1.0'}</td>
                    <td className="table-cell">
                      <span className="flex items-center gap-1 text-xs text-slate-400">
                        <Clock size={12} />
                        {item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}
                      </span>
                    </td>
                    <td className="table-cell text-xs text-slate-500">
                      {item.input_summary ? (
                        <span>
                          Age {item.input_summary.age_years || '—'} · BP {item.input_summary.systolic_bp || '—'}/{item.input_summary.diastolic_bp || '—'}
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > 0 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-900/40">
            <span className="text-xs text-slate-500">
              Showing {((page - 1) * limit) + 1}–{Math.min(page * limit, total)} of {total.toLocaleString()}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="btn-secondary p-2 disabled:opacity-40"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="px-3 py-1.5 text-sm text-slate-400 bg-slate-800 rounded-lg">{page}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="btn-secondary p-2 disabled:opacity-40"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
