## SKIPPED тесты (анализ)

- `tests/test_auction.py` → Это не аукцион (/product/) — сценарий ставок пропускается.
- `tests/test_auth_registration.py` → Нужен реальный код из письма; экран «Персональные данные» после него здесь не проверяем.
- `tests/test_favorites.py` → В избранном есть объявления — пустое состояние не проверяем.
- `tests/test_my_bids.py` → Нет ссылок на лоты в списке ставок.
- `tests/test_negative.py` → Кнопка «Войти» недоступна (часто при активной сессии из auth/state.json).
- `tests/test_notifications.py` → Нет уведомлений со ссылкой на товар или аукцион.
- `tests/test_profile_settings.py` → Поля профиля на стенде только для просмотра.
- `tests/test_profile_settings.py` → Нет редактируемых полей.
- `tests/test_profile_settings.py` → Поле e-mail только для просмотра.
- `tests/test_search_filters.py` → Нет пункта категории «Животные» в ожидаемой позиции списка (стенд/верстка).
- `tests/test_search_filters.py` → Нет кнопок переключения Объявления/Аукционы на выдаче.
- `tests/test_search_filters.py` → При заведомо пустом запросе на стенде остаются карточки без явного текста о пустой выдаче.
