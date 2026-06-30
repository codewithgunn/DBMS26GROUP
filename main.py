import os
import datetime
import random
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from fastapi.middleware.cors import CORSMiddleware

# --- DATABASE SETUP ---
current_user = os.getenv("USER") 
DATABASE_URL = f"postgresql://{current_user}@localhost/dinesync"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELS ---

class CustomerDB(Base):
    __tablename__ = "customers"
    customer_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, unique=True, index=True)
    total_points = Column(Integer, default=0)
    visit_count = Column(Integer, default=1)
    cluster_tag = Column(String, default="New")
    reservations = relationship("ReservationDB", back_populates="customer")
    bills = relationship("BillDB", back_populates="customer")

class TableDB(Base):
    __tablename__ = "tables"
    table_id = Column(Integer, primary_key=True, index=True)
    table_number = Column(Integer, unique=True)
    capacity = Column(Integer)
    status = Column(String, default="Available") 
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

class ReservationDB(Base):
    __tablename__ = "reservations"
    reservation_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"))
    table_id = Column(Integer, ForeignKey("tables.table_id"), nullable=True)
    reservation_time = Column(DateTime)
    party_size = Column(Integer)
    status = Column(String, default="Confirmed")
    customer = relationship("CustomerDB", back_populates="reservations")

class WaitlistDB(Base):
    __tablename__ = "waitlist" 
    waitlist_id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String)
    party_size = Column(Integer)
    phone = Column(String)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)
    estimated_wait_minutes = Column(Integer, default=0)

class BillDB(Base):
    __tablename__ = "bills"
    bill_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=True)
    table_id = Column(Integer, ForeignKey("tables.table_id"))
    subtotal = Column(Float)
    loyalty_discount = Column(Float, default=0.0)
    final_total = Column(Float)
    payment_status = Column(String, default="Pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    customer = relationship("CustomerDB", back_populates="bills")

class LoyaltyRedemptionDB(Base):
    __tablename__ = "loyalty_redemptions"
    redemption_id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.bill_id"))
    customer_id = Column(Integer, ForeignKey("customers.customer_id"))
    points_redeemed = Column(Integer)
    discount_amount = Column(Float)
    redeemed_at = Column(DateTime, default=datetime.datetime.utcnow)

# WIPE EVERYTHING and start fresh — controlled by RESET_DB env var (default: true, preserves
# the existing demo workflow in cmd.txt). Set RESET_DB=false to keep data across restarts.
RESET_DB = os.getenv("RESET_DB", "true").lower() == "true"
if RESET_DB:
    Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- REQUEST BODY MODELS (replaces raw query params) ---
class WaitlistCreate(BaseModel):
    name: str
    size: int
    phone: str

class PaymentCreate(BaseModel):
    amount: float
    phone: str
    name: str = "Guest"

# --- ROLE ENFORCEMENT ---
# Frontend must send an `X-Role` header (e.g. "Receptionist", "Floor Manager", "Manager")
# matching whichever role the logged-in user selected client-side.
VALID_ROLES = {"Manager", "Floor Manager", "Receptionist"}

def require_role(*allowed_roles: str):
    def checker(x_role: str = Header(None)):
        if x_role not in VALID_ROLES:
            raise HTTPException(status_code=401, detail="Missing or invalid X-Role header")
        if x_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{x_role}' is not permitted to access this endpoint. Allowed: {allowed_roles}"
            )
        return x_role
    return checker

