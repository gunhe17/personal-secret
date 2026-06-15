from __future__ import annotations

import os

import httpx

from personal_secret.cli.config import CliConfig
from personal_secret.cli.config import get_cli_config
from personal_secret.cli.exception import ApiError


# #
# api

class Api:
    def __init__(self, *, config: CliConfig):
        self._config = config

    # #
    # auth

    def login(self, *, email: str, password: str) -> dict:
        result = self._request(
            method="POST",
            path="/auth/login",
            body={"email": email, "password": password},
        )
        self._save_token(token=result["data"]["token"])
        return result

    def _save_token(self, *, token: str) -> None:
        path = self._config.TOKEN_PATH
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(token)

    def _load_token(self) -> str | None:
        path = self._config.TOKEN_PATH
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return f.read().strip() or None

    # #
    # secret

    def create(self, *, domain: str, service: str, project: str, field: str, value: str) -> dict:
        body = {"domain": domain, "service": service, "project": project, "field": field, "value": value}
        return self._request(method="POST", path="/secret", body=body)

    def list(self, *, domain: str | None, service: str | None, project: str | None) -> list[dict]:
        params = {k: v for k, v in {"domain": domain, "service": service, "project": project}.items() if v is not None}
        return self._request(method="GET", path="/secret", params=params)

    def reveal(self, *, id: str) -> dict:
        return self._request(method="GET", path=f"/secret/{id}/reveal")

    def update(self, *, id: str, value: str) -> dict:
        body = {"id": id, "value": value}
        return self._request(method="POST", path="/secret/update", body=body)

    def delete(self, *, id: str) -> dict:
        return self._request(method="DELETE", path=f"/secret/{id}")

    # #
    # internal

    def _request(self, *, method: str, path: str, body: dict | None = None, params: dict | None = None):
        headers = {"X-Requested-By": "personal-secret-cli"}
        token = self._load_token()
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        try:
            with httpx.Client(base_url=self._config.API_BASE_URL, timeout=30.0) as http:
                response = http.request(
                    method,
                    path,
                    json=body,
                    params=params,
                    headers=headers,
                )
        except httpx.ConnectError:
            raise ApiError(f"서버에 연결할 수 없습니다 (식별자: {self._config.API_BASE_URL}, 조치: 컨테이너 확인)")

        if response.status_code >= 400:
            try:
                message = response.json().get("message", response.text)
            except Exception:
                message = response.text
            raise ApiError(message)

        result = response.json() if response.content else None
        return result


# #
# Api

api = Api(config=get_cli_config())
