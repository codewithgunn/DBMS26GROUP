# 🍽️ DineSync — AI-Powered Restaurant Management System

A full-stack restaurant operations platform combining real-time table management, customer loyalty tracking, and machine learning–driven wait-time prediction.

![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React%2019-Frontend-61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E)

## 📋 Table of Contents
- [Overview](#-overview)
- [Key Features](#-key-features)
- [User Roles & Permissions](#-user-roles--permissions)
- [Machine Learning Engine](#-machine-learning-engine)
- [Authentication & Security](#-authentication--security)
- [Table & Waitlist Management](#-table--waitlist-management)
- [Loyalty Program](#-loyalty-program)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Setup Instructions](#-setup-instructions)
- [API Endpoints](#-api-endpoints)

## 🎯 Overview

DineSync is a Database Management System (DBMS) project that streamlines day-to-day restaurant operations through three role-specific dashboards: **Manager**, **Floor Manager**, and **Receptionist**. The platform unifies live table status, a smart waitlist, customer loyalty tracking, and revenue reporting into one system, with a hybrid ML/heuristic engine predicting guest wait times in real time.

### Core Concept
- **Receptionists** add walk-in guests to the waitlist and seat them once a table opens up
- **Floor Managers** track live table status (Available / Occupied / Dirty) and process payments
- **Managers** get full visibility: revenue trends, loyalty program analytics, and the live floor view
- An ML-powered prediction engine estimates wait times based on current occupancy, queue length, and historical demand patterns

## ✨ Key Features

### 🔐 Authentication & Security
- Role-based login (Manager / Floor Manager / Receptionist) with persisted session via `localStorage`
- Server-side role enforcement via `X-Role` header middleware — every protected endpoint validates the caller's role before executing
- Manager-only access to sensitive endpoints (customer PII, revenue/transaction history)
- CORS-enabled API for local frontend/backend separation

### 📊 Live Dashboard
- Real-time table grid (2/4/6-seater) with status indicators: Available, Occupied, Dirty
- Live occupancy rate calculation
- Per-table-size wait-time matrix (e.g., "2-Seater Wait: 12 min")
- Auto-refreshing data (polled every 4 seconds)
- Light/Dark theme toggle with persisted preference

### ⏳ Smart Waitlist Management
- Add guests to the queue with name, phone, and party size
- One-click "Seat Now" action that assigns the next available table
- Live estimated wait time per guest, computed at the moment they join the queue
- Automatic table-readiness simulation based on current occupancy

### 🧮 Table Lifecycle Management
- Full table status lifecycle: **Available → Occupied → Dirty → Available**
- "Collect Bill" action (Floor Manager / Manager) triggers payment + loyalty point accrual
- "Mark Clean" action resets a dirty table to available
- Elapsed-time badge showing how long a table has been occupied

### 🏆 Loyalty Program (Customers Page)
- Automatic customer profile creation on first payment (matched by phone number)
- Points accrual: 10% of bill total awarded as loyalty points
- Rule-based tier segmentation:
  - **New** — default tier
  - **Regular** — 5+ visits
  - **VIP** — 1,000+ accumulated points
- Searchable, filterable customer table (by name/phone and tier)

### 🧾 Revenue & Transactions
- Recent bills feed on the Manager dashboard
- Full transaction history lookup by customer phone (Manager-only)
- Payment status tracking

## 👥 User Roles & Permissions

| Role | Dashboard Access | Key Actions |
|---|---|---|
| **Manager** | Dashboard, Tables, Waitlist, Loyalty Program, Revenue | Full read/write access across the system |
| **Floor Manager** | Tables view | Collect payments, mark tables clean |
| **Receptionist** | Waitlist view | Add guests to queue, seat waiting guests |

Permissions are enforced **server-side**, not just hidden in the UI — each protected FastAPI endpoint checks the `X-Role` header against an allow-list before executing.

## 🧠 Machine Learning Engine

DineSync predicts guest wait times using a **hybrid model**: a deterministic table-availability heuristic blended with a trained Random Forest Regressor.

```
final_wait_estimate = 0.6 × heuristic_prediction + 0.4 × ML_prediction
```

- **Heuristic**: simulates the live readiness timeline of each table size given current occupancy and queue position
- **ML Model**: `RandomForestRegressor` (scikit-learn, 100 estimators) trained on 5 engineered features — day of week, hour of day, party size, occupied tables, and waitlist length
- **Training data**: ~5,000 synthetic historical records generated with decorrelated, continuous feature distributions to avoid artificial collinearity
- **Validated performance** (held-out 20% test set): **MAE ≈ 3.78 minutes, R² ≈ 0.953**
- Feature importance assessed via **permutation importance** (more robust to correlated features than default impurity-based importance)
- Falls back gracefully to 100% heuristic if the model file is missing or fails to load

## 🚚 Table & Waitlist Management

See [Table Lifecycle Management](#-table-lifecycle-management) above — table state transitions and queue handling are the operational core of the Floor Manager and Receptionist dashboards.

## 💳 Payment Integration

- Manual bill entry (amount, customer phone, customer name) via a payment modal
- Automatic loyalty point calculation on payment confirmation
- Table automatically flips to "Dirty" status post-payment, prompting a cleaning action

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI (Python) |
| **Database** | PostgreSQL + SQLAlchemy ORM |
| **ML/AI** | scikit-learn (Random Forest Regressor) |
| **Frontend** | React 19 + Vite 7 |
| **Charts** | Recharts |
| **Styling** | Custom CSS (Glassmorphism, light/dark theming) |

## 📁 Project Structure

```
DBMS26GROUP-main/
├── main.py                # FastAPI backend — schema, endpoints, role enforcement
├── train_model.py         # Trains the Random Forest model on historical data
├── seed_history.py        # Seeds synthetic historical data for ML training
├── dinesync_brain.pkl     # Saved, trained ML model
├── requirements.txt       # Python dependencies
├── cmd.txt                # Quick-start terminal commands
├── README.md
└── frontend/
    ├── src/
    │   ├── App.jsx         # Main UI, role-based routing, dashboard
    │   ├── Customers.jsx   # Loyalty program / customer management
    │   ├── App.css
    │   ├── index.css
    │   └── main.jsx
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (running locally with a `dinesync` database created)

### 1. Backend Setup
```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed historical data for the ML model
python seed_history.py

# (Optional) Retrain the model on fresh seed data
python train_model.py

# Start the API server
uvicorn main:app --reload --port 8000
```
The API will be available at `http://localhost:8000` (interactive docs at `/docs`).

> **Note:** The database resets on every restart by default (`RESET_DB=true`). Set `RESET_DB=false` to preserve data across restarts.

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev -- --host
```
The UI will be available at `http://localhost:5173`.

## 🔌 API Endpoints

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/dashboard` | Live table status, waitlist, wait-time matrix | All roles |
| `GET` | `/api/customers` | Loyalty member list (search/filter) | Manager |
| `GET` | `/api/transactions` | Billing/transaction history | Manager |
| `POST` | `/api/queue/add` | Add a guest to the waitlist | Receptionist, Manager |
| `POST` | `/api/queue/seat/{waitlist_id}` | Seat a waiting guest | Receptionist, Manager |
| `POST` | `/api/tables/{table_id}/pay` | Process payment for a table | Floor Manager, Manager |
| `POST` | `/api/tables/{table_id}/clean` | Mark a table as cleaned | Floor Manager, Manager |

---

Developed by **Group 26** for the DBMS Project.