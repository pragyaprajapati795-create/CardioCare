import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Users, FlaskConical, Database,
  Brain, BarChart3, History, Heart, Activity
} from 'lucide-react';

const links = [
  { to: '/',               icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/analytics',      icon: BarChart3,       label: 'Analytics' },
  { to: '/patients',       icon: Users,           label: 'Patients' },
  { to: '/predict',        icon: Brain,           label: 'AI Prediction' },
  { to: '/query-lab',      icon: FlaskConical,    label: 'Query Lab' },
  { to: '/model-insights', icon: Activity,        label: 'Model Insights' },
  { to: '/history',        icon: History,         label: 'Prediction History' },
  { to: '/database',       icon: Database,        label: 'Database' },
];

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-slate-950 border-r border-slate-800 flex flex-col z-20">
      {/* Logo */}
      <div className="px-6 py-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg shadow-primary-900/40">
            <Heart size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white">CardioCare</h1>
            <p className="text-xs text-slate-400">Analytics Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="px-3 text-xs font-semibold text-slate-600 uppercase tracking-widest mb-3">Main</p>
        {links.slice(0, 3).map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}

        <p className="px-3 text-xs font-semibold text-slate-600 uppercase tracking-widest mt-5 mb-3">Machine Learning</p>
        {links.slice(3, 7).map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}

        <p className="px-3 text-xs font-semibold text-slate-600 uppercase tracking-widest mt-5 mb-3">System</p>
        {links.slice(7).map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-800">
        <p className="text-xs text-slate-600">v1.0 · 68,616 Records</p>
        <p className="text-xs text-slate-700 mt-0.5">Educational Demo Only</p>
      </div>
    </aside>
  );
}
