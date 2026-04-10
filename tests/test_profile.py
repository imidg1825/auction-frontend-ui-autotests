"""
Личный кабинет (авторизованный пользователь).

Сессия задаётся в conftest через auth/state.json.
"""

from pathlib import Path

import allure
import pytest
from playwright.sync_api import expect


STATE_JSON = Path(__file__).resolve().parent.parent / "auth" / "state.json"

pytestmark = pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — выполните auth/save_auth.py.",
)

VIEWPORT_MOBILE = {"width": 390, "height": 844}
VIEWPORT_DESKTOP = {"width": 1280, "height": 800}


def _dismiss_cookie_banner_if_visible(page):
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()


def _open_home(page):
    page.goto("/", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)


def _open_profile_drawer_mobile(page):
    page.set_viewport_size(VIEWPORT_MOBILE)
    _open_home(page)
    page.locator("header button[class*='linkAvatar']").click()
    expect(page.get_by_text("Мои объявления", exact=True)).to_be_visible(
        timeout=15_000
    )


@allure.epic("UI Auction")
@allure.feature("Profile")
def test_authenticated_user_sees_profile_link_in_header(page):
    """В шапке есть вход в профиль (ссылка с аватаром «И»), а не кнопка «Войти»."""
    page.set_viewport_size(VIEWPORT_DESKTOP)
    _open_home(page)

    profile = page.locator('header a[href="/profile/myAds"]')
    expect(profile).to_be_visible()
    expect(profile).to_contain_text("И")
    expect(page.get_by_role("button", name="Войти")).not_to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Profile")
def test_profile_avatar_opens_menu_with_sections(page):
    """Клик по аватару (моб.) открывает список разделов личного кабинета."""
    _open_profile_drawer_mobile(page)

    expect(page.get_by_role("link", name="Мои ставки")).to_be_visible()
    expect(page.get_by_role("link", name="Сообщения")).to_be_visible()
    expect(page.get_by_role("link", name="Уведомления")).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Profile")
def test_profile_menu_lists_main_cabinet_sections(page):
    """В меню есть основные разделы (как в UI стенда)."""
    _open_profile_drawer_mobile(page)

    expect(page.get_by_role("link", name="Мои объявления")).to_be_visible()
    expect(page.get_by_role("link", name="Избранное")).to_be_visible()
    expect(page.locator('a[href="/profile/settings"]')).to_be_visible()
    expect(page.get_by_text("Выход", exact=True)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Profile")
def test_navigate_to_my_ads_section(page):
    """Раздел «Мои объявления» открывается."""
    page.set_viewport_size(VIEWPORT_DESKTOP)
    page.goto("/profile/myAds", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)

    expect(page).to_have_url("https://front.test.kp.ktsf.ru/profile/myAds")
    main = page.locator("main")
    expect(main.get_by_role("heading", name="Мои объявления")).to_be_visible()
    expect(main.get_by_text("Зарегистрирован", exact=False)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Profile")
def test_navigate_to_favorites_section(page):
    """Раздел «Избранное» открывается."""
    page.set_viewport_size(VIEWPORT_DESKTOP)
    page.goto("/profile/favorites", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)

    expect(page).to_have_url("https://front.test.kp.ktsf.ru/profile/favorites")
    expect(
        page.locator("main").get_by_role("heading", name="Избранное")
    ).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Profile")
def test_navigate_to_settings_section(page):
    """Раздел «Настройки» открывается."""
    page.set_viewport_size(VIEWPORT_DESKTOP)
    page.goto("/profile/settings", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)

    expect(page).to_have_url("https://front.test.kp.ktsf.ru/profile/settings")
    expect(page.locator("main").get_by_text("Личные данные", exact=False)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Profile")
def test_logout_from_profile_menu(page):
    """Выход из аккаунта из мобильного меню профиля."""
    _open_profile_drawer_mobile(page)

    page.get_by_text("Выход", exact=True).click()
    expect(page).to_have_url("https://front.test.kp.ktsf.ru/", timeout=30_000)
    expect(page.locator('header a[href="/profile/myAds"]')).to_have_count(0)


@allure.epic("UI Auction")
@allure.feature("Profile")
def test_after_logout_sign_in_button_visible_on_desktop(page):
    """После выхода на десктопной ширине снова видна кнопка «Войти»."""
    _open_profile_drawer_mobile(page)
    page.get_by_text("Выход", exact=True).click()
    expect(page).to_have_url("https://front.test.kp.ktsf.ru/", timeout=30_000)

    page.set_viewport_size(VIEWPORT_DESKTOP)

    expect(page.get_by_role("button", name="Войти")).to_be_visible(timeout=15_000)
