import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ClaimsQueue from './pages/ClaimsQueue';
import TransactionLedger from './pages/TransactionLedger';
import Reconciliation from './pages/Reconciliation';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-slate-800 text-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-6">
            <span className="text-xl font-bold tracking-tight">Samanvaya</span>
            <NavLink to="/" end className={({isActive}) => `px-3 py-1.5 rounded text-sm font-medium ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`}>Dashboard</NavLink>
            <NavLink to="/claims" className={({isActive}) => `px-3 py-1.5 rounded text-sm font-medium ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`}>Claims Queue</NavLink>
            <NavLink to="/ledger" className={({isActive}) => `px-3 py-1.5 rounded text-sm font-medium ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`}>Ledger</NavLink>
            <NavLink to="/reconciliation" className={({isActive}) => `px-3 py-1.5 rounded text-sm font-medium ${isActive ? 'bg-slate-600' : 'hover:bg-slate-700'}`}>Reconciliation</NavLink>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/claims" element={<ClaimsQueue />} />
            <Route path="/ledger" element={<TransactionLedger />} />
            <Route path="/reconciliation" element={<Reconciliation />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
