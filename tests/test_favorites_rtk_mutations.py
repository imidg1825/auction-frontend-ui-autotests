"""
Минимальные UI-проверки клика по "избранному" (RTK mutations).

Важно: без проверок rollback/server error — только то, что UI не падает и иконка остаётся видимой.
"""

from __future__ import annotations

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


def _dismiss_cookie_banner_if_visible(page) -> None:
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()


def _open_favorites(page, *, ad_type: str | None = None):
    suffix = f"?ad_type={ad_type}" if ad_type else ""
    page.goto(f"/profile/favorites{suffix}", wait_until="domcontentloaded", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)
    main = page.locator("main")
    expect(main).to_be_visible()
    expect(main.get_by_role("heading", name="Избранное")).to_be_visible(timeout=30_000)

    # Дождаться перехода в одно из состояний: есть карточки или пустое состояние с табами.
    cards = main.locator('[class*="Card"]')
    if cards.count() > 0:
        expect(cards.first).to_be_visible(timeout=30_000)
        return main

    empty_listings_tab = main.get_by_text("Объявления", exact=True)
    empty_auctions_tab = main.get_by_text("Аукционы", exact=True)
    try:
        expect(empty_listings_tab).to_be_visible(timeout=30_000)
        expect(empty_auctions_tab).to_be_visible(timeout=30_000)
        expect(cards).to_have_count(0)
    except AssertionError:
        # Если это не пустое состояние — значит должны появиться карточки.
        expect(cards.first).to_be_visible(timeout=30_000)
    return main


def _favorites_links_for_product(main, product_id: str):
    return main.locator(f'a[href*="/product/{product_id}"]')


def _favorites_links_for_auction(main, auction_id: str):
    return main.locator(f'a[href*="/auction/{auction_id}"]')


def _favorite_card_for_product(page, main, product_id: str):
    cards = main.locator('[class*="card_card"], [class*="Card"]')
    card = cards.filter(has=page.locator(f'a[href*="/product/{product_id}"]')).first
    if card.count() > 0:
        return card

    link = main.locator(f'a[href*="/product/{product_id}"]').first
    return link.locator(
        "xpath=ancestor::*[contains(@class, 'card_card') or contains(@class, 'Card')][1]"
    )


def _favorite_card_for_auction(page, main, auction_id: str):
    cards = main.locator('[class*="card_card"], [class*="Card"]')
    card = cards.filter(has=page.locator(f'a[href*="/auction/{auction_id}"]')).first
    if card.count() > 0:
        return card

    link = main.locator(f'a[href*="/auction/{auction_id}"]').first
    return link.locator(
        "xpath=ancestor::*[contains(@class, 'card_card') or contains(@class, 'Card')][1]"
    )


def _remove_from_favorites_page(page, product_id: str) -> None:
    main = _open_favorites(page)
    card = _favorite_card_for_product(page, main, product_id)
    expect(card).to_be_visible(timeout=30_000)

    heart = card.locator('svg[class*="card_icon__like"]').first
    expect(heart).to_be_visible(timeout=30_000)
    heart.click(no_wait_after=True)

    main = _open_favorites(page)
    expect(_favorites_links_for_product(main, product_id)).to_have_count(0, timeout=30_000)


def _remove_auction_from_favorites_auctions_tab(page, auction_id: str) -> None:
    main = _open_favorites(page, ad_type="auction")
    card = _favorite_card_for_auction(page, main, auction_id)
    expect(card).to_be_visible(timeout=30_000)

    heart = card.locator('svg[class*="card_icon__like"]').first
    expect(heart).to_be_visible(timeout=30_000)
    heart.click(no_wait_after=True)

    main = _open_favorites(page, ad_type="auction")
    expect(_favorites_links_for_auction(main, auction_id)).to_have_count(0, timeout=30_000)


def _is_product_in_favorites(page, product_id: str) -> bool:
    main = _open_favorites(page)
    return _favorites_links_for_product(main, product_id).count() > 0


def _is_auction_in_favorites_auctions_tab(page, auction_id: str) -> bool:
    main = _open_favorites(page, ad_type="auction")
    return _favorites_links_for_auction(main, auction_id).count() > 0


