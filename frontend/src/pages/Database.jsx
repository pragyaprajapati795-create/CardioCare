import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Database as DbIcon, Server, Cpu, DatabaseZap, LayoutList, CheckCircle2 } from 'lucide-react';

const Database = () => {
  const [stats, setStats] = useState(null);
  const [indexes, setIndexes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDbData = async () => {
      try {
        const [statsRes, indexesRes] = await Promise.all([
          axios.get('http://localhost:8000/api/v1/database/stats'),
          axios.get('http://localhost:8000/api/v1/database/indexes')
        ]);
        setStats(statsRes.data);
        setIndexes(indexesRes.data);
      } catch (error) {
        console.error("Error fetching database stats:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchDbData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Database Architecture</h1>
        <p className="text-gray-500 mt-1">System architecture and MongoDB optimization overview</p>
      </div>

      {/* Architecture Flow */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <h3 className="text-lg font-semibold text-gray-800 mb-6">System Architecture Flow</h3>
        <div className="flex flex-col md:flex-row items-center justify-between text-center gap-4 relative">
           
           <div className="flex flex-col items-center bg-blue-50 p-6 rounded-lg w-full md:w-1/4 border border-blue-100 z-10">
             <LayoutList className="text-blue-500 mb-2" size={32} />
             <span className="font-semibold text-blue-900">React Frontend</span>
             <span className="text-xs text-blue-600 mt-1">Axios HTTP Client</span>
           </div>
           
           <div className="hidden md:block h-1 w-full bg-gray-200 absolute left-0 top-1/2 -translate-y-1/2 z-0"></div>

           <div className="flex flex-col items-center bg-green-50 p-6 rounded-lg w-full md:w-1/4 border border-green-100 z-10">
             <Server className="text-green-500 mb-2" size={32} />
             <span className="font-semibold text-green-900">FastAPI Backend</span>
             <span className="text-xs text-green-600 mt-1">Python Service Layer</span>
           </div>

           <div className="flex flex-col items-center bg-purple-50 p-6 rounded-lg w-full md:w-1/4 border border-purple-100 z-10">
             <Cpu className="text-purple-500 mb-2" size={32} />
             <span className="font-semibold text-purple-900">ML Model</span>
             <span className="text-xs text-purple-600 mt-1">XGBoost / Joblib</span>
           </div>

           <div className="flex flex-col items-center bg-orange-50 p-6 rounded-lg w-full md:w-1/4 border border-orange-100 z-10">
             <DbIcon className="text-orange-500 mb-2" size={32} />
             <span className="font-semibold text-orange-900">MongoDB</span>
             <span className="text-xs text-orange-600 mt-1">PyMongo Driver</span>
           </div>

        </div>
      </div>

      {/* Collections Overview */}
      <div>
         <h3 className="text-lg font-semibold text-gray-800 mb-4">Database: <span className="text-primary-600 font-mono bg-primary-50 px-2 py-1 rounded">{stats?.database_name}</span></h3>
         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
           {stats?.collections.map(col => (
             <div key={col.name} className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
               <div className="flex items-center gap-2 mb-3 text-orange-600">
                  <DatabaseZap size={20} />
                  <h4 className="font-semibold">{col.name}</h4>
               </div>
               <p className="text-sm text-gray-600 mb-4 h-10">{col.purpose}</p>
               <div className="flex justify-between items-end">
                 <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Documents</span>
                 <span className="text-xl font-bold text-gray-900">{col.document_count.toLocaleString()}</span>
               </div>
             </div>
           ))}
         </div>
      </div>

      {/* Indexes and Optimization */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-6 border-b border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800">Database Optimization (Indexing)</h3>
          <p className="text-sm text-gray-500 mt-1">Indexes created on the `patients` collection to improve read performance.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b text-sm font-medium text-gray-500">
                <th className="py-3 px-6">Index Name</th>
                <th className="py-3 px-6">Collection</th>
                <th className="py-3 px-6">Indexed Field</th>
                <th className="py-3 px-6">Purpose / Optimization</th>
                <th className="py-3 px-6">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y text-sm text-gray-700">
              {indexes.map(idx => (
                <tr key={idx.name} className="hover:bg-gray-50">
                  <td className="py-3 px-6 font-mono text-xs text-gray-600 bg-gray-100 inline-block m-2 rounded px-2">{idx.name}</td>
                  <td className="py-3 px-6">{idx.collection}</td>
                  <td className="py-3 px-6 font-semibold">{idx.field} {idx.unique && <span className="text-xs ml-2 text-primary-600 bg-primary-50 px-2 py-1 rounded-full">Unique</span>}</td>
                  <td className="py-3 px-6">{idx.purpose}</td>
                  <td className="py-3 px-6">
                    <span className="flex items-center gap-1 text-green-600 font-medium">
                      <CheckCircle2 size={16} /> Active
                    </span>
                  </td>
                </tr>
              ))}
              {indexes.length === 0 && (
                <tr>
                  <td colSpan="5" className="py-6 text-center text-gray-500">No custom indexes found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};

export default Database;
