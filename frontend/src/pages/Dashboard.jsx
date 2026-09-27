import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Users, HeartPulse, Percent, CalendarDays, TrendingUp, Activity } from 'lucide-react';
import { getOverview, getAgeAnalytics, getDbHealth } from '../api/client';

const COLORS_DISEASE = ['#f43f5e', '#22c55e'];

function KpiCard({ icon: Icon, title, value, sub, color = 'primary' }) {
  const colorMap = {
    primary: 'text-primary-400',
    red: 'text-danger-500',
    green: 'text-success-500',
    purple: 'text-accent-500',
  };
  return (
    <div className="kpi-card group">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest">{title}</p>
          <p className={`text-3xl font-extrabold mt-2 ${colorMap[color]}`}>{value}</p>
          {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
        </div>
        <div className={`w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center ${colorMap[color]}`}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="spinner w-10 h-10" />
    </div>
  );
}

export default function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [ageData, setAgeData]   = useState([]);
  const [dbStatus, setDbStatus] = useState(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);

  useEffect(() => {
    Promise.all([
      getOverview(),
      getAgeAnalytics(),
      getDbHealth(),
    ])
      .then(([ov, ag, db]) => {
        setOverview(ov.data);
        setAgeData(ag.data);
        setDbStatus(db.data);
      })
      .catch(e => setError('Failed to load dashboard data. Is the backend running?'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error) return <div className="text-danger-500 bg-danger-500/10 border border-danger-500/20 rounded-xl p-6">{error}</div>;

  const pieData = overview ? [
    { name: 'CVD Cases', value: overview.diseaseCases },
    { name: 'No CVD',    value: overview.nonDiseaseCases },
  ] : [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard <span className="gradient-text">Overview</span></h1>
          <p className="section-sub">Real-time statistics from MongoDB · Live data</p>
        </div>
        {dbStatus && (
          <div className="flex items-center gap-2 text-xs bg-success-500/10 text-success-500 border border-success-500/20 px-3 py-1.5 rounded-full">
            <span className="w-2 h-2 rounded-full bg-success-500 animate-pulse" />
            MongoDB Connected · {dbStatus.patient_count?.toLocaleString()} patients
          </div>
        )}
      </div>

      {/* KPI Cards */}
      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard icon={Users}       title="Total Patients" value={overview.totalPatients?.toLocaleString()} sub="Live from MongoDB" color="primary" />
          <KpiCard icon={HeartPulse}  title="CVD Cases"      value={overview.diseaseCases?.toLocaleString()} sub="Cardiovascular disease" color="red" />
          <KpiCard icon={Percent}     title="Disease Rate"   value={`${overview.diseasePercentage}%`} sub="Of total dataset" color="purple" />
          <KpiCard icon={CalendarDays} title="Average Age"   value={`${overview.averageAge} yrs`} sub="Dataset mean" color="green" />
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <div className="card p-6">
          <h3 className="font-semibold text-slate-200 mb-1">Disease Distribution</h3>
          <p className="text-xs text-slate-500 mb-4">CVD vs. non-CVD patient split</p>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={75} outerRadius={105}
                paddingAngle={4} dataKey="value">
                {pieData.map((_, i) => <Cell key={i} fill={COLORS_DISEASE[i]} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12 }}
                formatter={v => v.toLocaleString()}
              />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Age Bar Chart */}
        <div className="card p-6">
          <h3 className="font-semibold text-slate-200 mb-1">Age Group Analysis</h3>
          <p className="text-xs text-slate-500 mb-4">Patient distribution by age bucket</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={ageData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12 }}
                formatter={v => v.toLocaleString()}
              />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              <Bar dataKey="total"   name="Total"         fill="#38bdf8" radius={[4,4,0,0]} />
              <Bar dataKey="disease" name="Disease Cases" fill="#f43f5e" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quick Stats */}
      {overview && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="card p-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary-500/10 flex items-center justify-center text-primary-400">
              <TrendingUp size={22} />
            </div>
            <div>
              <p className="text-xs text-slate-500">Average BMI</p>
              <p className="text-xl font-bold text-slate-100">{overview.averageBMI || '—'}</p>
            </div>
          </div>
          <div className="card p-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-danger-500/10 flex items-center justify-center text-danger-500">
              <Activity size={22} />
            </div>
            <div>
              <p className="text-xs text-slate-500">Avg Systolic BP</p>
              <p className="text-xl font-bold text-slate-100">{overview.averageSystolicBP || '—'} mmHg</p>
            </div>
          </div>
          <div className="card p-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-accent-500/10 flex items-center justify-center text-accent-500">
              <HeartPulse size={22} />
            </div>
            <div>
              <p className="text-xs text-slate-500">Non-CVD Patients</p>
              <p className="text-xl font-bold text-slate-100">{overview.nonDiseaseCases?.toLocaleString()}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