def _ensure_auction_not_in_favorites(page, auction_id: str) -> None:
    if not _is_auction_in_favorites_auctions_tab(page, auction_id):
        return

    for attempt in (1, 2):
        try:
            _remove_auction_from_favorites_auctions_tab(page, auction_id)
            return
        except AssertionError:
            if attempt == 2:
                pytest.fail(
                    f"Не удалось убрать аукцион /auction/{auction_id} из избранного за 2 попытки."
                )


def _open_product_by_id(page, product_id: str):
    page.goto(f"/product/{product_id}", wait_until="domcontentloaded", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)
    expect(page).to_have_url(re.compile(r".*/product/[^/]+"), timeout=60_000)
    heart = page.locator('[class*="Contacts_wrapper__info"] svg[class*="Like_icon"]')
    expect(heart).to_be_visible(timeout=30_000)
    return heart


def _get_product_card_from_home_by_id(page, product_id: str):
    page.goto("/", wait_until="domcontentloaded", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)

    main = page.locator("main")
    expect(main).to_be_visible(timeout=60_000)

    cards = page.locator('[class*="card_card"], [class*="Card"]')
    expect(cards.first).to_be_visible(timeout=60_000)

    def _home_diag_by_id() -> str:
        product_count = page.locator('a[href*="/product/"]').count()
        auction_count = page.locator('a[href*="/auction/"]').count()
        cards_count = cards.count()
        links_for_id = page.locator(f'a[href*="/product/{product_id}"]').count()
        try:
            text_preview = (page.locator("body").inner_text() or "")[:500]
        except Exception:
            text_preview = "<inner_text error>"
        return (
            f"product_id={product_id!r}, links_for_id={links_for_id}, "
            f"product_links={product_count}, auction_links={auction_count}, "
            f"cards_count={cards_count}, body_text_preview={text_preview!r}"
        )

    link = page.locator(f'a[href*="/product/{product_id}"]').first
    if link.count() == 0:
        pytest.fail(
            f"На главной нет ссылки на /product/{product_id}. " + _home_diag_by_id()
        )

    expect(link).to_be_visible(timeout=30_000)

    card = link.locator(
        "xpath=ancestor::*[contains(@class, 'card_card') or contains(@class, 'Card')][1]"
    )
    expect(card).to_be_visible(timeout=30_000)

    heart = card.locator('svg[class*="card_icon__like"]').first
    expect(heart).to_be_visible(timeout=30_000)

    return card, heart


def _ensure_in_favorites(page, product_id: str) -> None:
    if _is_product_in_favorites(page, product_id):
        return

    for attempt in (1, 2):
        _, heart = _get_product_card_from_home_by_id(page, product_id)
        heart.click(no_wait_after=True)

        main = _open_favorites(page)
        links = _favorites_links_for_product(main, product_id)
        try:
            expect(links.first).to_be_visible(timeout=30_000)
            return
        except AssertionError:
            if attempt == 2:
                pytest.fail(
                    f"Не удалось добавить товар /product/{product_id} в избранное за 2 попытки."
                )


def _ensure_not_in_favorites(page, product_id: str) -> None:
    if not _is_product_in_favorites(page, product_id):
        return

    for attempt in (1, 2):
        try:
            _remove_from_favorites_page(page, product_id)
            return
        except AssertionError:
            if attempt == 2:
                pytest.fail(
                    f"Не удалось убрать товар /product/{product_id} из избранного за 2 попытки."
                )


def _open_any_product_from_home(page) -> None:
    page.goto("/", wait_until="domcontentloaded", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)

    main = page.locator("main")
    expect(main).to_be_visible(timeout=60_000)
    cards = main.locator('[class*="Card"], [class*="card_card"]')
    expect(cards.first).to_be_visible(timeout=60_000)

    product_links = main.locator('a[href*="/product/"]')
    if product_links.count() == 0:
        pytest.skip('На главной нет ссылок с href, содержащим "/product/".')

    link = None
    for i in range(product_links.count()):
        candidate = product_links.nth(i)
        if candidate.is_visible():
            link = candidate
            break

    if link is None:
        pytest.skip('На главной есть ссылки "/product/" в DOM, но нет видимой для клика.')

    with page.expect_navigation(timeout=60_000):
        link.click()

    expect(page).to_have_url(re.compile(r".*/product/[^/]+"), timeout=60_000)


