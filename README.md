# CareVoice AI – Intelligent Task Management System

## Overview

**CareVoice AI** is a full-stack AI-powered task management system designed for healthcare environments.
It converts **voice recordings into actionable tasks**, prioritizes them using AI, and ensures execution through **shift-based reminders and escalation workflows**.

The system supports **role-based access** for carers and managers, enabling efficient task handling and critical oversight.

---

## Key Features

### AI-Powered Task Extraction

* Converts audio to text using Whisper
* Extracts structured tasks using GPT
* Categorizes tasks into:

  * Resident
  * Inventory
  * General

---

### Intelligent Task Prioritization

* Tasks automatically classified as:

  * 🔴 Critical
  * 🟡 Important
  * ⚪ Routine

---

### Shift-Based Workflow

* Tasks are assigned based on shift rotation
* Automatic handover between carers

---

### Smart Reminder System

* Critical tasks trigger reminders during shift
* Popup alerts for pending critical tasks

---

### Escalation System

* If critical tasks are not completed within shift:

  * Escalated to Manager
* Original carer **retains ownership**
* Manager gets visibility (no modification rights)

---

### Role-Based Dashboards

#### Carer Dashboard

* Create tasks via voice/upload
* View active & completed tasks
* Reassign tasks
* Mark tasks as completed

#### Manager Dashboard

* View **only escalated critical tasks**
* Clean, centered UI
* Read-only (no actions allowed)

---

### Persistent State Handling

* Session-based login
* Shift tracking using localStorage
* Works even after refresh/logout

---

## Project Structure

```
CareVoiceAI/
│
├── app.py          # FastAPI backend
├── db.py           # Database connection & table creation
├── index.html      # Frontend UI
├── style.css       # Styling
└── README.md       # Documentation
```

---

## Tech Stack

### Backend

* FastAPI
* PostgreSQL
* OpenAI API (Whisper + GPT)

### Frontend

* HTML
* CSS
* JavaScript (Vanilla)

---

## Database Design

### Tasks Table

* Stores all tasks with:

  * description
  * priority
  * category
  * carer_id
  * escalated_to
  * timestamps

---

## API Endpoints

Key APIs from backend: 

* `POST /upload/` → Process audio & create tasks
* `GET /tasks/pending` → Get active tasks
* `GET /tasks/completed` → Get completed tasks
* `PUT /tasks/{id}/complete` → Mark task complete
* `PUT /tasks/{tid}/revert` → Undo completed task if made by mistake
* `PUT /tasks/escalate/{id}` → Escalate task

---

## Setup Instructions

### 1️⃣ Clone Repository

```bash
git clone <your-repo-url>
cd CareVoiceAI
```

---

### 2️⃣ Install Backend Dependencies

```bash
pip install fastapi uvicorn psycopg2 openai python-multipart
```

---

### 3️⃣ Setup PostgreSQL

Create database:

```sql
CREATE DATABASE care_ai;
```

Update credentials in:

📄 

```python
dbname="care_ai",
user="postgres",
password="your_password",
host="localhost",
port="5432"
```

---

### 4️⃣ Create Tables

```bash
python db.py
```

---

### 5️⃣ Set OpenAI API Key

```bash
setx OPENAI_API_KEY "your_api_key"
```

Restart terminal after this.

---

### 6️⃣ Run Backend

```bash
uvicorn app:app --reload
```

Backend runs at:

```
http://127.0.0.1:8000
```

---

### 7️⃣ Run Frontend

Simply open:

```
index.html
```

in your browser.

---

## How to Test

### Create Task

* Login as carer
* Record/upload audio
* Example:

  ```
  Patient oxygen level is low. Check immediately.
  ```

---

### Test Escalation

Open browser console:

```javascript
localStorage.setItem(
  "shift_start_time",
  new Date(Date.now() - (8 * 60 * 60 * 1000)).toISOString()
);
localStorage.setItem("escalation_done", "false");

checkShiftEndEscalation();
```

---

### Verify

* Task appears in manager dashboard
* `escalated_to = C-MGR-01`

---

## Default Credentials

| Role    | ID       | Password  |
| ------- | -------- | --------- |
| Carer   | C-MOR-01 | Care@2026 |
| Manager | C-MGR-01 | Care@2026 |

---

## System Design Highlights

* AI-driven task extraction
* Role-based UI rendering
* Shift-aware reminders
* Escalation without reassignment
* Frontend + Backend integration

---

## Future Improvements

* Real-time notifications
* Backend scheduler (Celery)
* JWT authentication
* Manager analytics dashboard
* Multi-level escalation

---

## Author

**Jayanthi M L**
Data Science | AI | Machine Learning

---

## Conclusion

This project demonstrates a **real-world intelligent workflow system** combining:

* AI
* Backend APIs
* Frontend UX
* Database design

It is designed with **scalability, usability, and real-world healthcare scenarios in mind**.

---
