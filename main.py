from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd
import os

app = FastAPI()

DB_PATH = "data/hives.db"
os.makedirs("data", exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS hives
                 (hive_id INTEGER PRIMARY KEY,
                  weight_kg REAL,
                  level INTEGER,
                  extracting BOOLEAN DEFAULT 0,
                  last_update TEXT)''')
    conn.commit()
    conn.close()

init_db()

class HiveData(BaseModel):
    hive: int
    weight_kg: float
    extracting: bool = False

@app.post("/beehive")
async def receive_data(data: HiveData):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    level = round((data.weight_kg / 12) * 100)
    level = max(0, min(100, level))
    c.execute('''INSERT OR REPLACE INTO hives 
                 (hive_id, weight_kg, level, extracting, last_update)
                 VALUES (?, ?, ?, ?, ?)''',
              (data.hive, data.weight_kg, level, data.extracting, now))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/beehive/{hive_id}/harvest-status")
async def harvest_status(hive_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT extracting FROM hives WHERE hive_id = ?", (hive_id,))
    result = c.fetchone()
    conn.close()
    return "true" if result and result[0] else "false"

def run_dashboard():
    st.set_page_config(page_title="SMART NYUKI", layout="wide")
    st.title("🐝 SMART NYUKI - Live Dashboard")

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM hives", conn)
    conn.close()

    if df.empty:
        st.info("Waiting for data from hives...")
    else:
        for _, row in df.iterrows():
            hive_id = row['hive_id']
            weight = row['weight_kg']
            level = row['level']
            extracting = row['extracting']

            with st.container(border=True):
                st.subheader(f"Hive {hive_id}")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.metric("Weight", f"{weight:.2f} kg")
                    st.progress(level / 100)
                    st.caption(f"{level}% full")
                with col2:
                    if level >= 50:
                        if st.button("HARVEST HONEY", key=f"btn_{hive_id}", type="primary"):
                            st.session_state[f"harvest_{hive_id}"] = True
                            st.success("Harvest command sent!")
                    else:
                        st.button("Not Ready", disabled=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--dashboard":
        run_dashboard()
    else:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