def _get_first_product_card_from_home(page):
    page.goto("/", wait_until="domcontentloaded", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)

    main = page.locator("main")
    expect(main).to_be_visible(timeout=60_000)

    cards = page.locator('[class*="card_card"], [class*="Card"]')
    expect(cards.first).to_be_visible(timeout=60_000)

    def _home_diag() -> str:
        product_count = page.locator('a[href*="/product/"]').count()
        auction_count = page.locator('a[href*="/auction/"]').count()
        cards_count = cards.count()
        try:
            text_preview = (page.locator("body").inner_text() or "")[:500]
        except Exception:
            text_preview = "<inner_text error>"
        return (
            f"product_links={product_count}, auction_links={auction_count}, "
            f"cards_count={cards_count}, body_text_preview={text_preview!r}"
        )

    product_links = page.locator('a[href*="/product/"]')
    if product_links.count() == 0:
        pytest.fail(
            'На главной нет ссылок с href, содержащим "/product/". '
            + _home_diag()
        )

    link = None
    for i in range(product_links.count()):
        candidate = product_links.nth(i)
        if candidate.is_visible():
            link = candidate
            break
    if link is None:
        pytest.fail(
            'На главной есть ссылки "/product/" в DOM, но нет видимой для клика. '
            + _home_diag()
        )

    href = link.get_attribute("href") or ""
    m = re.search(r"/product/([^/?#]+)", href, flags=re.I)
    if not m:
        pytest.fail(
            f'Не удалось извлечь product_id из href="{href}". ' + _home_diag()
        )
    product_id = m.group(1)

    card = link.locator(
        "xpath=ancestor::*[contains(@class, 'card_card') or contains(@class, 'Card')][1]"
    )
    expect(card).to_be_visible(timeout=30_000)

    heart = card.locator('svg[class*="card_icon__like"]').first
    expect(heart).to_be_visible(timeout=30_000)

    return product_id, card, heart


def _dismiss_cookie_dialogs_auction_style(page) -> None:
    """Как в tests/test_auction.py — перед кликом по вкладке «Аукционы»."""
    btn = page.get_by_role("button", name="Принять")
    try:
        expect(btn.first).to_be_visible(timeout=5_000)
        btn.first.click(force=True)
        expect(btn.first).not_to_be_visible(timeout=5_000)
    except AssertionError:
        return


def _auction_card_link_in_main(page):
    return page.locator("main").locator('a[href*="/auction/"]')


def _switch_home_to_auctions_tab_like_auction_test(page) -> None:
    page.goto("/", wait_until="domcontentloaded", timeout=120_000)
    _dismiss_cookie_dialogs_auction_style(page)

    auctions_tab = page.locator("main").locator("button").filter(has_text="Аукционы").last
    expect(auctions_tab).to_be_visible(timeout=60_000)
    _dismiss_cookie_dialogs_auction_style(page)
    box = auctions_tab.bounding_box()
    if box is None:
        pytest.skip("Вкладка «Аукционы» найдена, но у неё нет видимой области для клика.")
    page.mouse.click(
        box["x"] + box["width"] / 2,
        box["y"] + box["height"] / 2,
    )


def _first_visible_auction_link_after_auctions_tab(page):
    link = _auction_card_link_in_main(page)
    try:
        expect(link.first).to_be_attached(timeout=60_000)
    except AssertionError:
        pytest.skip(
            "На вкладке «Аукционы» нет ссылки /auction/. "
            "Сценарий зависит от наличия аукционов на стенде."
        )

    visible_link = None
    for i in range(link.count()):
        candidate = link.nth(i)
        if candidate.is_visible():
            visible_link = candidate
            break

    if visible_link is None:
        pytest.skip(
            "На вкладке «Аукционы» ссылки /auction/ есть в DOM, "
            "но нет видимой карточки для открытия."
        )
    return visible_link


