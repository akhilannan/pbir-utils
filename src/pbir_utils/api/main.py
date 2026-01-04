"""FastAPI application for PBIR Utils UI."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from .routes import browse, reports

app = FastAPI(
    title="PBIR-Utils UI",
    description="Web-based UI for Power BI Enhanced Report Format utilities",
    version="1.0.0",
)

# CORS - allow local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(browse.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

# Template and Static directories
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
STATIC_DIR = Path(__file__).parent.parent / "static"


@app.get("/", response_class=HTMLResponse)
async def index(initial_report: str = None):
    """Serve the main UI client page."""
    env = Environment(loader=FileSystemLoader([TEMPLATE_DIR, STATIC_DIR]))
    template = env.get_template("client.html.j2")
    return template.render(initial_report=initial_report)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
