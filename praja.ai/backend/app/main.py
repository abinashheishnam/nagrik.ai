from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_router
from app.auth.routes import router as auth_router

from app.ai.ml import load_models

app = FastAPI(title="Praja.ai Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    load_models()

app.include_router(auth_router)
app.include_router(api_router)

# ===== API v1 Router Mount (fix double /api/v1) =====
from app.api.v1.router import router as v1_router
app.include_router(v1_router, prefix="/api/v1")
from fastapi.responses import PlainTextResponse

@app.post("/")
async def root_post():
    return PlainTextResponse("Praja.ai backend is running. Twilio webhook should target /api/v1/whatsapp/twilio", status_code=200)

@app.get("/")
async def root_get():
    return PlainTextResponse("OK", status_code=200)
