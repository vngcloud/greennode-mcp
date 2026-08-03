"""Fixtures for agentbase-mcp-server tests (passthrough — no IAM, no creds).

Every upstream call in tests must carry Authorization: Bearer test-bearer,
forwarded from user_token_var — that is the core passthrough invariant.
"""

import pytest
from greennode.agentbase_mcp_server.auth import PassthroughTokenManager
from greennode.agentbase_mcp_server.client import AgentbaseClient
from greennode.agentbase_mcp_server.config import load_config
from greennode.mcp_core.http import user_token_var


@pytest.fixture
def config():
    return load_config(env={})


@pytest.fixture
def passthrough_token():
    """Set the caller bearer token for the test scope; reset after."""
    ctx = user_token_var.set("test-bearer")
    yield "test-bearer"
    user_token_var.reset(ctx)


@pytest.fixture
def policy_client(passthrough_token):
    return AgentbaseClient(config=load_config(env={}), token_manager=PassthroughTokenManager())
