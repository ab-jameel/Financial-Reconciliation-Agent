# backend/orchestration/src/recon_orchestration/graph/migrations.py
"""When GRAPH_VERSION changes, a resumed checkpoint's state["graph_version"]
may not match the current constant. MIGRATIONS maps an old version to a
transform function. No migration registered for an old version -> resuming
must fail loudly and route to manual handling, never silently proceed with
a mismatched schema. This is called at the API layer before resuming (Phase 2
has no automatic hook for it — noted honestly rather than implied)."""
from recon_orchestration.graph.state import GRAPH_VERSION

MIGRATIONS = {
    # "v1": lambda old_state: {**old_state, "some_new_field": default},
}


class UnmigratableCheckpointError(Exception):
    pass


def migrate_state_if_needed(state: dict) -> dict:
    version = state.get("graph_version", GRAPH_VERSION)
    if version == GRAPH_VERSION:
        return state
    migrate_fn = MIGRATIONS.get(version)
    if migrate_fn is None:
        raise UnmigratableCheckpointError(
            f"No migration from graph_version={version!r} to {GRAPH_VERSION!r}. "
            "Case needs manual review before it can resume."
        )
    return migrate_fn(state)