"""ALTAMONT API — serves tract accessibility scores, scenarios, and diffs as GeoJSON."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ALTAMONT",
    description=(
        "Transit-equity scenario tool for San Joaquin County super-commuters. "
        "Routing by Conveyal R5 (via r5py); everything else built here."
    ),
    version="0.1.0",
)

# Frontend dev server runs on a different origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "altamont-api"}