@app.get("/")
def home():
    return {"status": "DineSync Backend is running", "api_docs": "/docs"}

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- HELPER: UPGRADED SMART TIME PREDICTION ALGO ---
def calculate_smart_wait(db: Session, party_size: int):
    import joblib
    import os

    # 1. Dynamic Dining Times (Larger parties stay longer!)
    if party_size <= 2:
        target_capacity = 2
        avg_dining_time = 45
    elif party_size <= 4:
        target_capacity = 4
        avg_dining_time = 60
    else:
        target_capacity = 6
        avg_dining_time = 75

    CLEANING_BUFFER = 5  # 5 minutes to bus and clean a table

    # 2. Find tables matching this capacity category
    tables = db.query(TableDB).filter(TableDB.capacity == target_capacity).all()
    if not tables:
        return 99  # No tables exist for this size

    # 3. Count people ahead in the queue for this specific table size
    people_ahead = 0
    waitlist = db.query(WaitlistDB).all()
    for w in waitlist:
        if (w.party_size <= 2 and target_capacity == 2) or \
           (2 < w.party_size <= 4 and target_capacity == 4) or \
           (w.party_size > 4 and target_capacity == 6):
            people_ahead += 1

    # 4. Build a "Ready Time" timeline for all tables of this size
    # This list will store how many minutes from now each table will be ready for a NEW guest.
    timeline = []
    now = datetime.datetime.utcnow()
    
    for t in tables:
        if t.status == "Available":
            timeline.append(0)
        elif t.status == "Dirty":
            timeline.append(CLEANING_BUFFER)
        else: # Occupied
            elapsed_minutes = (now - t.last_updated).total_seconds() / 60
            remaining = max(0, avg_dining_time - elapsed_minutes)
            timeline.append(remaining + CLEANING_BUFFER)
            
    timeline.sort()

    # 5. Calculate wait based on the timeline
    num_tables = len(timeline)
    if num_tables == 0: return 15
    
    # The 'people_ahead'-th person takes the 'people_ahead % num_tables' table
    # but they might have to wait for multiple 'cycles' of that table.
    table_index = people_ahead % num_tables
    cycles = people_ahead // num_tables
    
    cycle_time = avg_dining_time + CLEANING_BUFFER
    base_prediction = timeline[table_index] + (cycles * cycle_time)

    # 6. AI Refinement (Random Forest)
    try:
        model_path = os.path.join(os.path.dirname(__file__), "dinesync_brain.pkl")
        if os.path.exists(model_path):
            import pandas as pd
            model = joblib.load(model_path)
            
            # Prepare contextual features
            now = datetime.datetime.now()
            total_occupied = db.query(TableDB).filter(TableDB.status == "Occupied").count()
            
            # Create a DataFrame with correct feature names for the model
            test_input = pd.DataFrame([[
                now.weekday(),     # day_of_week
                now.hour,          # hour_of_day
                party_size,        # party_size
                total_occupied,    # occupied_tables
                people_ahead       # waitlist_count (specific to this capacity)
            ]], columns=['day_of_week', 'hour_of_day', 'party_size', 'occupied_tables', 'waitlist_count'])
            
            ai_prediction = model.predict(test_input)[0]
            
            # Blend: 60% Heuristic (exact table state), 
            # ns)
            final_wait = (base_prediction * 0.6) + (ai_prediction * 0.4)
            return int(final_wait)
    except Exception as e:
        print(f"⚠️ AI Prediction Skip: {e}")

    return int(base_prediction)

