import React, { useState, useEffect, useCallback } from 'react';
import { Search, ChevronLeft, ChevronRight, SlidersHorizontal, X } from 'lucide-react';
import { getPatients } from '../api/client';

const CHOL_LABELS = { 1: 'Normal', 2: 'Above Normal', 3: 'Well Above' };

function Spinner() { return <div className="flex justify-center py-10"><div className="spinner w-8 h-8" /></div>; }

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [total, setTotal]       = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const [page, setPage]         = useState(1);
  const limit = 20;

  // Filters
  const [search, setSearch]   = useState('');
  const [gender, setGender]   = useState('');
  const [cardio, setCardio]   = useState('');
  const [cholesterol, setCholesterol] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [sortBy, setSortBy]   = useState('patient_id');
  const [sortOrder, setSortOrder] = useState('asc');

  const fetchPatients = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, limit, sort_by: sortBy, sort_order: sortOrder };
      if (search) params.search = search;
      if (gender) params.gender = gender;
      if (cardio !== '') params.cardio = cardio;
      if (cholesterol) params.cholesterol = cholesterol;

      const res = await getPatients(params);
      const d   = res.data?.data || res.data;
      setPatients(d.items || []);
      setTotal(d.total || 0);
      setTotalPages(d.total_pages || 1);
    } catch (e) {
      setError('Failed to fetch patients');
    } finally {
      setLoading(false);
    }
  }, [page, search, gender, cardio, cholesterol, sortBy, sortOrder]);

  useEffect(() => { fetchPatients(); }, [fetchPatients]);

  const clearFilters = () => {
    setSearch(''); setGender(''); setCardio(''); setCholesterol('');
    setPage(1);
  };

  const hasFilters = search || gender || cardio !== '' || cholesterol;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Patient <span className="gradient-text">Explorer</span></h1>
          <p className="section-sub">
            {total > 0 ? `${total.toLocaleString()} records · Page ${page} of ${totalPages}` : 'Loading...'}
          </p>
        </div>
      </div>

      {/* Search + Filters bar */}
      <div className="card p-4 space-y-3">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
            <input
              id="patient-search"
              type="text"
              placeholder="Search by Patient ID (e.g. P10001)…"
              className="input pl-9"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
            />
          </div>
          <button
            id="toggle-filters"
            onClick={() => setShowFilters(s => !s)}
            className={`btn-secondary flex items-center gap-2 ${showFilters ? 'ring-1 ring-primary-500' : ''}`}
          >
            <SlidersHorizontal size={16} /> Filters
          </button>
          {hasFilters && (
            <button onClick={clearFilters} className="btn-secondary flex items-center gap-2 text-danger-400">
              <X size={16} /> Clear
            </button>
          )}
        </div>

        {showFilters && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-slate-800">
            <div>
              <label className="label">Gender</label>
              <select id="filter-gender" className="select" value={gender} onChange={e => { setGender(e.target.value); setPage(1); }}>
                <option value="">All</option>
                <option value="1">Female (1)</option>
                <option value="2">Male (2)</option>
              </select>
            </div>
            <div>
              <label className="label">CVD Status</label>
              <select id="filter-cardio" className="select" value={cardio} onChange={e => { setCardio(e.target.value); setPage(1); }}>
                <option value="">All</option>
                <option value="1">Disease</option>
                <option value="0">Normal</option>
              </select>
            </div>
            <div>
              <label className="label">Cholesterol</label>
              <select id="filter-chol" className="select" value={cholesterol} onChange={e => { setCholesterol(e.target.value); setPage(1); }}>
                <option value="">All</option>
                <option value="1">Normal</option>
                <option value="2">Above Normal</option>
                <option value="3">Well Above</option>
              </select>
            </div>
            <div>
              <label className="label">Sort By</label>
              <div className="flex gap-2">
                <select className="select flex-1" value={sortBy} onChange={e => setSortBy(e.target.value)}>
                  <option value="patient_id">ID</option>
                  <option value="age_years">Age</option>
                  <option value="bmi">BMI</option>
                  <option value="systolic_bp">Systolic BP</option>
                  <option value="cholesterol">Cholesterol</option>
                </select>
                <select className="select w-24" value={sortOrder} onChange={e => setSortOrder(e.target.value)}>
                  <option value="asc">Asc</option>
                  <option value="desc">Desc</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="table-header">
                <th className="table-cell">Patient ID</th>
                <th className="table-cell">Age</th>
                <th className="table-cell">Gender</th>
                <th className="table-cell">BP (Sys/Dia)</th>
                <th className="table-cell">BMI</th>
                <th className="table-cell">Cholesterol</th>
                <th className="table-cell">Glucose</th>
                <th className="table-cell">CVD Status</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="8"><Spinner /></td></tr>
              ) : error ? (
                <tr><td colSpan="8" className="table-cell text-danger-500 text-center">{error}</td></tr>
              ) : patients.length === 0 ? (
                <tr><td colSpan="8" className="table-cell text-slate-500 text-center py-12">No patients found</td></tr>
              ) : patients.map(p => (
                <tr key={p.patient_id} className="table-row">
                  <td className="table-cell font-mono font-semibold text-primary-400">{p.patient_id}</td>
                  <td className="table-cell">{p.age_years}</td>
                  <td className="table-cell">{p.gender === 1 ? 'Female' : 'Male'}</td>
                  <td className="table-cell">{p.systolic_bp} / {p.diastolic_bp}</td>
                  <td className="table-cell">{p.bmi}</td>
                  <td className="table-cell">{CHOL_LABELS[p.cholesterol] || p.cholesterol}</td>
                  <td className="table-cell">{CHOL_LABELS[p.glucose] || p.glucose}</td>
                  <td className="table-cell">
                    {p.cardio === 1
                      ? <span className="badge-red">Disease</span>
                      : <span className="badge-green">Normal</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-900/40">
          <span className="text-xs text-slate-500">
            {total > 0 ? `Showing ${((page-1)*limit)+1}–${Math.min(page*limit, total)} of ${total.toLocaleString()}` : ''}
          </span>
          <div className="flex gap-2">
            <button
              id="prev-page"
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
              className="btn-secondary p-2 disabled:opacity-40"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="px-3 py-1.5 text-sm text-slate-400 bg-slate-800 rounded-lg">{page}</span>
            <button
              id="next-page"
              disabled={page >= totalPages}
              onClick={() => setPage(p => p + 1)}
              className="btn-secondary p-2 disabled:opacity-40"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
