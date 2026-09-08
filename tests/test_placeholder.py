"""Smoke test that the workspace and its key dependencies import cleanly."""

def test_core_imports():
    """Fail fast if the environment or workspace linking is broken."""
    import fastapi
    import langgraph
    import qdrant_client
    import langsmith
    import litellm
    import recon_common  # proves the workspace member resolves
    assert True
