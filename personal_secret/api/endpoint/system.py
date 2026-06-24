from pathlib import Path

from fastapi.responses import FileResponse

from personal_secret.api.infrastructure.map.client import map_client


# #
# health

def health() -> dict:
    return {"ok": True}


# #
# map

def map() -> dict:
    return map_client.build()


def page_map() -> FileResponse:
    return FileResponse(
        Path(
            __file__
        )
        .resolve()
        .parent.parent / "server" / "static" / "map.html"
    )


def page_lab() -> FileResponse:
    return FileResponse(
        Path(
            __file__
        )
        .resolve()
        .parent.parent / "server" / "static" / "map_lab.html"
    )


def page_exception_lab() -> FileResponse:
    return FileResponse(
        Path(
            __file__
        )
        .resolve()
        .parent.parent / "server" / "static" / "map_exception_lab.html"
    )
