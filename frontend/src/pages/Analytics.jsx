import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  getGenderAnalytics, getCholAnalytics, getGlucoseAnalytics,
  getLifestyle, getBMIAnalytics, getBPAnalytics, getAgeAnalytics
} from '../api/client';

const TT = { contentStyle: { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12 }, formatter: v => v.toLocaleString() };

function ChartCard({ title, sub, children }) {
  return (
    <div className="card p-6">
      <h3 className="font-semibold text-slate-200">{title}</h3>
      {sub && <p className="text-xs text-slate-500 mb-4">{sub}</p>}
      {children}
    </div>
  );
}

function Spinner() {
  return <div className="flex items-center justify-center py-20"><div className="spinner w-10 h-10" /></div>;
}

export default function Analytics() {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    Promise.all([
      getGenderAnalytics(), getCholAnalytics(), getGlucoseAnalytics(),
      getLifestyle(), getBMIAnalytics(), getBPAnalytics(), getAgeAnalytics()
    ])
      .then(([gender, chol, glucose, lifestyle, bmi, bp, age]) => {
        setData({ gender: gender.data, chol: chol.data, glucose: glucose.data,
                  lifestyle: lifestyle.data, bmi: bmi.data, bp: bp.data, age: age.data });
      })
      .catch(() => setError('Failed to load analytics data'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error) return <div className="text-danger-500 bg-danger-500/10 border border-danger-500/20 rounded-xl p-6">{error}</div>;

  const genderPie = (data.gender || []).map(g => ({ name: g.name, value: g.total }));
  const GENDER_COLORS = ['#f472b6', '#38bdf8']; // Female=pink, Male=blue (API returns Female first)

  const DISEASE_COLOR = '#f43f5e';   // red
  const HEALTHY_COLOR  = '#38bdf8';   // blue

  const cholData = (data.chol || []).map(c => ({
    name: c.name,
    disease: c.diseaseCases,
    healthy: c.total - c.diseaseCases,
  }));

  const glucoseData = (data.glucose || []).map(c => ({
    name: c.name,
    disease: c.diseaseCases,
    healthy: c.total - c.diseaseCases,
  }));

  const lifestyleItems = data.lifestyle ? [
    { name: 'Smoking', value: data.lifestyle.smoking?.diseaseCases || 0, healthy: data.lifestyle.smoking?.total - data.lifestyle.smoking?.diseaseCases || 0 },
    { name: 'Alcohol',  value: data.lifestyle.alcohol?.diseaseCases || 0,  healthy: data.lifestyle.alcohol?.total - data.lifestyle.alcohol?.diseaseCases || 0 },
    { name: 'Active',   value: data.lifestyle.physicalActivity?.diseaseCases || 0, healthy: data.lifestyle.physicalActivity?.total - data.lifestyle.physicalActivity?.diseaseCases || 0 },
  ] : [];

  const bmiData = (data.bmi || []).map(b => ({
    name: b.name,
    disease: b.diseaseCases,
    healthy: b.total - b.diseaseCases,
    total: b.total,
  }));
  const bpData  = (data.bp  || []).map(b => ({ name: b.name, total: b.total, disease: b.diseaseCases, healthy: b.total - b.diseaseCases }));
  const ageData = (data.age || []).map(a => ({ name: a.name, total: a.total, disease: a.disease }));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Analytics <span className="gradient-text">Deep Dive</span></h1>
        <p className="section-sub">8 real-time MongoDB aggregation charts</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gender Distribution */}
        <ChartCard title="Gender Distribution" sub="Female vs Male patient split">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={genderPie} cx="50%" cy="50%" outerRadius={90} paddingAngle={4} dataKey="value">
                {genderPie.map((_, i) => <Cell key={i} fill={GENDER_COLORS[i]} />)}
              </Pie>
              <Tooltip {...TT} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Age Group */}
        <ChartCard title="Age Group Analysis" sub="Disease cases by age bucket">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={ageData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip {...TT} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              <Bar dataKey="total"   name="Total"   fill="#38bdf8" radius={[4,4,0,0]} />
              <Bar dataKey="disease" name="Disease" fill="#f43f5e" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Cholesterol vs Disease */}
        <ChartCard title="Cholesterol vs. Disease" sub="Stratified by cholesterol category">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={cholData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip {...TT} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              <Bar dataKey="disease" name="Disease" fill={DISEASE_COLOR} radius={[4,4,0,0]} />
              <Bar dataKey="healthy" name="No Disease"  fill={HEALTHY_COLOR} radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Glucose vs Disease */}
        <ChartCard title="Glucose vs. Disease" sub="Stratified by glucose category">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={glucoseData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip {...TT} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              <Bar dataKey="disease" name="Disease" fill={DISEASE_COLOR} radius={[4,4,0,0]} />
              <Bar dataKey="healthy" name="No Disease"  fill={HEALTHY_COLOR} radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* BMI */}
        <ChartCard title="BMI Category Analysis" sub="Disease by BMI classification">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={bmiData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} width={85} />
              <Tooltip {...TT} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              <Bar dataKey="disease" name="Disease" fill={DISEASE_COLOR} radius={[0,4,4,0]} />
              <Bar dataKey="healthy" name="No Disease"  fill={HEALTHY_COLOR} radius={[0,4,4,0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Blood Pressure */}
        <ChartCard title="Blood Pressure Categories" sub="Patient count by BP classification">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={bpData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip {...TT} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              <Bar dataKey="total"   name="Total"   fill="#818cf8" radius={[4,4,0,0]} />
              <Bar dataKey="disease" name="Disease" fill={DISEASE_COLOR} radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Lifestyle table */}
      <div className="card p-6">
        <h3 className="font-semibold text-slate-200 mb-4">Lifestyle Factors vs. Disease</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="table-header">
              <th className="table-cell text-left">Factor</th>
              <th className="table-cell text-right">Disease Cases</th>
              <th className="table-cell text-right">No Disease Cases</th>
            </tr>
          </thead>
          <tbody>
            {lifestyleItems.map(item => (
              <tr key={item.name} className="table-row">
                <td className="table-cell font-medium text-slate-200">{item.name}</td>
                <td className="table-cell text-right text-danger-500">{item.value.toLocaleString()}</td>
                <td className="table-cell text-right text-success-500">{item.healthy.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
