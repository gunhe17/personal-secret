import os

from personal_secret.api.config import get_app_environment, is_develop
from personal_secret.api.server.server import personal_secret_api
from personal_secret.api.server import middleware
from personal_secret.api.server.router import Router
from personal_secret.api.endpoint import system
from personal_secret.api.endpoint import command
from personal_secret.api.endpoint import secret
from personal_secret.api.endpoint import auth
from personal_secret.api.endpoint import team
from personal_secret.api.endpoint import account
from personal_secret.api.server import exception


# #
# server

server = personal_secret_api()

# middleware
server.middleware(middleware.cors())
server.middleware(middleware.proxy_headers())

# #
# router

# system
server.router(
    Router(path="/system/health", methods=["GET"], endpoint=system.health)
)
server.router(
    Router(path="/system/schema", methods=["GET"], endpoint=system.schema)
)

# view
server.router(
    Router(path="/schema", methods=["GET"], endpoint=system.page_schema)
)

# auth
server.router(
    Router(path="/auth/register", methods=["POST"], endpoint=auth.post_register)
)
server.router(
    Router(path="/auth/salts", methods=["GET"], endpoint=auth.get_salts)
)
server.router(
    Router(path="/auth/login", methods=["POST"], endpoint=auth.post_login)
)

# account
server.router(
    Router(path="/accounts/public-key", methods=["GET"], endpoint=account.get_public_key)
)

# team
server.router(
    Router(path="/teams", methods=["POST"], endpoint=team.post_create)
)
server.router(
    Router(path="/teams/{team_id}/key", methods=["GET"], endpoint=team.get_key)
)
server.router(
    Router(path="/teams/{team_id}/members", methods=["POST"], endpoint=team.post_invite)
)
server.router(
    Router(path="/teams/{team_id}/members/{account_id}", methods=["DELETE"], endpoint=team.delete_member)
)
server.router(
    Router(path="/teams/{team_id}/rotate", methods=["POST"], endpoint=team.post_rotate)
)

# secret
server.router(
    Router(path="/teams/{team_id}/secrets", methods=["POST"], endpoint=secret.post_create)
)
server.router(
    Router(path="/teams/{team_id}/secrets", methods=["GET"], endpoint=secret.get_list)
)
server.router(
    Router(path="/teams/{team_id}/secrets/{secret_id}", methods=["GET"], endpoint=secret.get_reveal)
)
server.router(
    Router(path="/teams/{team_id}/secrets/{secret_id}", methods=["PUT"], endpoint=secret.put_update)
)
server.router(
    Router(path="/teams/{team_id}/secrets/{secret_id}", methods=["DELETE"], endpoint=secret.delete_secret)
)

# exception handler
server.exception_handler(exception.client())
server.exception_handler(exception.internal())

# app
app = server.app()


# #
# run

if __name__ == "__main__":
    import uvicorn

    environment = get_app_environment()
    develop = is_develop()

    uvicorn.run(
        app="personal_secret.api.bin.server:app",
        host=str(os.environ[f"{environment.upper()}_API_HOST"]),
        port=int(os.environ[f"{environment.upper()}_API_CONTAINER_PORT"]),
        reload=develop,
    )