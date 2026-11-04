"""Local real-road browser harness. No synthetic endpoints; never download data.
PYTHONPATH=backend:tools:<extension> ROAD_FIXTURE_ROOT=... uvicorn road_server:app
"""

from pathlib import Path
from fastapi.staticfiles import StaticFiles
import api

app = api.app
app.mount(
    "/ui",
    StaticFiles(directory=Path(__file__).resolve().parents[1] / "frontend", html=True),
    name="road-ui",
)
