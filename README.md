# Pivot — Career Guidance Agent

Pivot is an AI-powered, multi-agent career guidance assistant.  
It helps users with small talk, general questions, recommends learning paths and courses, and provides admissions information for PTIT (Posts and Telecommunications Institute of Technology).  

---

## 📌 Overview

Pivot is organized as a **root agent** that coordinates several **sub-agents**:

- `general_agent`: small talk and simple questions  
- `path_learning_agent`: recommends courses and learning paths (hybrid search)  
- `admission_agent`: admissions information and PTIT details  

The system uses **hybrid search** (vector + text) over MongoDB corpora and the **Google GenAI stack** for embeddings and generation.

---

## ✨ Key Features

- Multi-agent architecture (root + sub-agents)  
- Hybrid search (vector + text) for document retrieval and ranking  
- Google GenAI (`genai`, `google-adk`) for embeddings and generation  
- FastAPI server with SSE for live responses  

---

## 🛠 Tech stack

- Python 3.10+  
- FastAPI + Uvicorn  
- google-genai, google-adk (GenAI client & agent runner)  
- pymongo (MongoDB)  
- python-dotenv  

---

## 🔑 Environment variables

Create a `.env` file in the project root or export them manually:  

- `GOOGLE_API_KEY` — Google GenAI API key  
- `MONGODB_URI_AMI` — Mongo URI for some agents  
- `MONGODB_ADMISSION` — Mongo URI for `admission_agent`  

---

## 🚀 Quick setup & run (PowerShell / Windows)

1. Create and activate virtual environment with `uv`:  
```powershell
uv venv .venv
.venv\Scripts\Activate.ps1
````

2. Install dependencies (from `pyproject.toml`):

```powershell
uv pip install -e .
```

---

## 📖 Usage

### 1. ADK UI

* Navigate to the `app` folder:

```powershell
cd app
adk web
```

* Open browser and go to:

```
http://127.0.0.1:8000
```

### 2. API Endpoint

* Run the server inside the `app` folder:

```powershell
cd app
uvicorn main:app --reload
```

* Access API via:

```
http://127.0.0.1:8000
```

* Main endpoint:

```
POST http://127.0.0.1:8000/query
```

* **Sample Request JSON**:

```json
{
    "query": "meaning of PTIT logo",
    "user_id": "user_123"
}
```

* **Sample Response JSON**:

```json
{
    "response": "..."
}
```

---

## 📑 Agents summary

* **general\_agent**: small talk and simple questions
* **path\_learning\_agent**: recommends courses & learning paths, uses hybrid search
* **admission\_agent**: admissions and PTIT info (conditions, deadlines, programs, campus, contact)

---

## 📌 API endpoints

* `POST /query` — receive JSON request and return final response

---

## ⚡ Request Flow

1. User sends query → `root_agent`
2. `root_agent` classifies query → delegates to appropriate sub-agent
3. Sub-agent retrieves data from MongoDB (hybrid search)
4. Google GenAI generates response
5. Final JSON response returned

---