import time

import pytest


def guest_entry_visible(page) -> bool:
    """Возвращает True, если на странице видна кнопка/ссылка «Войти»."""
    btn = page.get_by_role("button", name="Войти")
    if btn.count() > 0 and btn.first.is_visible():
        return True

    link = page.get_by_role("link", name="Войти")
    if link.count() > 0 and link.first.is_visible():
        return True

    return False


def require_authenticated(page, timeout_ms: int = 12000) -> None:
    """
    Проверяет, что пользователь авторизован.
    Если сессия протухла и виден вход — делает pytest.skip().
    """
    if guest_entry_visible(page):
        pytest.skip("Не авторизован (state.json протух)")

    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if guest_entry_visible(page):
            pytest.skip("Не авторизован (state.json протух)")
        page.wait_for_timeout(300)