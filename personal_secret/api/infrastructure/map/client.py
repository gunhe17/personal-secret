from __future__ import annotations

from personal_secret.api.infrastructure.map import schema
from personal_secret.api.infrastructure.map import usecase
from personal_secret.api.infrastructure.map import endpoint
from personal_secret.api.infrastructure.map import repository
from personal_secret.api.infrastructure.map import domain
from personal_secret.api.infrastructure.map import exception


# #
# map

class Map:
    def build(self) -> dict:
        facts = schema.build_schema()
        usecases = usecase.build_usecases()
        return {
            "tables": facts["tables"],
            "rels": facts["rels"],
            "usecases": usecases,
            "endpoints": endpoint.build_endpoints(usecases),
            "repositories": repository.build_repositories(),
            "repo_tables": repository.build_repo_tables(),
            "value_objects": domain.build_value_objects(),
            "entities": domain.build_entities(),
            "events": domain.build_events(),
            "exceptions": exception.build_exceptions(usecases),
        }


# #
# client

map_client = Map()
