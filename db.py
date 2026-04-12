import psycopg2

# =========================
# DB CONNECTION FUNCTION
# =========================
def get_db_connection():
    return psycopg2.connect(
        dbname="care_ai",
        user="postgres",
        password="your_password",
        host="localhost",
        port="5432"
    )


# =========================
# TABLE CREATION FUNCTION
# =========================
def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()

    # ----------- CARE RECORDS TABLE -----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS care_records (
        id SERIAL PRIMARY KEY,
        resident_name TEXT NOT NULL,
        room_number TEXT DEFAULT 'NA',
        resident_number TEXT DEFAULT 'NA',
        carer_id TEXT NOT NULL,
        observation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # ----------- TASKS TABLE -----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        record_id INTEGER REFERENCES care_records(id) ON DELETE CASCADE,
        carer_id TEXT NOT NULL,
        created_by TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT CHECK (category IN ('Resident', 'Inventory', 'General')),
        priority TEXT CHECK (priority IN ('Critical', 'Important', 'Routine')) DEFAULT 'Routine',
        status TEXT CHECK (status IN ('pending', 'completed')) DEFAULT 'pending',
        escalated_to TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        completed_by_carer TEXT
    );
    """)

    # ----------- INDEXES (for performance) -----------
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_carer ON tasks(carer_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);")

    conn.commit()
    cur.close()
    conn.close()


# =========================
# OPTIONAL: AUTO RUN
# =========================
if __name__ == "__main__":
    print("Creating tables...")
    create_tables()
    print("Tables created successfully!")