import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import CustomersPage from './Customers';
import './App.css';

const PaymentModal = ({ table, onConfirm, onCancel }) => {
  const [amount, setAmount] = useState(1000);
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');

  return (
    <div className="modal-overlay">
      <div className="modal-content fade-in">
        <h3>Collect Payment - Table {table.table_number}</h3>
        <div className="modal-body">
          <div className="form-group">
            <label>Bill Amount (₹)</label>
            <input type="number" className="input-field" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Customer Phone</label>
            <input type="text" className="input-field" placeholder="9990000000" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Customer Name</label>
            <input type="text" className="input-field" placeholder="Guest Name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </div>
        <div className="modal-actions">
          <button className="nav-btn" onClick={onCancel}>Cancel</button>
          <button className="submit-btn" style={{gridColumn: 'span 1', width: 'auto'}} onClick={() => onConfirm(amount, phone, name)}>Confirm Payment</button>
        </div>
      </div>
    </div>
  );
};

function App() {
  const [data, setData] = useState(null);
  const [role, setRole] = useState(localStorage.getItem('userRole') || null);
  const [view, setView] = useState('dashboard');
  const [activePayment, setActivePayment] = useState(null);
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');
  
  // Form States
  const [qName, setQName] = useState('');
  const [qPhone, setQPhone] = useState('');
  const [qSize, setQSize] = useState(2);

  const fetchData = async () => {
    try {
      const response = await fetch('/api/dashboard');
      const result = await response.json();
      setData(result);
    } catch (error) { console.error("API Error"); }
  };

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    if (role) {
      fetchData();
      const interval = setInterval(fetchData, 4000);
      return () => clearInterval(interval);
    }
  }, [role]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const handleLogout = () => {
    setRole(null);
    localStorage.removeItem('userRole');
  };

  const handleLogin = (selectedRole) => {
    setRole(selectedRole);
    localStorage.setItem('userRole', selectedRole);
    if (selectedRole === 'floor_manager') setView('tables');
    else if (selectedRole === 'receptionist') setView('waitlist');
    else setView('dashboard');
  };

  const handleAction = async (table, action) => {
    if (action === 'pay') {
      setActivePayment(table);
    } else {
      await fetch(`/api/tables/${table.table_id}/clean`, { method: 'POST' });
      fetchData();
    }
  };

  const confirmPayment = async (amount, phone, name) => {
    if (!phone) {
      alert("Phone number is required for loyalty points.");
      return;
    }
    const cleanPhone = phone.trim();
    await fetch(`/api/tables/${activePayment.table_id}/pay?amount=${amount}&phone=${cleanPhone}&name=${name}`, { method: 'POST' });
    setActivePayment(null);
    fetchData();
  };

  const addToQueue = async (e) => {
    e.preventDefault();
    if (!qName || !qPhone) return;

    const url = `/api/queue/add?name=${encodeURIComponent(qName)}&size=${qSize}&phone=${encodeURIComponent(qPhone)}`;

    try {
      const response = await fetch(url, { method: 'POST' });
      if (response.ok) {
        setQName('');
        setQPhone('');
        fetchData(); 
      }
    } catch (error) { console.error("Queue Error:", error); }
  };

  const seatGuest = async (waitlistId) => {
    const response = await fetch(`/api/queue/seat/${waitlistId}`, { method: 'POST' });
    const result = await response.json();
    if (result.error) alert(result.error); 
    else fetchData(); 
  };

  const getTimeElapsed = (startTime) => {
    if (!startTime) return null;
    const start = new Date(startTime + "Z");
    const diff = Math.floor((new Date() - start) / 60000);
    return diff > 0 ? `${diff}m` : 'Just now';
  };

  if (!role) {
    return (
      <div className="login-screen">
        <div className="login-card fade-in">
          <div style={{display: 'flex', justifyContent: 'flex-end', marginBottom: '-2rem'}}>
            <button className="theme-toggle" onClick={toggleTheme}>
              {theme === 'light' ? '🌙' : '☀️'}
            </button>
          </div>
          <h1 style={{ color: 'var(--primary)', fontSize: '2.5rem', marginBottom: '0.5rem', marginTop: '1rem' }}>🍽️ DineSync Pro</h1>
          <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>Restaurant Management Suite</p>
          <div className="role-grid">
            <button className="role-option" onClick={() => handleLogin('manager')}>
              <div className="role-icon">📊</div>
              <div style={{textAlign: 'left'}}>
                <div style={{fontWeight: 700}}>Admin Manager</div>
                <div style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>Full access to revenue & customers</div>
              </div>
            </button>
            <button className="role-option" onClick={() => handleLogin('floor_manager')}>
              <div className="role-icon">🏢</div>
              <div style={{textAlign: 'left'}}>
                <div style={{fontWeight: 700}}>Floor Manager</div>
                <div style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>Manage table status & cleaning</div>
              </div>
            </button>
            <button className="role-option" onClick={() => handleLogin('receptionist')}>
              <div className="role-icon">📞</div>
              <div style={{textAlign: 'left'}}>
                <div style={{fontWeight: 700}}>Receptionist</div>
                <div style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>Manage waitlist & seating</div>
              </div>
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return <div className="login-screen" style={{background: 'var(--background)', color: 'var(--primary)'}}>Loading System...</div>;

  const isManager = role === 'manager';
  const isFloorManager = role === 'floor_manager';
  const isReceptionist = role === 'receptionist';

  return (
    <div className="app-container">
      <nav className="navbar">
        <div className="nav-brand">🍽️ DineSync</div>
        <div className="nav-links">
          {isManager && (
            <>
              <button onClick={() => setView('dashboard')} className={`nav-btn ${view === 'dashboard' ? 'active' : ''}`}>Dashboard</button>
              <button onClick={() => setView('customers')} className={`nav-btn ${view === 'customers' ? 'active' : ''}`}>Loyalty Program</button>
            </>
          )}
          {isFloorManager && <button className="nav-btn active">Floor Management</button>}
          {isReceptionist && <button className="nav-btn active">Reception Desk</button>}
        </div>
        <div className="nav-user">
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
          <span className={`status-indicator ${isManager ? 'status-available' : isFloorManager ? 'status-occupied' : 'status-dirty'}`} style={{marginBottom: 0}}>
            {role.replace('_', ' ')}
          </span>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </nav>

      {(isManager || isReceptionist) && view !== 'customers' && (
        <header className="matrix-header fade-in">
          <div className="matrix-grid">
            {Object.entries(data.wait_times_detailed || {})
              .filter(([size]) => String(size) !== '8')
              .map(([size, time]) => (
              <div key={size} className="matrix-card">
                <span className="matrix-label">{size}-Seater Wait</span>
                <span className="matrix-value">
                  {time === 0 ? 'READY' : `${time} min`}
                </span>
              </div>
            ))}
            <div className="matrix-card">
              <span className="matrix-label">Live Occupancy</span>
              <span className="matrix-value">{data.occupancy_rate}</span>
            </div>
          </div>
        </header>
      )}

      <main className="fade-in">
        {view === 'dashboard' || view === 'tables' || view === 'waitlist' ? (
          <div className="dashboard-grid" style={{
            gridTemplateColumns: isManager ? '350px 1fr 300px' : isFloorManager ? '1fr' : '350px 1fr'
          }}>
            
            {/* WAITLIST PANEL */}
            {(isManager || isReceptionist) && (
              <div className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">⏳ Live Waitlist</h3>
                </div>
                <div className="panel-content">
                  <form onSubmit={addToQueue} className="waitlist-form">
                    <input className="input-field" style={{gridColumn: 'span 2'}} placeholder="Guest Name" value={qName} onChange={(e) => setQName(e.target.value)} required />
                    <input className="input-field" placeholder="Phone Number" value={qPhone} onChange={(e) => setQPhone(e.target.value)} required />
                    <select className="input-field" value={qSize} onChange={(e) => setQSize(e.target.value)}>
                      {[2,4,6].map(s => <option key={s} value={s}>{s} Guests</option>)}
                    </select>
                    <button type="submit" className="submit-btn">Add to Queue</button>
                  </form>
                  <div className="queue-list">
                    {data.waitlist && data.waitlist.map(q => (
                      <div key={q.waitlist_id} className="queue-item-new">
                        <div>
                          <div style={{fontWeight: 700, color: 'var(--text-main)'}}>{q.customer_name}</div>
                          <div style={{fontSize: '0.75rem', color: 'var(--text-muted)'}}>{q.party_size} Guests • {q.estimated_wait_minutes}m est.</div>
                        </div>
                        <button onClick={() => seatGuest(q.waitlist_id)} className="seat-btn-new">Seat Now</button>
                      </div>
                    ))}
                    {(!data.waitlist || data.waitlist.length === 0) && (
                      <div style={{textAlign: 'center', color: 'var(--text-muted)', marginTop: '2rem'}}>No guests waiting</div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* TABLES GRID */}
            {(isManager || isFloorManager) && (
              <div className="table-grid">
                {data.tables
                  .filter((table) => table.capacity !== 8)
                  .map((table) => (
                  <div key={table.table_id} className="table-card">
                    <div className="table-id">Table {table.table_number}</div>
                    <div className="table-capacity">{table.capacity} Seater</div>
                    <div className={`status-indicator ${
                      table.status === 'Available' ? 'status-available' : 
                      table.status === 'Occupied' ? 'status-occupied' : 'status-dirty'
                    }`}>
                      {table.status}
                    </div>
                    {table.status === 'Occupied' && (
                      <div className="timer-badge">
                        ⏱️ {getTimeElapsed(table.last_updated)}
                      </div>
                    )}
                    <div className="table-actions">
                      {table.status === 'Occupied' ? (
                        (isManager || isFloorManager) && <button onClick={() => handleAction(table, 'pay')} className="action-btn btn-pay">Collect Bill</button>
                      ) : table.status === 'Dirty' ? (
                        <button onClick={() => handleAction(table, 'clean')} className="action-btn btn-clean">Mark Clean</button>
                      ) : (
                        <div className="ready-text">Table Ready</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* TRANSACTIONS PANEL */}
            {isManager && (
              <div className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">🧾 Recent Revenue</h3>
                </div>
                <div className="panel-content">
                  <div className="bill-list">
                    {data.recent_bills && data.recent_bills.map(bill => (
                      <div key={bill.id} className="bill-card-new">
                        <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem'}}>
                          <span style={{fontWeight: 800, color: 'var(--text-main)'}}>₹{bill.total}</span>
                          <span className="pay-tag">PAID</span>
                        </div>
                        <div style={{fontSize: '0.75rem', color: 'var(--text-muted)'}}>{bill.customer}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <CustomersPage />
        )}
      </main>

      {activePayment && (
        <PaymentModal 
          table={activePayment} 
          onConfirm={confirmPayment} 
          onCancel={() => setActivePayment(null)} 
        />
      )}

    </div>
  )
}

export default App;