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
    # 3000 is occupied by a local Postgres service on this machine; dev web runs on 3001
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "altamont-api"}


from api.routes.baseline import router as baseline_router  # noqa: E402
from api.routes.scenarios import router as scenarios_router  # noqa: E402

app.include_router(baseline_router)
app.include_router(scenarios_router)
