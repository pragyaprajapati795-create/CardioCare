import React, { useState, useEffect } from 'react';
import { Play, Database, Clock } from 'lucide-react';
import { getQueries, runQuery } from '../api/client';

const QueryLab = () => {
  const [queries, setQueries] = useState([]);
  const [selectedQuery, setSelectedQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getQueries()
      .then(res => {
        const data = res.data || [];
        setQueries(data);
        if (data.length > 0) setSelectedQuery(data[0].id);
      })
      .catch(err => console.error("Error loading queries", err));
  }, []);

  const handleRunQuery = async () => {
    if (!selectedQuery) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await runQuery(selectedQuery);
      setResult(res.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (detail?.error) {
        setError(detail.error);
      } else {
        setError("Failed to execute query");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">MongoDB Query Lab</h1>
        <p className="section-sub">Execute and visualize real MongoDB aggregations</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel: Query Selection */}
        <div className="lg:col-span-1 space-y-4">
          <div className="card p-6">
            <h3 className="font-semibold text-slate-200 mb-4">Select Query</h3>
            <select
              className="select"
              value={selectedQuery}
              onChange={(e) => setSelectedQuery(e.target.value)}
            >
              {queries.map(q => (
                <option key={q.id} value={q.id}>{q.name}</option>
              ))}
            </select>

            <button
              onClick={handleRunQuery}
              disabled={loading}
              className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
            >
              {loading ? <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" /> : <Play size={18} />}
              Run Query
            </button>
          </div>

          {result && (
            <div className="card p-6">
              <h3 className="font-semibold text-slate-200 mb-2">Query Information</h3>
              <p className="text-sm text-slate-400 mb-4">{result.description}</p>

              <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-800/50 p-2 rounded-lg">
                <Clock size={14} /> Execution Time: <span className="font-medium text-slate-300">{result.execution_time_ms} ms</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-800/50 p-2 rounded-lg mt-2">
                <Database size={14} /> Collection: <span className="font-medium text-slate-300">patients</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-800/50 p-2 rounded-lg mt-2">
                <Play size={14} /> Operation: <span className="font-medium text-slate-300">{result.operation}</span>
              </div>
            </div>
          )}
        </div>

        {/* Right Panel: Code & Results */}
        <div className="lg:col-span-2 space-y-6">
          {result ? (
            <>
              <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
                <div className="px-4 py-2 bg-slate-900 text-xs font-mono text-slate-400 border-b border-slate-800 flex justify-between">
                  <span>MongoDB Shell (Aggregation)</span>
                  <span className="text-slate-500">Read-Only</span>
                </div>
                <pre className="p-4 text-sm text-emerald-400 font-mono overflow-x-auto">
                  {result.code}
                </pre>
              </div>

              <div className="card p-6">
                <h3 className="font-semibold text-slate-200 mb-4 border-b border-slate-800 pb-2">Query Results</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="table-header">
                        {Object.keys(result.result[0] || {}).map(key => (
                          <th key={key} className="table-cell">{key}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.result.map((row, i) => (
                        <tr key={i} className="table-row">
                          {Object.values(row).map((val, j) => (
                            <td key={j} className="table-cell">{String(val)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-slate-500 mt-3">
                  {result.result_count} result{result.result_count !== 1 ? 's' : ''} returned
                </p>
              </div>
            </>
          ) : (
            <div className="card p-12 flex flex-col items-center justify-center text-slate-500">
              <Database size={48} className="mb-4 opacity-30" />
              <p>Select and run a query to view execution code and results.</p>
            </div>
          )}
          {error && (
            <div className="bg-danger-500/10 text-danger-500 p-4 rounded-xl border border-danger-500/20">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default QueryLab;
