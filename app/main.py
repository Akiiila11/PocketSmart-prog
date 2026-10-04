import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import init_db, get_db
from .auth import hash_password, verify_password, create_token, current_user
from .ai import generate_recommendation

BASE = Path(__file__).resolve().parent
UPLOADS = BASE / "uploads"
UPLOADS.mkdir(exist_ok=True)

app = FastAPI(title="PocketSmart AI")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

@app.on_event("startup")
def startup():
    init_db()

def render(request, page, **context):
    uid = current_user(request)
    context["logged_in"] = bool(uid)
    context["user_id"] = uid
    return templates.TemplateResponse(request=request, name=page, context=context)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render(request, "index.html")

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return render(request, "register.html")

@app.post("/register")
def register(name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
            (name.strip(), email.strip().lower(), hash_password(password))
        )
        conn.commit()
    except Exception:
        conn.close()
        return RedirectResponse("/register?error=Email already registered", status_code=303)
    conn.close()
    return RedirectResponse("/login?message=Registration successful", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render(request, "login.html")

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    conn.close()
    if not user or not verify_password(password, user["password_hash"]):
        return RedirectResponse("/login?error=Invalid email or password", status_code=303)
    token = create_token(user["id"])
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("access_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    uid = current_user(request)
    if not uid:
        return RedirectResponse("/login", status_code=303)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM recommendations WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,)
    ).fetchall()
    conn.close()
    return render(request, "dashboard.html", history=rows)

@app.get("/planner/{planner}", response_class=HTMLResponse)
def planner_page(request: Request, planner: str):
    if planner not in {"home", "party", "jewelry"}:
        return RedirectResponse("/", status_code=303)
    return render(request, f"{planner}.html", planner=planner)

def save_result(uid, planner, budget, data, result):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO recommendations(user_id,planner,budget,input_json,result_json) VALUES(?,?,?,?,?)",
        (uid, planner, budget, json.dumps(data), json.dumps(result))
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid

@app.post("/generate-home", response_class=HTMLResponse)
def generate_home(request: Request, budget: float = Form(...), room: str = Form(...),
                  style: str = Form("Modern"), quantities: str = Form("")):
    uid = current_user(request)
    if not uid:
        return RedirectResponse("/login", status_code=303)
    data = {"budget": budget, "room": room, "style": style, "quantities": quantities}
    result = generate_recommendation("home", data)
    save_result(uid, "home", budget, data, result)
    return render(request, "results.html", planner="Home Interior", result=result)

@app.post("/generate-party", response_class=HTMLResponse)
def generate_party(request: Request, budget: float = Form(...), guests: int = Form(...),
                   event_type: str = Form(...), venue: str = Form("")):
    uid = current_user(request)
    if not uid:
        return RedirectResponse("/login", status_code=303)
    data = {"budget": budget, "guests": guests, "event_type": event_type, "venue": venue}
    result = generate_recommendation("party", data)
    save_result(uid, "party", budget, data, result)
    return render(request, "results.html", planner="Party", result=result)

@app.post("/generate-jewelry", response_class=HTMLResponse)
async def generate_jewelry(request: Request, budget: float = Form(...),
                           occasion: str = Form(...), style: str = Form(...),
                           outfit_notes: str = Form(""),
                           outfit_image: UploadFile | None = File(None)):
    uid = current_user(request)
    if not uid:
        return RedirectResponse("/login", status_code=303)

    image_path = None
    if outfit_image and outfit_image.filename:
        suffix = Path(outfit_image.filename).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            return render(request, "jewelry.html", error="Use JPG, PNG or WEBP image.")
        safe_name = f"user_{uid}_{Path(outfit_image.filename).name}"
        image_path = str(UPLOADS / safe_name)
        with open(image_path, "wb") as f:
            shutil.copyfileobj(outfit_image.file, f)

    data = {"budget": budget, "occasion": occasion, "style": style, "outfit_notes": outfit_notes}
    result = generate_recommendation("jewelry", data, image_path)
    save_result(uid, "jewelry", budget, data, result)
    return render(request, "results.html", planner="Jewelry", result=result)

@app.get("/history", response_class=HTMLResponse)
def history(request: Request):
    uid = current_user(request)
    if not uid:
        return RedirectResponse("/login", status_code=303)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM recommendations WHERE user_id=? ORDER BY id DESC", (uid,)
    ).fetchall()
    conn.close()
    return render(request, "history.html", history=rows)
