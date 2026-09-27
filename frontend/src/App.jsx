import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Analytics from './pages/Analytics';
import Patients from './pages/Patients';
import Predict from './pages/Predict';
import QueryLab from './pages/QueryLab';
import ModelInsights from './pages/ModelInsights';
import PredictionHistory from './pages/PredictionHistory';
import Database from './pages/Database';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950 flex">
        <Sidebar />
        <div className="flex-1 ml-64 flex flex-col min-h-screen">
          {/* Top bar */}
          <header className="h-14 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between px-8 sticky top-0 z-10 backdrop-blur">
            <span className="text-sm text-slate-400 font-medium">CardioCare Analytics Platform</span>
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">Admin</span>
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white text-sm font-bold">A</div>
            </div>
          </header>
          {/* Page content */}
          <main className="flex-1 p-8">
            <Routes>
              <Route path="/"               element={<Dashboard />} />
              <Route path="/analytics"      element={<Analytics />} />
              <Route path="/patients"       element={<Patients />} />
              <Route path="/predict"        element={<Predict />} />
              <Route path="/query-lab"      element={<QueryLab />} />
              <Route path="/model-insights" element={<ModelInsights />} />
              <Route path="/history"        element={<PredictionHistory />} />
              <Route path="/database"       element={<Database />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
