from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pantry_engine.api.routers import demo, health, ingestion, inventory, menu
from pantry_engine.api.startup import on_startup

load_dotenv()
load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(title="Pantry API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(inventory.router)
app.include_router(menu.router)
app.include_router(demo.router)
app.include_router(ingestion.router)


@app.on_event("startup")
def startup_event():
    on_startup()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
