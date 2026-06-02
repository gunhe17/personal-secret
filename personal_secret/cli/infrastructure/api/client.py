from __future__ import annotations

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
    # secret

    def create(self, *, kind: str, name: str, tags: list[str], expires_at: str | None, data: dict) -> dict:
        body = {"kind": kind, "name": name, "tags": tags, "expires_at": expires_at, "data": data}
        return self._request(method="POST", path="/secret", body=body)

    def list(self, *, kind: str | None, tag: str | None, query: str | None) -> list[dict]:
        params = {k: v for k, v in {"kind": kind, "tag": tag, "query": query}.items() if v is not None}
        return self._request(method="GET", path="/secret", params=params)

    def reveal(self, *, identifier: str) -> dict:
        return self._request(method="GET", path=f"/secret/{identifier}/reveal")

    def update(self, *, identifier: str, name: str, tags: list[str], expires_at: str | None, data: dict | None) -> dict:
        body = {"identifier": identifier, "name": name, "tags": tags, "expires_at": expires_at, "data": data}
        return self._request(method="POST", path="/secret/update", body=body)

    def delete(self, *, identifier: str) -> dict:
        return self._request(method="DELETE", path=f"/secret/{identifier}")

    def expiring(self, *, within_days: int) -> list[dict]:
        return self._request(method="GET", path="/secret/expiring", params={"within_days": within_days})

    # #
    # internal

    def _request(self, *, method: str, path: str, body: dict | None = None, params: dict | None = None):
        try:
            with httpx.Client(base_url=self._config.API_BASE_URL, timeout=30.0) as http:
                response = http.request(
                    method,
                    path,
                    json=body,
                    params=params,
                    headers={"X-Requested-By": "personal-secret-cli"},
                )
        except httpx.ConnectError:
            raise ApiError(f"서버에 연결할 수 없습니다 ({self._config.API_BASE_URL}). 컨테이너가 떠 있는지 확인하세요.")

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
