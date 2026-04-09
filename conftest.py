from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest
from playwright.sync_api import Playwright


ROOT = Path(__file__).resolve().parent
AUTH_STATE_PATH = ROOT / "auth" / "state.json"
BASE_URL = "https://front.test.kp.ktsf.ru/"


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def browser_context_args(
    pytestconfig: pytest.Config,
    playwright: Playwright,
    device: Optional[str],
    base_url: Optional[str],
    _pw_artifacts_folder,
) -> dict:
    """Как в pytest-playwright, плюс storage_state из auth/state.json при наличии файла."""
    context_args: dict = {}
    if device:
        context_args.update(playwright.devices[device])
    if base_url:
        context_args["base_url"] = base_url

    if AUTH_STATE_PATH.is_file():
        context_args["storage_state"] = str(AUTH_STATE_PATH)

    video_option = pytestconfig.getoption("--video")
    if video_option in ("on", "retain-on-failure"):
        context_args["record_video_dir"] = _pw_artifacts_folder.name

    return context_args


@pytest.fixture
def guest_page(browser, base_url: str):
    """Контекст без storage_state — гостевые сценарии при наличии auth/state.json в основном контексте."""
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    yield page
    context.close()