# --- SEEDER  ---
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    if db.query(TableDB).count() == 0:
        print("🌱 Seeding Database with Tables...")
        tables = []
        for i in range(1, 21):
            if i <= 8: cap = 2      
            elif i <= 16: cap = 4   
            else: cap = 6           

            if i <= 5:
                status = "Available"
                last_updated = datetime.datetime.utcnow()
            else:
                status = random.choice(["Occupied", "Occupied", "Dirty", "Available"])
                last_updated = datetime.datetime.utcnow() - timedelta(minutes=random.randint(5, 45))

            tables.append(TableDB(table_number=i, capacity=cap, status=status, last_updated=last_updated))
        
        db.add_all(tables)
        
        # --- NEW DUMMY DATA: 20 DIFFERENT CUSTOMERS ---
        print("👥 Seeding 20 Unique Customers...")
        names = [
            "Rahul VIP", "Aditi", "Krish", "Aanya", "Gunneet", "Karan", "Priya", "Rohan", "Sneha", "Vikram",
            "Anjali", "Siddharth", "Neha", "Arjun", "Meera", "Kabir", "Pooja", "Aakash", "Riya", "Nikhil"
        ]
        
        customers = []
        for i in range(20):
            # Create varied data so the pie chart and tables look realistic
            points = random.choice([50, 150, 400, 850, 1200, 2500, 4500, 100, 600])
            visits = random.randint(1, 12)
            
            if points > 1000: tag = "VIP"
            elif visits > 5: tag = "Regular"
            else: tag = "New"
            
            # Make sure every phone number is unique
            unique_phone = f"999000{i:02d}" 
            
            c = CustomerDB(
                name=names[i], 
                phone=unique_phone, 
                total_points=points, 
                cluster_tag=tag, 
                visit_count=visits
            )
            customers.append(c)
            
        db.add_all(customers)
        db.commit() 
        
        for c in customers:
            db.refresh(c)

        print("🧾 Seeding 20 Past Transactions (One for each person)...")
        for i in range(20):
            random_amount = random.choice([850, 1200, 2400, 450, 3100, 1500, 650, 4200])
            
            new_bill = BillDB(
                customer_id=customers[i].customer_id, 
                table_id=random.randint(1, 20), # Added missing table_id
                subtotal=random_amount,
                final_total=random_amount,
                payment_status="Paid"
            )
            db.add(new_bill)
            
        db.add(WaitlistDB(customer_name="Simran", party_size=4, phone="123456", estimated_wait_minutes=15))
        
        db.commit()
        print("✅ Database Ready: 20 Unique Customers Inserted!")
    db.close()

# --- ENDPOINTS ---

@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    tables = db.query(TableDB).order_by(TableDB.table_number).all()
    waitlist = db.query(WaitlistDB).order_by(WaitlistDB.joined_at).all()
    customers = db.query(CustomerDB).order_by(CustomerDB.total_points.desc()).all()
    recent_bills = db.query(BillDB).order_by(BillDB.created_at.desc()).limit(10).all()
    
    bill_data = []
    for b in recent_bills:
        c_name = b.customer.name if b.customer else "Guest"
        bill_data.append({"id": b.bill_id, "customer": c_name, "total": b.final_total, "status": b.payment_status, "created_at": b.created_at})

    occupied = sum(1 for t in tables if t.status == 'Occupied')
    occ_rate = f"{int((occupied / len(tables)) * 100)}%" if tables else "0%"
    
    # Updated to pass 'db' session into the smart calculation
    wait_times = {str(s): calculate_smart_wait(db, s) for s in [2, 4, 6]}
    
    segment_counts = {}
    for c in customers:
        tag = c.cluster_tag or "New"
        segment_counts[tag] = segment_counts.get(tag, 0) + 1
    chart_data = [{"name": k, "value": v} for k, v in segment_counts.items()] or [{"name": "No Data", "value": 1}]

    return {
        "tables": tables,
        "waitlist": waitlist,
        "recent_bills": bill_data,
        "occupancy_rate": occ_rate,
        "wait_times_detailed": wait_times,
        "customer_list": customers,
        "chart_data": chart_data
    }

@app.get("/api/transactions")
def get_transactions(
    phone: str = "",
    db: Session = Depends(get_db),
    role: str = Depends(require_role("Manager"))
):
    query = db.query(BillDB)
    if phone:
        query = query.join(CustomerDB).filter(CustomerDB.phone == phone)
    bills = query.order_by(BillDB.created_at.desc()).all()
    
    bill_data = []
    for b in bills:
        c_name = b.customer.name if b.customer else "Guest"
        c_phone = b.customer.phone if b.customer else "N/A"
        bill_data.append({
            "id": b.bill_id, 
            "customer": c_name, 
            "phone": c_phone,
            "total": b.final_total, 
            "status": b.payment_status, 
            "created_at": b.created_at
        })
    return bill_data

