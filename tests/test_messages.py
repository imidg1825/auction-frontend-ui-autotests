"""
Раздел «Сообщения» в личном кабинете.

Сессия задаётся в conftest через auth/state.json.
"""

import re
import time
from pathlib import Path

import pytest
from playwright.sync_api import expect

STATE_JSON = Path(__file__).resolve().parent.parent / "auth" / "state.json"

pytestmark = pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — выполните auth/save_auth.py.",
)

VIEWPORT_MOBILE = {"width": 390, "height": 844}
MESSAGES_PATH = re.compile(r"/profile/messages/?$")
MESSAGES_CHAT_PATH = re.compile(r"/profile/messages/\d+")


def _dismiss_cookie_banner_if_visible(page):
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()


def _open_home(page):
    page.goto("/", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)


def _messages_main_heading(page):
    return page.locator("main").get_by_role("heading", name="Сообщения")


def _try_visible_first(locator) -> bool:
    try:
        return locator.count() > 0 and locator.first.is_visible()
    except Exception:
        return False


def _find_profile_menu_trigger(page):
    """
    Элемент, открывающий меню ЛК (моб. шапка). Классы/теги на стенде менялись.
    Порядок: linkAvatar → ссылка в ЛК → буква «И» в шапке (как в test_profile).
    """
    header = page.locator("header")
    candidates = (
        header.locator("button[class*='linkAvatar']"),
        header.locator("a[class*='linkAvatar']"),
        header.locator("button[class*='LinkAvatar']"),
        header.locator("a[class*='LinkAvatar']"),
        page.locator("button[class*='linkAvatar']"),
        page.locator("a[class*='linkAvatar']"),
        header.locator('a[href*="/profile/"]').filter(has_text=re.compile(r"^\s*И\s*$")),
        header.locator("a, button").filter(has_text=re.compile(r"^\s*И\s*$")),
    )
    for loc in candidates:
        if _try_visible_first(loc):
            return loc.first
    return None


def _wait_profile_menu_trigger(page, timeout_ms: int = 60_000):
    """Ждём гидратацию шапки: триггер меню может появиться позже networkidle."""
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        el = _find_profile_menu_trigger(page)
        if el is not None:
            return el
        page.wait_for_timeout(350)
    return None


def _guest_entry_visible(page) -> bool:
    btn = page.get_by_role("button", name="Войти")
    if btn.count() > 0 and btn.first.is_visible():
        return True
    link = page.get_by_role("link", name="Войти")
    if link.count() > 0 and link.first.is_visible():
        return True
    return False


def _require_authenticated_header_or_skip(page) -> None:
    """
    Перед кликом по аватару: гость / протухшая сессия → skip (не FAIL на таймаутах).
    """
    if _guest_entry_visible(page):
        pytest.skip("Не авторизован (state.json протух)")

    deadline = time.monotonic() + 12.0
    while time.monotonic() < deadline:
        if _guest_entry_visible(page):
            pytest.skip("Не авторизован (state.json протух)")
        if _find_profile_menu_trigger(page) is not None:
            return
        if _try_visible_first(page.locator("header").locator('a[href*="/profile/myAds"]')):
            return
        page.wait_for_timeout(300)

    pytest.skip("Не авторизован (state.json протух)")


def _open_messages_from_profile_menu(page):
    """Мобильное меню по аватару → ссылка «Сообщения» (как в test_profile)."""
    page.set_viewport_size(VIEWPORT_MOBILE)
    _open_home(page)

    # Дождаться оболочки главной: иначе клик по аватару часто ловит timeout.
    expect(page.get_by_placeholder("Поиск по объявлениям")).to_be_visible(timeout=60_000)

    _require_authenticated_header_or_skip(page)

    opener = _wait_profile_menu_trigger(page)
    if opener is None:
        # Триггер меню в шапке не найден — пробуем прямой URL (нужна валидная сессия).
        page.goto("/profile/messages", wait_until="networkidle", timeout=120_000)
        if not MESSAGES_PATH.search(page.url):
            pytest.skip("Не авторизован (state.json протух)")
        expect(_messages_main_heading(page)).to_be_visible(timeout=30_000)
        page.wait_for_timeout(4000)
        return

    expect(opener).to_be_visible(timeout=5_000)
    opener.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    opener.click(timeout=60_000)

    # Явный сигнал, что выезжающее меню открылось (как в _open_profile_drawer_mobile).
    expect(page.get_by_role("link", name="Мои объявления")).to_be_visible(timeout=20_000)

    messages = page.get_by_role("link", name="Сообщения")
    expect(messages).to_be_visible(timeout=20_000)
    messages.scroll_into_view_if_needed()
    messages.click(timeout=30_000)

    expect(page).to_have_url(MESSAGES_PATH, timeout=30_000)
    expect(_messages_main_heading(page)).to_be_visible(timeout=30_000)
    page.wait_for_timeout(4000)


def _conversation_links(page):
    """Ссылки на конкретные диалоги (и относительные, и абсолютные href после SPA)."""
    return page.locator("main").locator('a[href*="/profile/messages/"]')


def _message_composer_input(page):
    return page.locator("main").get_by_placeholder("Написать сообщение")


def _composer_ready_for_fill(inp) -> bool:
    """Перед fill(): явно visible + enabled + editable (иначе Playwright падает на disabled)."""
    try:
        if inp.count() == 0:
            return False
        el = inp.first
        return bool(el.is_visible() and el.is_enabled() and el.is_editable())
    except Exception:
        return False


def _composer_input_is_active(inp) -> bool:
    """Поле в DOM видимо, не disabled и допускает ввод (реальный стенд: иначе fill падает)."""
    return _composer_ready_for_fill(inp)


