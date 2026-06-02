# #
# registry — web slash-command palette. single source the web reads via /commands.
# (style-guide 레퍼런스: create만 유지)

COMMANDS = [
    {"name": "new", "hint": "create a secret", "kind": "form"},
]


# #
# endpoint

def list_commands() -> list[dict]:
    return COMMANDS
