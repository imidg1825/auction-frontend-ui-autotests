"""
Раздел «Мои ставки» в личном кабинете.

Сессия задаётся в conftest через auth/state.json.
"""

import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

STATE_JSON = Path(__file__).resolve().parent.parent / "auth" / "state.json"

pytestmark = pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — выполните auth/save_auth.py.",
)

VIEWPORT_MOBILE = {"width": 390, "height": 844}
MY_BIDS_PATH = re.compile(r"/profile/myBids/?$")
AUCTION_LOT_PATH = re.compile(r".*/auction/[^/?#]+", re.I)


def _dismiss_cookie_banner_if_visible(page):
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()


def _open_home(page):
    page.goto("/", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)


def _my_bids_heading(page):
    return page.locator("main").get_by_role("heading", name="Мои ставки")


def _open_my_bids_from_profile_menu(page):
    """Меню по аватару → ссылка «Мои ставки»."""
    page.set_viewport_size(VIEWPORT_MOBILE)
    _open_home(page)
    page.locator("header button[class*='linkAvatar']").click()
    expect(page.get_by_role("link", name="Мои ставки")).to_be_visible(timeout=15_000)
    page.get_by_role("link", name="Мои ставки").click()
    expect(page).to_have_url(MY_BIDS_PATH, timeout=30_000)
    expect(_my_bids_heading(page)).to_be_visible(timeout=30_000)
    # список ставок и переключатели подгружаются после первого paint
    page.wait_for_timeout(8000)


def _auction_lot_links(page):
    """Ссылки на лоты в контенте (не меню кабинета)."""
    return page.locator("main").locator('a[href*="/auction/"]')


def test_my_bids_opens_from_profile_menu(page):
    """Раздел «Мои ставки» открывается из меню профиля."""
    _open_my_bids_from_profile_menu(page)


def test_my_bids_url(page):
    """URL соответствует разделу моих ставок."""
    _open_my_bids_from_profile_menu(page)
    expect(page).to_have_url(MY_BIDS_PATH)


def test_my_bids_page_shows_section_marker(page):
    """На странице явно виден раздел «Мои ставки»."""
    _open_my_bids_from_profile_menu(page)
    expect(_my_bids_heading(page)).to_be_visible()


def test_my_bids_list_or_empty_state(page):
    """
    Либо есть ссылки на аукционы в списке ставок,
    либо пустое состояние / отсутствие таких ссылок.
    """
    _open_my_bids_from_profile_menu(page)
    main = page.locator("main")
    lots = _auction_lot_links(page)

    if lots.count() >= 1:
        expect(lots.first).to_be_visible()
        return

    hint = main.get_by_text(
        re.compile(
            r"ставок нет|нет активных|нет ставок|пока нет|ничего нет|не найден",
            re.I,
        )
    )
    if hint.count() > 0 and hint.first.is_visible():
        expect(hint.first).to_be_visible()
    else:
        expect(lots).to_have_count(0)


def test_my_bids_tabs_when_present(page):
    """Переключатели «Активные» / «Завершённые» отображаются, если есть в разметке."""
    _open_my_bids_from_profile_menu(page)
    main = page.locator("main")

    active_btn = main.get_by_role("button", name="Активные")
    done_btn = main.get_by_role("button", name="Завершённые")
    if active_btn.count() == 0 or done_btn.count() == 0:
        pytest.skip("Нет переключателей статуса ставок на стенде.")

    expect(active_btn.first).to_be_visible()
    expect(done_btn.first).to_be_visible()


def test_my_bids_open_auction_when_link_available(page):
    """Переход по ставке открывает страницу аукциона."""
    _open_my_bids_from_profile_menu(page)
    lots = _auction_lot_links(page)
    if lots.count() == 0:
        pytest.skip("Нет ссылок на лоты в списке ставок.")

    expect(lots.first).to_be_visible()
    lots.first.click(no_wait_after=True)
    expect(page).to_have_url(AUCTION_LOT_PATH, timeout=30_000)
