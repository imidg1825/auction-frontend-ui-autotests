"""
Раздел «Мои объявления» в личном кабинете.

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
MY_ADS_PATH = re.compile(r"/profile/myAds/?$")
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


def _my_ads_heading(page):
    return page.locator("main").get_by_role("heading", name="Мои объявления")


def _open_my_ads_from_profile_menu(page):
    """Меню по аватару → ссылка «Мои объявления»."""
    page.set_viewport_size(VIEWPORT_MOBILE)
    _open_home(page)
    page.locator("header button[class*='linkAvatar']").click()
    expect(page.get_by_role("link", name="Мои объявления")).to_be_visible(
        timeout=15_000
    )
    page.get_by_role("link", name="Мои объявления").click()
    expect(page).to_have_url(MY_ADS_PATH, timeout=30_000)
    expect(_my_ads_heading(page)).to_be_visible(timeout=30_000)
    page.wait_for_timeout(4000)


def _listing_links(page):
    """Ссылки на карточки объявлений или аукционов в контенте страницы."""
    return page.locator("main").locator(
        'a[href*="/product/"], a[href*="/auction/"]'
    )


@allure.epic("UI Auction")
@allure.feature("My Ads")
def test_my_ads_opens_from_profile_menu(page):
    """Раздел «Мои объявления» открывается из меню профиля."""
    _open_my_ads_from_profile_menu(page)


@allure.epic("UI Auction")
@allure.feature("My Ads")
def test_my_ads_url(page):
    """URL соответствует разделу моих объявлений."""
    _open_my_ads_from_profile_menu(page)
    expect(page).to_have_url(MY_ADS_PATH)


@allure.epic("UI Auction")
@allure.feature("My Ads")
def test_my_ads_page_shows_section_marker(page):
    """На странице явно виден раздел «Мои объявления»."""
    _open_my_ads_from_profile_menu(page)
    expect(_my_ads_heading(page)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("My Ads")
def test_my_ads_list_cards_or_empty_state(page):
    """Либо список/карточки объявлений, либо пустое состояние / их отсутствие."""
    _open_my_ads_from_profile_menu(page)
    main = page.locator("main")
    links = _listing_links(page)
    cards = main.locator('[class*="Card"]')

    if links.count() >= 1:
        expect(links.first).to_be_visible()
        return
    if cards.count() >= 1:
        expect(cards.first).to_be_visible()
        return

    hint = main.get_by_text(
        re.compile(
            r"нет объявлен|пока нет|ничего нет|разместите|создайте|пусто|не найден",
            re.I,
        )
    )
    if hint.count() > 0 and hint.first.is_visible():
        expect(hint.first).to_be_visible()
    else:
        expect(links).to_have_count(0)


@allure.epic("UI Auction")
@allure.feature("My Ads")
def test_my_ads_tabs_when_present(page):
    """Переключатели «Объявления / Аукционы» и статусы отображаются, если есть в разметке."""
    _open_my_ads_from_profile_menu(page)
    main = page.locator("main")

    type_ads = main.get_by_role("button", name="Объявления")
    type_auc = main.get_by_role("button", name="Аукционы")
    if type_ads.count() == 0 and type_auc.count() == 0:
        pytest.skip("Нет переключателей типа на странице моих объявлений.")

    expect(type_ads.first).to_be_visible()
    expect(type_auc.first).to_be_visible()

    active_tab = main.get_by_role("button", name=re.compile(r"Активные"))
    mod_tab = main.get_by_role("button", name="На модерации")
    arch_tab = main.get_by_role("button", name="Архив")

    if active_tab.count() == 0 and mod_tab.count() == 0 and arch_tab.count() == 0:
        pytest.skip("Нет переключателей статуса (активные / модерация / архив).")

    if active_tab.count() > 0:
        expect(active_tab.first).to_be_visible()
    if mod_tab.count() > 0:
        expect(mod_tab.first).to_be_visible()
    if arch_tab.count() > 0:
        expect(arch_tab.first).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("My Ads")
def test_my_ads_open_listing_when_link_available(page):
    """Переход по объявлению из раздела открывает страницу товара или аукциона."""
    _open_my_ads_from_profile_menu(page)
    links = _listing_links(page)
    if links.count() == 0:
        pytest.skip("Нет ссылок на объявления в списке.")

    expect(links.first).to_be_visible()
    links.first.click(no_wait_after=True)
    expect(page).to_have_url(PRODUCT_OR_AUCTION_PATH, timeout=30_000)
