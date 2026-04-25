# DineSync: AI-Powered Restaurant Management System

DineSync is a modern Database Management System (DBMS) designed to streamline restaurant operations through real-time table management, customer loyalty tracking, and AI-driven wait-time predictions.

## 🚀 Technical Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React 19 + Vite
- **Database:** PostgreSQL + SQLAlchemy ORM
- **AI/ML:** Scikit-learn (Random Forest)

## 📁 Project Structure & Files

### Backend & Core Logic
- **`main.py`**: The core FastAPI backend. Defines the PostgreSQL database schema and handles RESTful API requests.
- **`train_model.py`**: Trains the Random Forest model on historical data to predict guest wait times.
- **`seed_history.py`**: Seeds the database with synthetic historical data for the AI engine.
- **`dinesync_brain.pkl`**: The saved AI model used for real-time predictions.
- **`requirements.txt`**: Python dependencies.
- **`cmd.txt`**: Quick-start guide with terminal commands for setup and execution.

### Frontend (React)
- **`frontend/src/App.jsx`**: Main UI entry point with role-based access control (Manager, Floor Manager, Receptionist).
- **`frontend/src/Customers.jsx`**: Loyalty program management and customer segmentation.
- **`frontend/src/App.css`**: Custom "Glassmorphism" styling and interactive UI components.

## 🔑 User Roles
- **Manager**: Analytics dashboard, revenue trends, and customer insights.
- **Floor Manager**: Real-time table status updates and seating management.
- **Receptionist**: Reservation handling and AI-assisted waitlist management.

---
Developed by **Group 26** for the DBMS Project.
