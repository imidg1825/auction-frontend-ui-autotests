"""
Раздел «Уведомления» в личном кабинете.

Сессия задаётся в conftest через auth/state.json.
"""

import re
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
NOTIFICATIONS_PATH = re.compile(r"/profile/notifications/?$")
PRODUCT_OR_AUCTION_PATH = re.compile(r".*/(product|auction)/[^/?#]+", re.I)


def _dismiss_cookie_banner_if_visible(page):
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()


def _open_home(page):
    page.goto("/", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)


def _notifications_heading(page):
    return page.locator("main").get_by_role("heading", name="Уведомления")


def _open_notifications_from_profile_menu(page):
    """Меню по аватару → ссылка «Уведомления» (как в test_profile)."""
    page.set_viewport_size(VIEWPORT_MOBILE)
    _open_home(page)
    page.locator("header button[class*='linkAvatar']").click()
    expect(page.get_by_role("link", name="Уведомления")).to_be_visible(timeout=15_000)
    page.get_by_role("link", name="Уведомления").click()
    expect(page).to_have_url(NOTIFICATIONS_PATH, timeout=30_000)
    expect(_notifications_heading(page)).to_be_visible(timeout=30_000)
    page.wait_for_timeout(4000)


def _notification_target_links(page):
    """Ссылки из уведомлений на объявление или аукцион (реальные цели на стенде)."""
    return page.locator("main").locator(
        'a[href*="/product/"], a[href*="/auction/"]'
    )


@allure.epic("UI Auction")
@allure.feature("Notifications")
def test_notifications_opens_from_profile_menu(page):
    """Раздел «Уведомления» открывается из меню профиля."""
    _open_notifications_from_profile_menu(page)


@allure.epic("UI Auction")
@allure.feature("Notifications")
def test_notifications_url(page):
    """URL соответствует разделу уведомлений."""
    _open_notifications_from_profile_menu(page)
    expect(page).to_have_url(NOTIFICATIONS_PATH)


@allure.epic("UI Auction")
@allure.feature("Notifications")
def test_notifications_page_shows_section_marker(page):
    """На странице явно виден раздел уведомлений (заголовок)."""
    _open_notifications_from_profile_menu(page)
    expect(_notifications_heading(page)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Notifications")
def test_notifications_list_cards_or_empty_state(page):
    """
    Либо есть элементы со ссылками на товар/аукцион,
    либо пустое состояние / их отсутствие.
    """
    _open_notifications_from_profile_menu(page)
    main = page.locator("main")
    targets = _notification_target_links(page)
    cards = main.locator('[class*="Card"]')

    if targets.count() >= 1:
        expect(targets.first).to_be_visible()
        return
    if cards.count() >= 1:
        expect(cards.first).to_be_visible()
        return

    hint = main.get_by_text(
        re.compile(r"нет уведомлен|пока нет|ничего нет|пусто|не найден", re.I)
    )
    if hint.count() > 0 and hint.first.is_visible():
        expect(hint.first).to_be_visible()
    else:
        expect(targets).to_have_count(0)


@allure.epic("UI Auction")
@allure.feature("Notifications")
def test_notifications_click_opens_target_when_available(page):
    """Клик по уведомлению ведёт на страницу объявления или аукциона."""
    _open_notifications_from_profile_menu(page)
    targets = _notification_target_links(page)
    if targets.count() == 0:
        pytest.skip("Нет уведомлений со ссылкой на товар или аукцион.")

    expect(targets.first).to_be_visible()
    targets.first.click(no_wait_after=True)
    expect(page).to_have_url(PRODUCT_OR_AUCTION_PATH, timeout=30_000)
