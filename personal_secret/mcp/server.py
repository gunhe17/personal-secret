import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from personal_secret.mcp.tools.dependency.dependency import dependency

server = FastMCP(
    "personal-secret-dev",
    host="0.0.0.0",
    port=int(os.environ["DEVELOP_MCP_CONTAINER_PORT"]),
    transport_security=(
        TransportSecuritySettings(
            allowed_hosts=[
                "mcp:*",
                "localhost:*",
                "127.0.0.1:*",
                "[::1]:*"
            ],
        )
    ),
)

# #
# Functions

@server.tool()
def ping() -> str:
    return "pong"


@server.tool()
def show_dependents(file: str, name: str | None = None, root: str | None = None) -> dict:
    """이 파일(과 심볼)에 의존하는 것들(dependents) — 즉 무엇이 이것을 import하는지(역참조)를 보여준다.

    다음과 같은 사용자 요청에서 호출되어야 한다:
    - "X의 의존처/사용처/참조 확인"
    - "X를 어디서 쓰는지/참조하는지/import하는지 찾아줘"
    - "X 사용처/레퍼런스/usage 조회"
    - "X를 수정하면 어디가 영향받나" (수정 전 임팩트 파악)
    - 특정 모듈·심볼이 어느 파일에서 import되는지 알고 싶을 때

    Args:
        file: 대상 .py 파일 경로
        name: 대상 심볼명 (클래스/함수/변수 등, 생략 시 모듈 전체)
        root: 스캔 루트 (생략 시 프로젝트 루트 자동 감지)
    """
    return dependency.dependents(file=file, name=name, root=root)


@server.tool()
def show_dependencies(file: str, root: str | None = None) -> dict:
    """이 파일이 의존하는 것들(dependencies) — 즉 무엇을 import하는지가 레이어 방향(INV-1)을 어겼는지 검사한다.

    다음과 같은 상황에서 호출되어야 한다:
    - 파일 편집/생성 직후 의존 방향 위반(상위 레이어 import) 검증
    - "이 파일이 레이어 규칙을 어겼는지/import 방향이 맞는지 확인"
    - "INV-1 / 의존 방향 / 레이어 위반 검사"

    의존 방향: bin→server→endpoint→usecase→domain→infrastructure, 모두 →core.
    상위 레이어를 import하면 violation=true. `import personal_secret.api.domain`(metadata 등록 idiom)은 예외(violation=false).

    Args:
        file: 검사 대상 .py 파일 경로 (personal_secret/api/ 밖이면 빈 결과)
        root: 스캔 루트 (생략 시 무관 — 경로에서 레이어 추론)

    Returns:
        {"source_layer": str|None,
         "dependencies": [{"module", "target_layer", "violation": bool}, ...]}
        — 내부(api) 의존성 전체, violation=true 가 INV-1 위반
    """
    return dependency.dependencies(file=file, root=root)


# #
# Run

if __name__ == "__main__":
    server.run(transport="streamable-http")
