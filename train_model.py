import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
from sklearn.inspection import permutation_importance
from sqlalchemy import create_engine
import joblib
import os

# --- DATABASE SETUP ---
current_user = os.getenv("USER")
DATABASE_URL = f"postgresql://{current_user}@localhost/dinesync"
engine = create_engine(DATABASE_URL)

print("🧠 DineSync AI: Loading training data from Postgres...")

# 1. READ FROM THE HISTORICAL DATA TABLE
query = "SELECT day_of_week, hour_of_day, party_size, occupied_tables, waitlist_count, actual_wait_minutes FROM historical_waits"
df = pd.read_sql(query, engine)

print(f"✅ Loaded {len(df)} records for training.")

# 2. DEFINE FEATURES AND TARGET
# Features: [DayOfWeek, HourOfDay, PartySize, OccupiedTables, WaitlistLength]
X = df[['day_of_week', 'hour_of_day', 'party_size', 'occupied_tables', 'waitlist_count']]
y = df['actual_wait_minutes']

# 2b. TRAIN/TEST SPLIT — hold out 20% so we can report a real, unbiased accuracy number
# instead of evaluating on data the model has already memorized.
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"📐 Split: {len(X_train)} training rows / {len(X_test)} held-out test rows.")

# 3. TRAIN A MORE SOPHISTICATED MODEL (Random Forest)
print("🏗️  Training Random Forest Regressor...")
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 3b. EVALUATE ON THE HELD-OUT TEST SET
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("📊 Held-out test set performance:")
print(f"   - MAE  (Mean Absolute Error): {mae:.2f} minutes")
print(f"   - RMSE (Root Mean Sq. Error): {rmse:.2f} minutes")
print(f"   - R²   (Variance Explained):  {r2:.3f}")

# 3c. PERMUTATION IMPORTANCE — more robust than impurity-based importance when features
# are correlated (waitlist_count, occupied_tables, and hour_of_day are all proxies for
# "is this a peak period?", which skews impurity-based importance toward whichever one
# the trees happen to split on first). This measures importance directly: how much
# performance drops on the held-out test set when each feature is shuffled. Must run
# BEFORE the full-data refit below, while X_test is still genuinely unseen by the model.
print("🔍 Permutation importance (on held-out test set):")
perm = permutation_importance(model, X_test, y_test, n_repeats=20, random_state=42)
perm_series = pd.Series(perm.importances_mean, index=X.columns).sort_values(ascending=False)
for feature, score in perm_series.items():
    print(f"   - {feature}: {score:.3f}")

print("ℹ️  (Note: tree-based feature_importances_ would show a different, more skewed")
print("    picture here because waitlist_count, occupied_tables, and hour_of_day are")
print("    correlated proxies for peak hours in the synthetic data.)")

# 3d. RETRAIN ON THE FULL DATASET for the production model that actually gets saved
# (standard practice: evaluate + measure importance on the split, but ship a model
# trained on all available data for best real-world performance)
model.fit(X, y)

# 4. SAVE THE MODEL
joblib.dump(model, "dinesync_brain.pkl")
print("🚀 Model successfully upgraded to RANDOM FOREST!")
print("   - This model now understands peak hours, weekend surges, and party sizes.")

# Example test
test_input = pd.DataFrame([[5, 19, 4, 15, 5]], columns=['day_of_week', 'hour_of_day', 'party_size', 'occupied_tables', 'waitlist_count'])
prediction = model.predict(test_input)[0]
print(f"   - Test Case (Sat @ 7PM, 4 People, Busy): Predicted Wait {prediction:.1f} mins")