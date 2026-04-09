"""
Раздел «Избранное» (авторизованный пользователь, storage_state из conftest).
"""

from pathlib import Path

import pytest
from playwright.sync_api import expect


STATE_JSON = Path(__file__).resolve().parent.parent / "auth" / "state.json"

pytestmark = pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — выполните auth/save_auth.py.",
)

VIEWPORT_MOBILE = {"width": 390, "height": 844}


def _dismiss_cookie_banner_if_visible(page):
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()


def _open_favorites_page(page):
    page.goto("/profile/favorites", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)


def test_authenticated_user_can_open_favorites_section(page):
    """Авторизованный пользователь может открыть раздел «Избранное»."""
    _open_favorites_page(page)

    expect(page.locator("main")).to_be_visible()


def test_favorites_page_loads_successfully(page):
    """Страница «Избранное» загружается без ошибки (контент профиля на месте)."""
    _open_favorites_page(page)

    expect(page.locator("main").get_by_text("Зарегистрирован", exact=False)).to_be_visible()


def test_favorites_page_shows_section_heading(page):
    """На странице виден заголовок раздела «Избранное»."""
    _open_favorites_page(page)

    expect(
        page.locator("main").get_by_role("heading", name="Избранное")
    ).to_be_visible()


def test_favorites_url_is_profile_favorites(page):
    """URL соответствует разделу favorites."""
    _open_favorites_page(page)

    expect(page).to_have_url("https://front.test.kp.ktsf.ru/profile/favorites")


def test_favorites_shows_cards_when_has_listings(page):
    """Если в избранном есть объявления — они показываются карточками."""
    _open_favorites_page(page)

    cards = page.locator("main").locator('[class*="Card"]')
    if cards.count() == 0:
        pytest.skip("В избранном нет объявлений — проверка карточек не применима.")

    expect(cards.first).to_be_visible()


def test_favorites_empty_state_when_no_listings(page):
    """Если избранное пустое — нет карточек объявлений под разделом."""
    _open_favorites_page(page)

    main = page.locator("main")
    cards = main.locator('[class*="Card"]')
    if cards.count() > 0:
        pytest.skip("В избранном есть объявления — пустое состояние не проверяем.")

    expect(main.get_by_role("heading", name="Избранное")).to_be_visible()
    expect(cards).to_have_count(0)
    expect(main.get_by_text("Объявления", exact=True)).to_be_visible()
    expect(main.get_by_text("Аукционы", exact=True)).to_be_visible()


def test_open_favorites_from_profile_menu(page):
    """Переход в «Избранное» из мобильного меню профиля."""
    page.set_viewport_size(VIEWPORT_MOBILE)
    page.goto("/", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)

    page.locator("header button[class*='linkAvatar']").click()
    expect(page.get_by_role("link", name="Избранное")).to_be_visible(timeout=15_000)
    page.get_by_role("link", name="Избранное").click()

    expect(page).to_have_url("https://front.test.kp.ktsf.ru/profile/favorites", timeout=30_000)
    expect(page.locator("main").get_by_role("heading", name="Избранное")).to_be_visible()
