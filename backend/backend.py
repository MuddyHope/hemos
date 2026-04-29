import sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from database import get_db
import pickle

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# Machine Learning Model Inference

from inference import CardiacMonitor  # your file

# Load trained artifacts
with open('cardiac_model.pkl', 'rb') as f:
    bundle = pickle.load(f)

model    = bundle['model']
encoder  = bundle['encoder']
features = bundle['features']


# Single global monitor instance
monitor = CardiacMonitor(model, encoder, features)


class VitalReading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str
    heart_rate: float | None = None
    body_temperature: float | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    model_config = ConfigDict()
    username: str
    password: str
    full_name: str | None = None
    sex: str | None = None
    smoking_status: str | None = None
    preferred_unit: str | None = None
    age: int | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    height_ft: int | None = None
    height_in: int | None = None
    weight_lb: float | None = None


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )


@app.get("/login", response_class=HTMLResponse)
def login_page_alias(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={}
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={}
    )


@app.post("/login")
def login(payload: LoginRequest):
    conn = get_db()
    row = conn.execute(
        """
        SELECT username, full_name FROM patients
        WHERE username = ? AND password = ?
        LIMIT 1
        """,
        (payload.username, payload.password)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "status": "ok",
        "username": row["username"],
        "full_name": row["full_name"]
    }


@app.post("/register")
def register(payload: RegisterRequest):
    if not payload.username or not payload.password or not payload.full_name:
        raise HTTPException(status_code=400, detail="username, password, and full_name are required")

    if not payload.preferred_unit:
        raise HTTPException(status_code=400, detail="preferred_unit is required")

    if not payload.sex:
        raise HTTPException(status_code=400, detail="sex is required")

    if not payload.smoking_status:
        raise HTTPException(status_code=400, detail="smoking_status is required")

    unit = payload.preferred_unit.lower()

    if unit not in ("metric", "us"):
        raise HTTPException(status_code=400, detail="preferred_unit must be 'metric' or 'us'")

    if payload.sex not in ("female", "male", "intersex", "other", "prefer_not_to_say"):
        raise HTTPException(status_code=400, detail="Invalid sex value")

    if payload.smoking_status not in ("never", "former", "current"):
        raise HTTPException(status_code=400, detail="Invalid smoking status")

    height_cm = payload.height_cm
    weight_kg = payload.weight_kg
    height_ft = payload.height_ft
    height_in = payload.height_in
    weight_lb = payload.weight_lb

    if unit == "metric":
        if height_cm is None or weight_kg is None:
            raise HTTPException(status_code=400, detail="Metric units require height_cm and weight_kg")
    else:
        if height_ft is None or weight_lb is None:
            raise HTTPException(status_code=400, detail="US units require height_ft and weight_lb")
        total_inches = (height_ft * 12) + (height_in or 0)
        height_cm = total_inches * 2.54
        weight_kg = weight_lb * 0.45359237

    bmi = None
    if height_cm and weight_kg and height_cm > 0:
        bmi = weight_kg / ((height_cm / 100) ** 2)

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO patients (
                username, password, full_name, sex, smoking_status, preferred_unit,
                age, height_cm, weight_kg, height_ft, height_in, weight_lb,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.username,
                payload.password,
                payload.full_name,
                payload.sex,
                payload.smoking_status,
                unit,
                payload.age,
                height_cm,
                weight_kg,
                height_ft,
                height_in,
                weight_lb,
                datetime.utcnow().isoformat()
            )
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")

    conn.close()

    return {
        "status": "ok",
        "message": "Registration successful",
        "bmi": round(bmi, 1) if bmi is not None else None,
        "bmi_category": (
            "Underweight" if bmi is not None and bmi < 18.5 else
            "Healthy weight" if bmi is not None and bmi < 25 else
            "Overweight" if bmi is not None and bmi < 30 else
            "Obesity" if bmi is not None else None
        ),
        "normalized_height_cm": round(height_cm, 1) if height_cm else None,
        "normalized_weight_kg": round(weight_kg, 1) if weight_kg else None
    }


@app.post("/api/vitals")
def receive_vitals(reading: VitalReading):
    conn = get_db()
    conn.execute(
        "INSERT INTO readings (device_id, timestamp, heart_rate, body_temperature) VALUES (?, ?, ?, ?)",
        (
            reading.device_id,
            datetime.utcnow().isoformat(),
            reading.heart_rate,
            reading.body_temperature,
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/api/latest")
def latest_reading():
    conn = get_db()
    row = conn.execute(
        """
        SELECT id, device_id, timestamp, heart_rate, body_temperature
        FROM readings
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()

    if not row:
        return {"status": "no data"}

    return dict(row)


@app.get("/api/history")
def history(limit: int = 20):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, device_id, timestamp, heart_rate, body_temperature
        FROM readings
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]


@app.get("/api/recovery")
def recovery():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT heart_rate, body_temperature
        FROM readings
        WHERE heart_rate IS NOT NULL OR body_temperature IS NOT NULL
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()
    conn.close()

    if not rows:
        return {"status": "no data", "recovery_score": None, "state": "No data"}

    hrs = [r["heart_rate"] for r in rows if r["heart_rate"] is not None]
    temps = [r["body_temperature"] for r in rows if r["body_temperature"] is not None]

    avg_hr = sum(hrs) / len(hrs) if hrs else None
    avg_temp = sum(temps) / len(temps) if temps else None

    score = 100

    if avg_hr is not None:
        if avg_hr > 110:
            score -= 35
        elif avg_hr > 95:
            score -= 20
        elif avg_hr > 85:
            score -= 10

    if avg_temp is not None:
        if avg_temp >= 38.0:
            score -= 35
        elif avg_temp >= 37.5:
            score -= 20
        elif avg_temp >= 37.2:
            score -= 10

    score = max(0, min(100, score))
    state = "Recovered" if score >= 85 else "Monitor" if score >= 65 else "Needs attention"

    return {
        "status": "ok",
        "avg_heart_rate": avg_hr,
        "avg_temperature": avg_temp,
        "recovery_score": score,
        "state": state,
    }

# Analysis Page
@app.get("/analysis", response_class=HTMLResponse)
def analysis_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="analysis.html",
        context = {}
    )

# Machine Learning Model
@app.get("/api/analysis")
def analyze_latest():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT heart_rate, body_temperature
        FROM readings
        WHERE heart_rate IS NOT NULL OR body_temperature IS NOT NULL
        ORDER BY id ASC
        LIMIT 100
        """
    ).fetchall()

    conn.close()

    if not rows:
        return {"status": "no data"}

    # 🔥 Reset buffers before rebuilding
    monitor.hr_buffer.clear()
    monitor.temp_buffer.clear()

    result = None

    # 🔥 Feed historical data sequentially
    for r in rows:
        hr = r["heart_rate"]
        temp = r["body_temperature"]

        result = monitor.predict(hr, temp)

    return {
        "status": "ok",
        "analysis": result,
        "samples_used": len(rows)
    }