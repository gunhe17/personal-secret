from __future__ import annotations

from personal_secret.api.infrastructure.map import schema
from personal_secret.api.infrastructure.map import usecase
from personal_secret.api.infrastructure.map import endpoint
from personal_secret.api.infrastructure.map import repository
from personal_secret.api.infrastructure.map import domain


# #
# map

class Map:
    def build(self) -> dict:
        facts = schema.build_schema()
        return {
            "tables": facts["tables"],
            "rels": facts["rels"],
            "usecases": usecase.build_usecases(),
            "endpoints": endpoint.build_endpoints(),
            "repositories": repository.build_repositories(),
            "repo_tables": repository.build_repo_tables(),
            "value_objects": domain.build_value_objects(),
            "entities": domain.build_entities(),
            "events": domain.build_events(),
        }


# #
# client

map_client = Map()
