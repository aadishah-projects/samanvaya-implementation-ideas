import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ClaimsQueue from './pages/ClaimsQueue';
import Batches from './pages/Batches';
import TransactionLedger from './pages/TransactionLedger';
import SosysMigration from './pages/SosysMigration';
import Reconciliation from './pages/Reconciliation';

const menuItems = ['Insurees and Policies', 'Claims', 'Utils', 'Administration', 'Tools', 'Profile'];
const toolRoutes = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/claims', label: 'Claims' },
  { to: '/batches', label: 'Batches' },
  { to: '/ledger', label: 'Ledger' },
  { to: '/sosys', label: 'SOSYS' },
  { to: '/reconciliation', label: 'Reconciliation' },
];

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#eeeeee] text-[#424242]">
        <header className="sticky top-0 z-40 bg-[#00838F] text-white shadow">
          <div className="flex h-14 items-center gap-4 px-4">
            <div className="flex min-w-fit items-center gap-2">
              <img src="/icon.png" alt="OpenIMIS" className="h-9 w-9" />
              <div className="leading-tight">
                <div className="text-[14px] font-medium">openIMIS</div>
                <div className="text-[11px] opacity-90">v1.5.0</div>
              </div>
            </div>

            <nav className="hidden flex-1 items-center justify-center gap-1 lg:flex">
              {menuItems.map((item) => (
                <span key={item} className="px-3 py-2 text-[14px] font-normal hover:bg-white/10">
                  {item}
                </span>
              ))}
            </nav>

            <div className="ml-auto flex items-center gap-2">
              <div className="hidden h-9 w-64 items-center gap-2 rounded bg-white px-3 text-[#757575] md:flex">
                <span className="material-icons text-[20px]">search</span>
                <input
                  placeholder="Insuree enquiry"
                  className="w-full border-0 bg-transparent text-[13px] text-[#424242] outline-none"
                />
              </div>
              <button className="material-icons rounded p-2 text-[22px] hover:bg-white/10" title="Settings">settings</button>
              <button className="material-icons rounded p-2 text-[22px] hover:bg-white/10" title="Help">help_outline</button>
            </div>
          </div>
          <nav className="flex gap-1 overflow-x-auto bg-white px-4 py-2 text-[#424242] shadow-sm">
            {toolRoutes.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded px-3 py-1.5 text-[13px] font-medium uppercase ${
                    isActive ? 'bg-[#E0F2F1] text-[#00838F]' : 'hover:bg-[#F5F5F5]'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </header>

        <main className="px-4 py-5">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/claims" element={<ClaimsQueue />} />
            <Route path="/batches" element={<Batches />} />
            <Route path="/ledger" element={<TransactionLedger />} />
            <Route path="/sosys" element={<SosysMigration />} />
            <Route path="/reconciliation" element={<Reconciliation />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
