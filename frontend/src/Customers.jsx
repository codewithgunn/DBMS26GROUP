import React, { useState, useEffect } from 'react';

export default function CustomersPage() {
    const [customers, setCustomers] = useState([]);
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedTag, setSelectedTag] = useState("All");

    useEffect(() => {
        const fetchCustomers = async () => {
            try {
                const response = await fetch(`/api/customers?search=${searchTerm}&tag=${selectedTag}`);
                const data = await response.json();
                setCustomers(data);
            } catch (error) {
                console.error("Failed to fetch customers:", error);
            }
        };

        const delayDebounceFn = setTimeout(() => {
            fetchCustomers();
        }, 300);

        return () => clearTimeout(delayDebounceFn);
    }, [searchTerm, selectedTag]);

    return (
        <div className="customers-container fade-in">
            <div className="page-header-new">
                <div>
                    <h2 style={{fontSize: '2rem', color: 'var(--text-main)', marginBottom: '0.5rem'}}>Loyalty Program</h2>
                    <p style={{color: 'var(--text-muted)'}}>Manage your restaurant's customer base and rewards.</p>
                </div>
            </div>

            <div className="controls-bar">
                <div className="search-wrapper">
                    <span className="search-icon">🔍</span>
                    <input
                        type="text"
                        placeholder="Search by name or phone number..."
                        className="input-field search-input-new"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                <div className="filter-wrapper">
                    <select 
                        className="input-field filter-select-new"
                        value={selectedTag}
                        onChange={(e) => setSelectedTag(e.target.value)}
                    >
                        <option value="All">All Tiers</option>
                        <option value="VIP">🌟 VIP Tier</option>
                        <option value="Regular">🔁 Regular Tier</option>
                        <option value="New">👋 New Members</option>
                    </select>
                </div>
            </div>

            <div className="table-card-new">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>CUSTOMER NAME</th>
                            <th>PHONE NUMBER</th>
                            <th>VISITS</th>
                            <th>LOYALTY POINTS</th>
                            <th>MEMBERSHIP TIER</th>
                        </tr>
                    </thead>
                    <tbody>
                        {customers.length > 0 ? (
                            customers.map((c) => (
                                <tr key={c.customer_id}>
                                    <td className="font-bold">{c.name}</td>
                                    <td>{c.phone}</td>
                                    <td>{c.visit_count}</td>
                                    <td className="points-cell">{c.total_points} pts</td>
                                    <td>
                                        <span className={`tier-badge tier-${(c.cluster_tag || 'New').toLowerCase()}`}>
                                            {c.cluster_tag || 'New'}
                                        </span>
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="5" className="empty-state">
                                    No loyalty members found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            <style dangerouslySetInnerHTML={{__html: `
                .customers-container {
                    padding: 2rem 3rem;
                    max-width: 1600px;
                    margin: 0 auto;
                }
                .page-header-new {
                    margin-bottom: 3rem;
                }
                .controls-bar {
                    display: flex;
                    gap: 1.5rem;
                    margin-bottom: 2.5rem;
                    align-items: center;
                }
                .search-wrapper {
                    position: relative;
                    flex: 5; /* EVEN BIGGER */
                }
                .filter-wrapper {
                    flex: 1;
                    min-width: 200px;
                }
                .search-icon {
                    position: absolute;
                    left: 1.25rem;
                    top: 50%;
                    transform: translateY(-50%);
                    color: var(--text-muted);
                    font-size: 1.1rem;
                }
                .search-input-new {
                    padding-left: 3.5rem !important;
                    height: 3.5rem;
                    font-size: 1rem !important;
                    border-radius: var(--radius-md);
                    background: var(--surface);
                }
                .filter-select-new {
                    width: 100%;
                    height: 3.5rem;
                    font-size: 1rem !important;
                    border-radius: var(--radius-md);
                    background: var(--surface);
                    cursor: pointer;
                    padding: 0 1rem;
                }
                /* Style option elements for dark mode support */
                .filter-select-new option {
                    background-color: var(--surface);
                    color: var(--text-main);
                }
                .table-card-new {
                    background: var(--card-bg);
                    border-radius: var(--radius-lg);
                    border: 1px solid var(--border);
                    overflow: hidden;
                    box-shadow: var(--shadow-md);
                }
                .data-table {
                    width: 100%;
                    border-collapse: collapse;
                }
                .data-table th {
                    text-align: left;
                    padding: 1.25rem 2rem;
                    background: var(--primary-bg);
                    font-size: 0.75rem;
                    font-weight: 800;
                    color: var(--text-muted);
                    border-bottom: 1px solid var(--border);
                    letter-spacing: 0.1em;
                }
                .data-table td {
                    padding: 1.5rem 2rem;
                    border-bottom: 1px solid var(--border);
                    color: var(--text-main);
                }
                .font-bold {
                    font-weight: 700;
                    color: var(--text-main);
                }
                .points-cell {
                    font-weight: 800;
                    color: var(--primary);
                }
                .tier-badge {
                    padding: 0.5rem 1rem;
                    border-radius: 9999px;
                    font-size: 0.75rem;
                    font-weight: 800;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }
                .tier-vip { background: var(--warning-bg); color: var(--warning); }
                .tier-regular { background: var(--primary-bg); color: var(--primary); }
                .tier-new { background: var(--success-bg); color: var(--success); }
                .empty-state {
                    text-align: center;
                    padding: 5rem !important;
                    color: var(--text-muted);
                    font-style: italic;
                }
            `}} />
        </div>
    );
}

