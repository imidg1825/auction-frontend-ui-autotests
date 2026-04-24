"""
Аукцион: переход с главной и проверки UI ставок (сессия из conftest).
"""

import re
from pathlib import Path

import allure
import pytest
from playwright.sync_api import expect


STATE_JSON = Path(__file__).resolve().parent.parent / "auth" / "state.json"

pytestmark = pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — для окна ставки нужна авторизация.",
)


def _dismiss_cookie_dialogs(page):
    for _ in range(3):
        dlg = page.locator('[role="dialog"]')
        if dlg.count() == 0:
            return
        btn = dlg.first.get_by_role("button", name="Принять")
        if btn.count() == 0:
            return
        btn.click()
        page.wait_for_timeout(600)


def _auction_card_link(page):
    return page.locator("main").locator('a[href*="/auction/"]')


@allure.epic("UI Auction")
@allure.feature("Auction")
def test_skip_when_page_is_fixed_price_product(page):
    """Объявление по /product/ — не аукцион, проверки ставок не выполняются."""
    page.goto("/product/911", wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(3000)
    _dismiss_cookie_dialogs(page)

    if "/auction/" in page.url:
        pytest.fail("Ожидалась страница фиксированной цены.")

    pytest.skip("Это не аукцион (/product/) — сценарий ставок пропускается.")


def _open_first_auction_from_home(page):
    page.goto("/", wait_until="domcontentloaded", timeout=120_000)
    _dismiss_cookie_dialogs(page)

    auctions_tab = page.locator("main").get_by_text("Аукционы", exact=True)
    expect(auctions_tab).to_be_visible(timeout=60_000)
    auctions_tab.click()

    expect(page.locator("main").get_by_text("Новые аукционы", exact=False)).to_be_visible(
        timeout=60_000
    )

    link = _auction_card_link(page)
    try:
        expect(link.first).to_be_visible(timeout=60_000)
    except AssertionError:
        pytest.skip("На вкладке «Аукционы» нет карточки аукциона (ссылка /auction/).")

    link.first.click(no_wait_after=True)
    expect(page).to_have_url(re.compile(r".*/auction/"), timeout=60_000)


@allure.epic("UI Auction")
@allure.feature("Auction")
def test_auction_page_shows_current_stake_time_and_bid_cta(page):
    """Аукцион: текущая ставка/ставки, время до окончания, кнопка «Сделать ставку»."""
    _open_first_auction_from_home(page)

    expect(page).to_have_url(re.compile(r".*/auction/"))
    main = page.locator("main")
    expect(main).to_contain_text(re.compile(r"ставк", re.I))
    expect(main).to_contain_text(re.compile(r"осталось", re.I))
    expect(main).to_contain_text("₽")
    expect(page.get_by_role("button", name="Сделать ставку")).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Auction")
def test_auction_bid_dialog_accepts_amount_and_enables_confirm(page):
    """Ввод суммы в модалке ставки активирует «Подтвердить ставку»."""
    _open_first_auction_from_home(page)
    _dismiss_cookie_dialogs(page)

    page.get_by_role("button", name="Сделать ставку").click()
    modal = page.locator('[role="dialog"]').filter(has_text="Установить ставку")
    expect(modal).to_be_visible(timeout=15_000)

    confirm = modal.get_by_role("button", name="Подтвердить ставку")
    expect(confirm).to_be_disabled()

    amount = modal.get_by_placeholder("Введите сумму")
    expect(amount).to_be_visible()
    amount.fill("95000")
    expect(confirm).to_be_enabled()
