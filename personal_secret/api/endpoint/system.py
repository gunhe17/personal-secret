from pathlib import Path

from fastapi.responses import FileResponse


# #
# health

def health() -> dict:
    return {"ok": True}


# #
# web ui

def index() -> FileResponse:
    return _static("index.html")


def styleguide() -> FileResponse:
    return _static("styleguide.html")


def styles() -> FileResponse:
    return _static("styles.css")


def _static(name: str) -> FileResponse:
    path = Path(__file__).resolve().parent.parent / "server" / "static" / name
    return FileResponse(path)
