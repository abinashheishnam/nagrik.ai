from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.api.v1.router import router as v1_router
from app.auth.routes import router as auth_router
from app.ai.ml import load_models
from app.api.v1.routes.ai_draft import router as ai_draft_router

app = FastAPI(title="Praja.ai Backend")

# ✅ CORS: keep ONE middleware only
# If you run frontend from Live Server (5500) or Vite (5173), allow those.
# Add your deployed domain later when hosting.
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    load_models()

# ✅ Auth routes (no /api/v1 prefix as you intended)
app.include_router(auth_router)

# ✅ API v1 router
app.include_router(v1_router, prefix="/api/v1")

# ✅ Fallback AI Draft route (for frontend fallback support)
app.include_router(ai_draft_router)

@app.get("/")
async def root_get():
    return PlainTextResponse("OK", status_code=200)

@app.post("/")
async def root_post():
    return PlainTextResponse("Praja.ai backend is running.", status_code=200)
