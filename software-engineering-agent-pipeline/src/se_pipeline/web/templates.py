"""
Shared Jinja2 templates instance
"""
from fastapi.templating import Jinja2Templates
from pathlib import Path

current_dir = Path(__file__).parent
templates = Jinja2Templates(directory=str(current_dir / "templates"))
