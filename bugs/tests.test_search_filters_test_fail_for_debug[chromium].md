# test_fail_for_debug[chromium]

## Источник
- Тест: tests.test_search_filters::test_fail_for_debug[chromium]

## Шаги воспроизведения
1. Запустить соответствующий тест
2. Дождаться падения
3. Сверить фактическое поведение

## Ожидаемый результат
Сценарий должен выполняться без ошибки.

## Фактический результат
Тест упал.

## Сообщение об ошибке
```text
AssertionError: Тестовое падение для проверки автоскрина и баг-репорта
assert False

page = <Page url='https://front.test.kp.ktsf.ru/'>

    def test_fail_for_debug(page):
        page.goto("/")
>       assert False, "Тестовое падение для проверки автоскрина и баг-репорта"
E       AssertionError: Тестовое падение для проверки автоскрина и баг-репорта
E       assert False

tests\test_search_filters.py:299: AssertionError
```
## Скриншот
`screenshots/tests_test_search_filters.py_test_fail_for_debug[chromium].png`
## Окружение
- Стенд: https://front.test.kp.ktsf.ru/
- Браузер: Chromium
- Источник: автогенерация из pytest junit.xml

## Примечание
Черновик создан автоматически после failed-прогона.
