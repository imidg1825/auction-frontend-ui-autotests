import allure
import pytest

from utils.auth_helpers import guest_entry_visible


@allure.epic("UI Auction")
@allure.feature("Auth State")
def test_auth_state_is_valid(page):
    page.goto("/", wait_until="networkidle", timeout=120_000)
    if guest_entry_visible(page):
        pytest.fail("state.json невалиден: пользователь не авторизован")