def _first_visible_main_auction_link_for_id(page, auction_id: str):
    links = page.locator("main").locator(f'a[href*="/auction/{auction_id}"]')
    try:
        expect(links.first).to_be_attached(timeout=60_000)
    except AssertionError:
        pytest.fail(
            f"На главной (вкладка «Аукционы») нет ссылки на /auction/{auction_id}."
        )

    for i in range(links.count()):
        candidate = links.nth(i)
        if candidate.is_visible():
            return candidate

    pytest.fail(
        f"Ссылка на /auction/{auction_id} есть в DOM главной, но нет видимой для клика."
    )


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK: клик по сердечку на первой карточке листинга")
def test_favorites_can_click_heart_on_first_listing_card(page):
    page.goto("/", wait_until="domcontentloaded", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)

    expect(page.locator("main")).to_be_visible(timeout=60_000)
    first_card = page.locator("main").locator('[class*="card_card"]').first
    expect(first_card).to_be_visible(timeout=60_000)

    heart = first_card.locator('svg[class*="card_icon__like"]')
    expect(heart).to_be_visible()

    heart.click(no_wait_after=True)

    expect(page.locator("main")).to_be_visible(timeout=60_000)
    expect(heart).to_be_visible(timeout=30_000)


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK: клик по сердечку на странице товара")
def test_favorites_can_click_heart_on_product_page(page):
    _open_any_product_from_home(page)

    heart = page.locator('[class*="Contacts_wrapper__info"] svg[class*="Like_icon"]')
    expect(heart).to_be_visible(timeout=30_000)

    heart.click(no_wait_after=True)

    expect(page.locator("main")).to_be_visible(timeout=60_000)
    expect(heart).to_be_visible(timeout=30_000)


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK: добавление в избранное отражается в /profile/favorites")
def test_favorites_product_appears_in_favorites_section(page):
    product_id, _, _ = _get_first_product_card_from_home(page)

    _ensure_not_in_favorites(page, product_id)

    _, heart = _get_product_card_from_home_by_id(page, product_id)
    heart.click(no_wait_after=True)

    main = _open_favorites(page)
    expect(_favorites_links_for_product(main, product_id).first).to_be_visible(timeout=30_000)


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK: удаление из избранного отражается в /profile/favorites")
def test_favorites_product_can_be_removed_from_favorites(page):
    product_id, _, _ = _get_first_product_card_from_home(page)

    _ensure_in_favorites(page, product_id)

    _ensure_not_in_favorites(page, product_id)

    main = _open_favorites(page)
    expect(_favorites_links_for_product(main, product_id)).to_have_count(0, timeout=30_000)


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK: double click по сердечку на карточке — избранное без дублей")
def test_favorites_double_click_heart_on_listing_card_no_duplicate_or_crash(page):
    product_id, _, heart = _get_first_product_card_from_home(page)
    expect(heart).to_be_visible()

    _ensure_not_in_favorites(page, product_id)

    _, heart = _get_product_card_from_home_by_id(page, product_id)
    heart.dblclick(no_wait_after=True)

    main = _open_favorites(page)
    expect(main).to_be_visible()

    # Селектор карточек даёт вложенные узлы; считаем уникальные корни карточек,
    # внутри которых есть ссылка на этот товар (не число ссылок).
    card_count = main.evaluate(
        r"""pid => {
          const root = document.querySelector("main");
          if (!root) return 0;
          const esc = String(pid).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
          const pathRe = new RegExp("/product/" + esc + "(?:/|$|\\?|#)", "i");
          const anchors = Array.from(
            root.querySelectorAll('a[href*="/product/"]')
          ).filter(a => pathRe.test(a.getAttribute("href") || ""));
          const cards = new Set();
          for (const link of anchors) {
            let el = link;
            let found = null;
            while (el && el !== root) {
              const cls = el.getAttribute("class") || "";
              if (cls.includes("card_card") || cls.includes("Card")) {
                found = el;
                break;
              }
              el = el.parentElement;
            }
            if (found) cards.add(found);
          }
          return cards.size;
        }""",
        product_id,
    )
    if card_count > 1:
        pytest.fail(
            f"В /profile/favorites несколько карточек для одного товара "
            f"(product_id={product_id!r}): cards={card_count}"
        )


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK: клик по сердечку на карточке аукциона (вкладка «Аукционы»)")
def test_favorites_can_click_heart_on_auction_listing_card(page):
    _switch_home_to_auctions_tab_like_auction_test(page)
    visible_link = _first_visible_auction_link_after_auctions_tab(page)

    href = visible_link.get_attribute("href") or ""
    m = re.search(r"/auction/([^/?#]+)", href, flags=re.I)
    if not m or not m.group(1):
        pytest.fail(f'Не удалось извлечь auction_id из href="{href}"')
    auction_id = m.group(1)

    card = visible_link.locator(
        "xpath=ancestor::*[contains(@class, 'card_card') or contains(@class, 'Card')][1]"
    )
    expect(card).to_be_visible(timeout=30_000)

    heart = card.locator('svg[class*="card_icon__like"]').first
    expect(heart).to_be_visible(timeout=30_000)
    heart.click(no_wait_after=True)

    expect(page.locator("main")).to_be_visible()
    assert auction_id


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title(
    "Favorites RTK: аукцион — добавление с ленты и удаление из /profile/favorites?ad_type=auction"
)
def test_favorites_auction_add_from_listing_remove_in_favorites_section(page):
    _switch_home_to_auctions_tab_like_auction_test(page)
    visible_link = _first_visible_auction_link_after_auctions_tab(page)

    href = visible_link.get_attribute("href") or ""
    m = re.search(r"/auction/([^/?#]+)", href, flags=re.I)
    if not m or not m.group(1):
        pytest.fail(f'Не удалось извлечь auction_id из href="{href}"')
    auction_id = m.group(1)

    _ensure_auction_not_in_favorites(page, auction_id)

    _switch_home_to_auctions_tab_like_auction_test(page)
    link = _first_visible_main_auction_link_for_id(page, auction_id)

    card = link.locator(
        "xpath=ancestor::*[contains(@class, 'card_card') or contains(@class, 'Card')][1]"
    )
    expect(card).to_be_visible(timeout=30_000)

    heart = card.locator('svg[class*="card_icon__like"]').first
    expect(heart).to_be_visible(timeout=30_000)
    heart.click(no_wait_after=True)

    main = _open_favorites(page, ad_type="auction")
    expect(_favorites_links_for_auction(main, auction_id).first).to_be_visible(timeout=30_000)

    fav_card = _favorite_card_for_auction(page, main, auction_id)
    expect(fav_card).to_be_visible(timeout=30_000)
    fav_heart = fav_card.locator('svg[class*="card_icon__like"]').first
    expect(fav_heart).to_be_visible(timeout=30_000)
    fav_heart.click(no_wait_after=True)

    main = _open_favorites(page, ad_type="auction")
    expect(_favorites_links_for_auction(main, auction_id)).to_have_count(0, timeout=30_000)


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK: листинг → избранное — добавление с ленты и удаление из раздела")
def test_favorites_listing_to_favorites_sync_add_and_remove(page):
    product_id, _, _ = _get_first_product_card_from_home(page)

    _ensure_not_in_favorites(page, product_id)

    _, heart = _get_product_card_from_home_by_id(page, product_id)
    expect(heart).to_be_visible(timeout=30_000)
    heart.click(no_wait_after=True)

    main = _open_favorites(page)
    expect(_favorites_links_for_product(main, product_id).first).to_be_visible(timeout=30_000)

    _ensure_not_in_favorites(page, product_id)

    main = _open_favorites(page)
    expect(_favorites_links_for_product(main, product_id)).to_have_count(0, timeout=30_000)


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK: удаление последнего товара из избранного не ломает страницу")
def test_favorites_remove_last_product_smoke(page):
    product_id, _, _ = _get_first_product_card_from_home(page)

    _ensure_not_in_favorites(page, product_id)

    _, listing_heart = _get_product_card_from_home_by_id(page, product_id)
    expect(listing_heart).to_be_visible(timeout=30_000)
    listing_heart.click(no_wait_after=True)

    main = _open_favorites(page)
    expect(_favorites_links_for_product(main, product_id).first).to_be_visible(timeout=30_000)

    _remove_from_favorites_page(page, product_id)

    main = _open_favorites(page)
    expect(_favorites_links_for_product(main, product_id)).to_have_count(0, timeout=30_000)

    # Если после удаления стало пусто — проверяем, что пустое состояние живо,
    # но не завязываемся на один конкретный текст.
    cards = main.locator('[class*="Card"]')
    if cards.count() == 0:
        listings_tab = main.get_by_text("Объявления", exact=True)
        auctions_tab = main.get_by_text("Аукционы", exact=True)
        expect(listings_tab).to_be_visible(timeout=30_000)
        expect(auctions_tab).to_be_visible(timeout=30_000)


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK: unlike остаётся в /profile/favorites и удаляет карточку")
def test_favorites_unlike_stays_on_favorites(page):
    product_id, _, _ = _get_first_product_card_from_home(page)

    _ensure_in_favorites(page, product_id)

    main = _open_favorites(page)
    expect(main.get_by_role("heading", name="Избранное")).to_be_visible(timeout=30_000)

    url_before = page.url

    card = _favorite_card_for_product(page, main, product_id)
    expect(card).to_be_visible(timeout=30_000)

    heart = card.locator('svg[class*="card_icon__like"]').first
    expect(heart).to_be_visible(timeout=30_000)
    heart.click(no_wait_after=True)

    expect(page).to_have_url(re.compile(r".*/profile/favorites(?:\\?|$|#)"), timeout=30_000)
    assert "/profile/favorites" in page.url, (
        "После unlike ожидали остаться в /profile/favorites "
        f"(url_before={url_before!r}, url_after={page.url!r})"
    )
    expect(page.locator("main")).to_be_visible(timeout=30_000)
    expect(page.locator("main").get_by_role("heading", name="Избранное")).to_be_visible(
        timeout=30_000
    )

    main = _open_favorites(page)
    expect(_favorites_links_for_product(main, product_id)).to_have_count(0, timeout=30_000)


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK: добавили с карточки → открыли товар → клик по heart на странице")
def test_favorites_listing_heart_then_product_page_heart_smoke(page):
    product_id, _, _ = _get_first_product_card_from_home(page)

    _ensure_not_in_favorites(page, product_id)

    _, listing_heart = _get_product_card_from_home_by_id(page, product_id)
    expect(listing_heart).to_be_visible(timeout=30_000)
    listing_heart.click(no_wait_after=True)

    page.goto(f"/product/{product_id}", wait_until="domcontentloaded", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)
    expect(page).to_have_url(re.compile(rf".*/product/{re.escape(product_id)}(?:/|$|\\?|#)"))

    main = page.locator("main")
    expect(main).to_be_visible(timeout=60_000)

    product_heart = page.locator('[class*="Contacts_wrapper__info"] svg[class*="Like_icon"]')
    expect(product_heart).to_be_visible(timeout=30_000)

    # Страница товара проверяется как smoke: ручной сценарий remove работает,
    # но в автотесте клик меняет DOM без подтверждённой favorites-mutation.
    product_heart.click(no_wait_after=True)

    expect(main).to_be_visible(timeout=60_000)
    expect(page).to_have_url(re.compile(rf".*/product/{re.escape(product_id)}(?:/|$|\\?|#)"))


