from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI                                                   
import json
import psycopg2                                                             
from psycopg2.extras import RealDictCursor
import shutil
import os
from typing import List, Optional
from pydantic import BaseModel                                              
import uuid
from datetime import datetime, timedelta
from db import get_db_connection

client = OpenAI()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                # tells the server to accept requests from any website or origin.
    allow_credentials=True,             # allows the browser to send sensitive information along with the request.
    allow_methods=["*"],                # any type of HTTP request is allowed
    allow_headers=["*"],                # to send any custom metadata
)           

# This block of code configures Cross-Origin Resource Sharing (CORS), 
# which is a security feature implemented by web browsers.


# --------------------------------------DATA VALIDATION MODELS (PYDANTIC)------------------------------------------

class TaskDetail(BaseModel):
    description: str
    priority: str 
    category: str 

class CareRecord(BaseModel):
    resident_name: str
    room_number: Optional[str] = "NA"
    resident_number: Optional[str] = "NA"
    summary_of_visit: str
    extracted_tasks: List[TaskDetail] 


# ---------------------------------------SHIFT STRUCTURE FOR TASK ROUTING-------------------------------------

SHIFT_ROTATION = {
    "MOR": {"next": "AFT", "res_map": {"C-MOR-01": "C-AFT-04", "C-MOR-02": "C-AFT-05"}, "gen": "C-AFT-06"},
    "AFT": {"next": "NIG", "res_map": {"C-AFT-04": "C-NIG-07", "C-AFT-05": "C-NIG-08"}, "gen": "C-NIG-09"},
    "NIG": {"next": "MOR", "res_map": {"C-NIG-07": "C-MOR-01", "C-NIG-08": "C-MOR-02"}, "gen": "C-MOR-03"}
}

# -------------------------------------Shift-Based Task Routing Logic-----------------------------------------

# Decides to whom the tasks should be allocated

def get_handover_carer(current_carer_id: str, task_type: str):
    try:
        parts = current_carer_id.split('-')
        shift_key = parts[1]
        shift_data = SHIFT_ROTATION[shift_key]
        if task_type == "Resident":
            return shift_data["res_map"].get(current_carer_id, shift_data["gen"])
        return shift_data["gen"]
    except:
        return current_carer_id
    
# --------------------------------------FORMATS EXTRACTED TASKS---------------------------------------

# It takes the raw JSON object received from the AI and 
# transforms it into a list of specific, actionable tasks that the database can understand.

def detect_tasks(record: dict, upload_carer_id: str):
    tasks = []
    res_name = record.get('resident_name', 'Unknown Resident')
    
    for item in record.get("extracted_tasks", []):

        target = get_handover_carer(upload_carer_id, item['category'])

        desc = f"{res_name}: {item['description']}" if item['category'] == "Resident" else item['description']
        
        tasks.append({
            "desc": desc,
            "type": item['category'],
            "carer": target,
            "creator": upload_carer_id,
            "priority": item.get('priority', 'Routine')
        })
    return tasks

## ========================================= API ENDPOINTS ================================================

# -----------------------------AI Processing Pipeline (Transcription & Extraction)-------------------------

