# SASP - Student Academic Scheduling Planner

## Prerequisites

- **Python 3.8+** - Download from: https://www.python.org/downloads/
  - During installation, check "Add Python to PATH"

## Setup Instructions (New PC/Laptop)

### 1. Copy the Project Folder
Transfer the entire `SASP` folder to the new computer (via USB, cloud storage, etc.)

### 2. Open Terminal/Command Prompt
Navigate to the project folder:
```powershell
cd C:\path\to\SASP
```

### 3. Create a Virtual Environment
```powershell
python -m venv .venv
```

Activate it:
```powershell
.venv\Scripts\activate
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

This will install:
| Dependency | Purpose |
|------------|---------|
| Flask | Web application framework |
| Flask-CORS | Enable cross-origin resource sharing |

---

## Run the app (development)

Start the Flask app without the reloader on port 5001 (recommended fallback if port 5000 is occupied):

To run:
```powershell
.venv\Scripts\python.exe app.py
```


Then open in your browser:

```
http://127.0.0.1:5001
```

Notes:
- If you need port 5000, stop any other process using that port (or reboot) and run `python app.py`.
- The app now injects initial curriculum data into the index page so it will render even if client-side API calls fail.