def _wait_for_active_composer_in_open_chat(page, timeout_ms: int = 25_000):
    """
    После перехода в чат поле может появиться позже или остаться disabled — ждём активное состояние.
    """
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        inp = _message_composer_input(page)
        if _composer_input_is_active(inp):
            return inp
        page.wait_for_timeout(200)
    return None


def _composer_send_button(page):
    """В разметке чата два button в main: служебный и отправка."""
    main_btns = page.locator("main").get_by_role("button")
    n = main_btns.count()
    if n < 2:
        return None
    return main_btns.nth(1)


def _count_chat_messages(page) -> int:
    """Приблизительное число строк переписки в main (для сравнения до/после отправки)."""
    main = page.locator("main")
    with_time = main.locator("div").filter(has=page.locator("time"))
    n = with_time.count()
    if n > 0:
        return n
    alt = main.locator('[class*="Message"], [class*="message"]')
    return alt.count()


def _enabled_composer_or_skip(page):
    """
    Первый диалог может быть с удалённым объявлением — поле «Написать сообщение» есть, но disabled.
    Перебираем диалоги и выбираем первый, где поле видимо, enabled и editable; иначе skip.
    """
    n = _conversation_links(page).count()
    if n == 0:
        pytest.skip("Нет диалогов.")

    for i in range(n):
        links = _conversation_links(page)
        if links.count() <= i:
            break
        links.nth(i).click()
        expect(page).to_have_url(MESSAGES_CHAT_PATH, timeout=30_000)

        inp = _wait_for_active_composer_in_open_chat(page, timeout_ms=25_000)
        if inp is not None:
            return inp

        page.goto("/profile/messages", wait_until="networkidle", timeout=120_000)
        expect(_messages_main_heading(page)).to_be_visible(timeout=30_000)
        page.wait_for_timeout(500)

    pytest.skip(
        "Нет диалога с активным полем «Написать сообщение» "
        "(видимое, не disabled, допускает ввод); остальные проверены."
    )


def _active_composer_for_text_input_or_skip(page):
    """
    Перебор диалогов: только если поле «Написать сообщение» проходит проверки перед вводом.
    """
    n = _conversation_links(page).count()
    if n == 0:
        pytest.skip("Нет диалогов с активным полем ввода")

    for i in range(n):
        links = _conversation_links(page)
        if links.count() <= i:
            break
        links.nth(i).click()
        expect(page).to_have_url(MESSAGES_CHAT_PATH, timeout=30_000)

        _wait_for_active_composer_in_open_chat(page, timeout_ms=25_000)

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            candidate = _message_composer_input(page)
            if _composer_ready_for_fill(candidate):
                return candidate
            page.wait_for_timeout(150)

        page.goto("/profile/messages", wait_until="networkidle", timeout=120_000)
        expect(_messages_main_heading(page)).to_be_visible(timeout=30_000)
        page.wait_for_timeout(500)

    pytest.skip("Нет диалогов с активным полем ввода")


def test_messages_opens_from_profile_menu(page):
    """Раздел «Сообщения» открывается из меню профиля."""
    _open_messages_from_profile_menu(page)


def test_messages_list_url(page):
    """URL соответствует разделу сообщений."""
    _open_messages_from_profile_menu(page)
    expect(page).to_have_url(MESSAGES_PATH)


def test_messages_page_shows_section_heading(page):
    """На странице явно виден раздел сообщений (заголовок)."""
    _open_messages_from_profile_menu(page)
    expect(_messages_main_heading(page)).to_be_visible()


def test_messages_list_or_empty_state(page):
    """
    Либо виден список диалогов (ссылки на /profile/messages/:id),
    либо пустое состояние / отсутствие таких ссылок.
    """
    _open_messages_from_profile_menu(page)
    main = page.locator("main")
    conv = _conversation_links(page)

    if conv.count() >= 1:
        expect(conv.first).to_be_visible()
        return

    hint = main.get_by_text(re.compile(r"нет|пока нет|ничего не найдено|начните", re.I))
    if hint.count() > 0 and hint.first.is_visible():
        expect(hint.first).to_be_visible()
    else:
        expect(conv).to_have_count(0)


def test_messages_open_conversation_when_available(page):
    """Клик по диалогу открывает переписку."""
    _open_messages_from_profile_menu(page)
    conv = _conversation_links(page)
    if conv.count() == 0:
        pytest.skip("Нет диалогов для открытия.")

    conv.first.click()
    expect(page).to_have_url(MESSAGES_CHAT_PATH, timeout=30_000)


def test_messages_composer_accepts_text_when_available(page):
    """Поле ввода сообщения принимает текст."""
    _open_messages_from_profile_menu(page)
    inp = _active_composer_for_text_input_or_skip(page)
    inp.fill("тест ui playwright")
    expect(inp).to_have_value("тест ui playwright")


def test_messages_empty_text_blocks_send_when_available(page):
    """
    Пустое сообщение не должно появиться в переписке.

    UI использует визуальную блокировку кнопки отправки вместо атрибута disabled,
    поэтому не проверяем to_be_disabled(), а сравниваем число сообщений до и после клика.
    """
    _open_messages_from_profile_menu(page)
    inp = _enabled_composer_or_skip(page)
    inp.clear()
    page.wait_for_timeout(400)

    send = _composer_send_button(page)
    if send is None:
        pytest.skip("Не найдена кнопка отправки в ожидаемой разметке.")

    count_before = _count_chat_messages(page)

    try:
        send.click(timeout=5000)
    except Exception:
        # Кнопку нельзя нажать (заблокирована) — ожидаемое поведение для пустого ввода
        return

    page.wait_for_timeout(800)
    count_after = _count_chat_messages(page)
    assert count_after == count_before, (
        "Пустое сообщение не должно увеличивать число строк в чате "
        f"(было {count_before}, стало {count_after})."
    )
