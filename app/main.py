from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.modules.auth.api import router as auth_router
from app.modules.tasks.api import router as tasks_router
from app.modules.projects.api import router as projects_router
from app.core.config import settings
from app.core.response import http_exception_handler, validation_exception_handler
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

# 1. Define the origins that are allowed to make requests to your API
origins = [
    "http://localhost:5173",  # Vite/React default
    "http://localhost:3000",  # Common React default
    "https://yourdomain.com", # Production domain
]

# 2. Add the middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             # Allows specific list of origins
    allow_credentials=True,            # Allows cookies/auth headers
    allow_methods=["*"],               # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],               # Allows all headers
)

# ── Register global exception handlers ────────────────────────────
# These ensure 404, 422, 500 etc all return the unified response format
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# ── Routers ───────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(projects_router)


@app.get("/", tags=["Health"])
def root():
    return {"status": 200, "success": True, "message": "API is running", "data": None}


@app.get("/health", tags=["Health"])
def health():
    return {"status": 200, "success": True, "message": "OK", "data": None}