@app.post("/upload/")
async def upload_audio(file: UploadFile = File(...), carer_id: str = Form(...)):

    file_path = f"temp_{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    # Creates a temporary file name with a unique ID (UUID). 
    # This is clever because it prevents two carers from overwriting 
    # each other's files if they upload at the exact same second.

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)                   # reads the file in small chunks and writes them to the disk.
    try:
        with open(file_path, "rb") as f:
            # STT
            transcript = client.audio.transcriptions.create(model="whisper-1", file=f, response_format="text")      
        
        # LLM
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": """Extract clinical tasks into JSON. 
                    PRIORITIES: 'Critical', 'Important', 'Routine'.
                    RULES: Use resident name from transcript. 
                    Categorize clinical supplies as 'Inventory', Specific Resident related as 'Resident', Other than these as 'General'"""
                },
                {"role": "user", "content": f"Transcript: {transcript}"}
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "care_record", "schema": CareRecord.model_json_schema()}}
        )
        
        # Text to JSON Format
        record = json.loads(response.choices[0].message.content)

        # detects the tasks using function
        tasks = detect_tasks(record, carer_id)
        
        # Saves to db
        with get_db_connection() as conn:
            with conn.cursor() as cur:

                # Summary of Shift Notes
                cur.execute("""
                    INSERT INTO care_records (resident_name, room_number, resident_number, carer_id, observation)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                """, (record['resident_name'], record['room_number'], record['resident_number'], carer_id, record['summary_of_visit']))
                
                rid = cur.fetchone()[0]     # id of the record created above

                for t in tasks:
                    # Created record of each task
                    cur.execute("""
                        INSERT INTO tasks (record_id, carer_id, created_by, description, category, priority) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (rid, t['carer'], t['creator'], t['desc'], t['type'], t['priority']))
                
                conn.commit()
        
        return {"transcript": transcript, "record": record}             # returned for the purpose of displaying in the Frontend
    
    finally:
        if os.path.exists(file_path): os.remove(file_path)              # The temp file is deleted.

# -------------------------------------------ACTIVE TASKS---------------------------------------

# Displayes the tasks that are pending -- so we use GET

@app.get("/tasks/pending")
async def get_pending():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:         # gives dictionary
            cur.execute("""
    SELECT id, description, priority, category, carer_id, created_by, created_at, escalated_to
    FROM tasks 
    WHERE status = 'pending' 
    ORDER BY created_at DESC
""")
            return cur.fetchall()

# -------------------------------------------COMPLETED TASKS------------------------------------

# Displayes the completed tasks that are marked completed in last 48hrs
 
@app.get("/tasks/completed")
async def get_completed():
    two_days_ago = datetime.now() - timedelta(days=2)
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""SELECT id, description, priority, category, carer_id, created_by, created_at, completed_at, completed_by_carer 
                        FROM tasks WHERE status = 'completed' 
                        AND completed_at >= %s ORDER BY completed_at DESC""", (two_days_ago,))
            return cur.fetchall()

# --------------------------------COUNTS THE ACTIVE TASKS OF EACH CARER--------------------------

# Shift Briefing after login --- gets tasks of specific carer

@app.get("/tasks/count/{carer_id}")
async def get_task_count(carer_id: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tasks WHERE carer_id = %s AND status = 'pending'", (carer_id,))
            return {"count": cur.fetchone()[0]}

# ------------------------------------MANUAL REASSIGNMENT-----------------------------------------

# If a carer want to reassign a task to some other carer.

@app.put("/tasks/{tid}/reassign/{new_carer_id}")
async def reassign_task(tid: int, new_carer_id: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE tasks SET carer_id = %s WHERE id = %s", (new_carer_id, tid))
            conn.commit()
            return {"status": "ok"}

# -------------------------------------UPDATES COMPLETED TASKS-------------------------------------

# marks a task as finished

@app.put("/tasks/{tid}/complete")
async def complete(tid: int, carer_id: str = Form(...)):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks SET status = 'completed', completed_at = %s, completed_by_carer = %s 
                WHERE id = %s
            """, (datetime.now(), carer_id, tid))
            conn.commit()
            return {"status": "ok"}

# -------------------------------------UNDOS COMPLETED TASKS----------------------------------------

# allows a carer to move a task from the "Completed" list back to the "Active" list if it was marked done by mistake.

@app.put("/tasks/{tid}/revert")
async def revert_task(tid: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks 
                SET status = 'pending', 
                    completed_at = NULL, 
                    completed_by_carer = NULL 
                WHERE id = %s
            """, (tid,))
            conn.commit()
            return {"status": "reverted"}
        

@app.put("/tasks/escalate/{tid}")
async def escalate_task(tid: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks 
                SET escalated_to = %s 
                WHERE id = %s
            """, ("C-MGR-01", tid))
            conn.commit()
            return {"status": "escalated"}