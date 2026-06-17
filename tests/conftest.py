import pytest


@pytest.fixture
def tenant_id() -> str:
    return "acme"


@pytest.fixture
def agent_id() -> str:
    return "test-agent"