@app.get("/api/customers")
def get_customers(
    search: str = "",
    tag: str = "All",
    db: Session = Depends(get_db),
    role: str = Depends(require_role("Manager"))
):
    # Start with a base query
    query = db.query(CustomerDB)
    
    # 1. SQL SEARCH: Use ILIKE for case-insensitive partial matching
    if search:
        query = query.filter(
            or_(
                CustomerDB.name.ilike(f"%{search}%"),
                CustomerDB.phone.ilike(f"%{search}%")
            )
        )
        
    # 2. SQL FILTER: Exact match on the cluster tag
    if tag and tag != "All":
        query = query.filter(CustomerDB.cluster_tag == tag)
        
    # 3. Sort by most points and execute the SQL query
    customers = query.order_by(CustomerDB.total_points.desc()).all()
    
    return customers

@app.post("/api/queue/add")
def add_to_waitlist(
    payload: WaitlistCreate,
    db: Session = Depends(get_db),
    role: str = Depends(require_role("Receptionist", "Manager"))
):
    # Updated to use the smart time prediction based on the database state
    est_wait = calculate_smart_wait(db, payload.size)
    db.add(WaitlistDB(customer_name=payload.name, party_size=payload.size, phone=payload.phone, estimated_wait_minutes=est_wait))
    db.commit()
    return {"message": "Added"}

@app.post("/api/queue/seat/{waitlist_id}")
def seat_guest(
    waitlist_id: int,
    db: Session = Depends(get_db),
    role: str = Depends(require_role("Receptionist", "Manager"))
):
    guest = db.query(WaitlistDB).filter(WaitlistDB.waitlist_id == waitlist_id).first()
    if not guest: 
        print(f"❌ Guest ID {waitlist_id} not found in DB")
        return {"error": "Guest not found"}

    table = db.query(TableDB).filter(TableDB.status == "Available", TableDB.capacity >= guest.party_size).first()
    
    if not table:
        print(f"❌ No table found for party size {guest.party_size}")
        return {"error": f"No Available Table for size {guest.party_size}. Clean a table first!"}

    print(f"✅ Seating {guest.customer_name} at Table {table.table_number}")
    table.status = "Occupied"
    table.last_updated = datetime.datetime.utcnow()
    
    db.delete(guest)
    db.commit()
    return {"message": f"Seated at Table {table.table_number}"}

@app.post("/api/tables/{table_id}/pay")
def pay_bill(
    table_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    role: str = Depends(require_role("Floor Manager", "Manager"))
):
    print(f"💰 Processing Payment: {payload.amount} for Phone: {payload.phone}")
    table = db.query(TableDB).filter(TableDB.table_id == table_id).first()

    clean_phone = payload.phone.strip()
    customer = db.query(CustomerDB).filter(CustomerDB.phone == clean_phone).first()

    if not customer:
        print(f"🆕 Creating NEW Customer profile for {clean_phone}")
        customer = CustomerDB(name=payload.name, phone=clean_phone, total_points=0, visit_count=0, cluster_tag="New")
        db.add(customer)
        db.flush()
    else:
        print(f"👋 Found EXISTING Customer: {customer.name}. Current Points: {customer.total_points}")
        if payload.name != "Guest": customer.name = payload.name

    points_earned = int(payload.amount * 0.10)
    customer.total_points += points_earned
    customer.visit_count += 1

    print(f"📈 Points Updated! New Balance: {customer.total_points}")

    if customer.total_points > 1000: customer.cluster_tag = "VIP"
    elif customer.visit_count > 5: customer.cluster_tag = "Regular"
    else: customer.cluster_tag = "New"

    new_bill = BillDB(
        customer_id=customer.customer_id,
        table_id=table_id,
        subtotal=payload.amount,
        final_total=payload.amount,
        payment_status="Paid"
    )

    table.status = "Dirty"
    db.add(new_bill)
    db.commit()

    return {"message": "Paid", "points_earned": points_earned}

@app.post("/api/tables/{table_id}/clean")
def clean_table(
    table_id: int,
    db: Session = Depends(get_db),
    role: str = Depends(require_role("Floor Manager", "Manager"))
):
    table = db.query(TableDB).filter(TableDB.table_id == table_id).first()
    table.status = "Available"
    db.commit()
    return {"message": "Table Cleaned"}