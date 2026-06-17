from pathlib import Path

from fastapi.responses import FileResponse

from personal_secret.api.infrastructure.introspect.map import build_map


# #
# health

def health() -> dict:
    return {"ok": True}


# #
# map

def map() -> dict:
    return build_map()


def page_map() -> FileResponse:
    return FileResponse(
        Path(
            __file__
        )
        .resolve()
        .parent.parent / "server" / "static" / "map.html"
    )
