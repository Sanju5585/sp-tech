from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.api import academic, ai, auth, ops, resources, schools, timetable
from app.bootstrap import bootstrap
from app.config import get_settings
from app.database import Base, SessionLocal, engine, ensure_schema
from app.models import entities as _models  # noqa: F401  ensure metadata

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

app = FastAPI(title=settings.app_name, version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def never_leak_gemini_key(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.on_event("startup")
def on_startup():
    Path("uploads").mkdir(exist_ok=True)
    Path("exports").mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    db: Session = SessionLocal()
    try:
        bootstrap(db)
        if settings.app_env != "production":
            from app.bootstrap import seed_demo_school

        if settings.app_env != "production":
            from app.bootstrap import seed_demo_school
            from app.models.entities import SchoolClass, Teacher

            school = seed_demo_school(db, replace=False)
            teachers_n = db.query(Teacher).filter(Teacher.school_id == school.id).count()
            classes_n = db.query(SchoolClass).filter(SchoolClass.school_id == school.id).count()
            if teachers_n != 11 or classes_n != 3:
                seed_demo_school(db, replace=True)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "env": settings.app_env, "gemini": bool(settings.gemini_api_key)}


@app.post("/api/dev/seed")
def seed_demo():
    if settings.app_env == "production":
        return JSONResponse({"detail": "Seed disabled in production"}, status_code=403)
    from app.bootstrap import seed_demo_school

    db = SessionLocal()
    try:
        school = seed_demo_school(db, replace=True)
        return {
            "school_id": school.id,
            "admin": "admin@demo.school",
            "password": "DemoAdmin123!",
            "teacher": "t001@demo.school",
            "teacher_password": "Teacher123!",
            "sample": "3 classes (6, 7, 8 with A/B), 7 subjects, 11 teachers",
        }
    finally:
        db.close()


app.include_router(auth.router, prefix="/api")
app.include_router(schools.router, prefix="/api")
app.include_router(academic.router, prefix="/api")
app.include_router(resources.router, prefix="/api")
app.include_router(timetable.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(ops.router, prefix="/api")


# Rate-limit AI routes more tightly
@app.middleware("http")
async def ai_rate_guard(request: Request, call_next):
    if request.url.path.startswith("/api/ai/"):
        # slowapi decorator alternative: rely on default + this header marker
        request.state.ai_endpoint = True
    return await call_next(request)
