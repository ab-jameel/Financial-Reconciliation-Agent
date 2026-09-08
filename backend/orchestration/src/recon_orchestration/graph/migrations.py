"""State migrations applied when a checkpoint's graph version is out of date."""

from recon_orchestration.graph.state import GRAPH_VERSION

MIGRATIONS = {
    # "v1": lambda old_state: {**old_state, "some_new_field": default},
}


class UnmigratableCheckpointError(Exception):
    """Raised when a checkpoint's graph version has no registered migration."""
    pass


def migrate_state_if_needed(state: dict) -> dict:
    """Return the state migrated to the current graph version, if needed.

    Raises UnmigratableCheckpointError when no migration is registered for
    the checkpoint's version; the case must then be handled manually.
    """
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
