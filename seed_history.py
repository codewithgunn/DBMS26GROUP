import os
import math
import datetime
import random
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- MINIMAL MODELS FOR SEEDING ---
Base = declarative_base()

class HistoricalWaitDB(Base):
    __tablename__ = "historical_waits"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    day_of_week = Column(Integer)  # 0-6
    hour_of_day = Column(Integer)  # 0-23
    party_size = Column(Integer)
    occupied_tables = Column(Integer)
    waitlist_count = Column(Integer)
    actual_wait_minutes = Column(Float)

# Connection setup
current_user = os.getenv("USER")
DATABASE_URL = f"postgresql://{current_user}@localhost/dinesync"
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Graded day-of-week multiplier (Mon=0 ... Sun=6) instead of a flat weekday/weekend
# binary. Gives day_of_week real, independent signal rather than just duplicating
# whatever "is_weekend" would have encoded.
DAY_MULTIPLIER = [0.90, 0.85, 0.92, 1.00, 1.15, 1.35, 1.30]


def hour_busyness(hour):
    """Smooth, continuous busyness curve with a lunch peak (~1pm) and dinner peak
    (~7:30pm), instead of a single binary is_peak flag. Returns roughly 0.0 (quiet)
    to ~1.1 (peak). Other features are driven off this curve but each gets its own
    independent noise term below, so they end up correlated with hour_of_day (as
    real restaurant data would be) without being deterministic proxies for it."""
    lunch = math.exp(-((hour - 13.0) ** 2) / (2 * 1.4 ** 2))
    dinner = math.exp(-((hour - 19.5) ** 2) / (2 * 1.8 ** 2))
    return lunch + dinner


def generate_history():
    print("📊 Generating ~3,000+ entries of historical dining data (decorrelated features)...")
    db.query(HistoricalWaitDB).delete()

    start_date = datetime.datetime.now() - datetime.timedelta(days=45)
    data = []

    for day in range(45):
        current_date = start_date + datetime.timedelta(days=day)
        dow = current_date.weekday()
        day_mult = DAY_MULTIPLIER[dow]

        for hour in range(11, 23):
            busy = hour_busyness(hour)

            # Number of groups walking in this hour: driven by busyness + day
            # multiplier, plus independent randomness so it's not a pure function
            # of hour alone.
            base_groups = 3 + busy * 9 * day_mult
            num_groups = max(1, int(round(random.gauss(base_groups, 2.0))))

            for _ in range(num_groups):
                party_size = random.choice([2, 2, 2, 3, 4, 4, 5, 6])

                # Occupied tables: driven by busyness, but with its OWN independent
                # noise term (std=3.0) so it's not a perfect copy of waitlist_count.
                occ_tables = 5 + busy * 13 * day_mult + random.gauss(0, 3.0)
                occ_tables = int(min(20, max(0, round(occ_tables))))

                # Waitlist count: also driven by busyness, but with a DIFFERENT
                # scale and a SEPARATE independent noise source (std=1.8).
                wl_count = busy * 7 * day_mult + random.gauss(0, 1.8)
                wl_count = int(min(15, max(0, round(wl_count))))

                # Ground-truth wait time. Coefficients are deliberately closer in
                # magnitude (no single feature contributes an order of magnitude
                # more than the others), and there's a genuinely independent
                # observation-noise term per row.
                wait = 4.0
                wait += party_size * 1.8
                wait += occ_tables * 1.6
                wait += wl_count * 2.6
                wait *= day_mult
                wait += busy * 6.0              # small direct time-of-day effect
                wait += random.gauss(0, 4.0)    # independent noise
                wait = max(0, wait)

                entry = HistoricalWaitDB(
                    timestamp=current_date.replace(hour=hour, minute=random.randint(0, 59)),
                    day_of_week=dow,
                    hour_of_day=hour,
                    party_size=party_size,
                    occupied_tables=occ_tables,
                    waitlist_count=wl_count,
                    actual_wait_minutes=round(wait, 2)
                )
                db.add(entry)

    db.commit()
    print("✅ Historical data seeded successfully!")


if __name__ == "__main__":
    generate_history()