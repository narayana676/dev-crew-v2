"""Force LLM_PROVIDER=mock for the automated test suite regardless of local .env.

Real-Gemini exercising is done separately (scripts/manual runs), not via pytest,
so unit/integration tests stay deterministic and offline.
"""

import app.config as config_module


def pytest_configure(config):
    config_module.settings.LLM_PROVIDER = "mock"