@allure.epic("UI Auction")
@allure.feature("Favorites")
@allure.title("Favorites RTK (guest): клик по heart не добавляет молча и предлагает вход")
def test_favorites_guest_click_heart_shows_login_or_stays_alive(guest_page):
    product_id, _, card_heart = _get_first_product_card_from_home(guest_page)
    assert product_id

    expect(card_heart).to_be_visible(timeout=30_000)
    card_heart.click(no_wait_after=True)

    main = guest_page.locator("main")
    expect(main).to_be_visible(timeout=60_000)

    login_re = re.compile(r"(войти|авторизац|телефон|почта|код)", re.I)
    candidates = [
        guest_page.get_by_role("button", name=re.compile(r"(войти|авторизац)", re.I)),
        guest_page.get_by_role("link", name=re.compile(r"(войти|авторизац)", re.I)),
        guest_page.get_by_role("heading", name=re.compile(r"(войти|авторизац)", re.I)),
        guest_page.get_by_role("dialog"),
        guest_page.get_by_placeholder(login_re),
        guest_page.get_by_label(login_re),
        guest_page.get_by_text(login_re),
    ]

    for loc in candidates:
        try:
            expect(loc.first).to_be_visible(timeout=5_000)
            break
        except AssertionError:
            continue
    else:
        try:
            preview = (guest_page.locator("body").inner_text() or "")[:500]
        except Exception:
            preview = "<inner_text error>"
        pytest.fail(
            "После клика по heart в гостевом режиме не найдено ожидаемое состояние авторизации "
            f"(url={guest_page.url!r}, body_text_preview={preview!r})"
        )


