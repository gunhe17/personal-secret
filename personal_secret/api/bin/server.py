import os

from personal_secret.api.config import get_app_environment, is_develop
from personal_secret.api.server.server import personal_secret_api
from personal_secret.api.server import middleware
from personal_secret.api.server.router import Router
from personal_secret.api.endpoint import system
from personal_secret.api.endpoint import command
from personal_secret.api.endpoint import secret
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
    Router(path="/health", methods=["GET"], endpoint=system.health)
)
server.router(
    Router(path="/", methods=["GET"], endpoint=system.index)
)
server.router(
    Router(path="/styles.css", methods=["GET"], endpoint=system.styles)
)
server.router(
    Router(path="/styleguide", methods=["GET"], endpoint=system.styleguide)
)
server.router(
    Router(path="/commands", methods=["GET"], endpoint=command.list_commands)
)

# secret
server.router(
    Router(path="/secret", methods=["POST"], endpoint=secret.post_create)
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