import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from personal_secret.api.config import is_develop


class Middleware:
    def __init__(
        self,
        middleware_class: type,
        **options: Any
    ):
        self.middleware_class = middleware_class
        self.options = options

    def register(self, app: FastAPI):
        app.add_middleware(self.middleware_class, **self.options)


# #
# factory

def cors():
    prefix = "DEVELOP" if is_develop() else "PRODUCTION"
    port = os.environ.get(f"{prefix}_API_PORT", "28200")
    origins = [
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
    ]
    return Middleware(
        middleware_class=CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def proxy_headers():
    return Middleware(
        middleware_class=ProxyHeadersMiddleware
    )
