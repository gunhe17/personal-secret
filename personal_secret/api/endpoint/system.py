from pathlib import Path

from fastapi.responses import FileResponse

from personal_secret.api.infrastructure.postgresql.schema import build_schema


# #
# health

def health() -> dict:
    return {"ok": True}


# #
# schema

def schema() -> dict:
    return build_schema()


def page_schema() -> FileResponse:
    return FileResponse(
        Path(
            __file__
        )
        .resolve()
        .parent.parent / "domain" / "schema.html"
    )


# #
# web ui

def index() -> FileResponse:
    return _static("index.html")


def styleguide() -> FileResponse:
    return _static("styleguide.html")


def styles() -> FileResponse:
    return _static("styles.css")


def _static(name: str) -> FileResponse:
    return FileResponse(
        Path(
            __file__
        )
        .resolve()
        .parent.parent / "server" / "static" / name
    )
