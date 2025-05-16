# Telegram Verification Bot

Telegram-бот на `aiogram 2` и `Python 3.10` для пошаговой верификации клиентов перед покупкой криптовалюты.

## Функции

### Клиент:
- Пройти верификацию (паспорт + селфи);
- Получить реквизиты для оплаты;
- Отправить чек (фото/скрин);
- Отправить видео;
- Получать уведомления на каждом этапе.

### Оператор:
- Видит список всех активных заявок;
- Подтверждает/отклоняет документы, оплату, видео;
- Выдаёт реквизиты из базы или вручную;
- Всё через кнопки (без команд);
- Может отменить заявку с указанием причины.

## Используемые технологии

- Python 3.10
- Aiogram 2
- SQLite3
- FSM (Finite State Machine)
- Reply-кнопки (без inline)
- Локальное хранение медиа (`media/docs`, `media/videos`, `media/payments`)

## Установка

1. Установить зависимости:

```bash
pip install -r requirements.txt
```

2. Создать `config.py`:

```python
BOT_TOKEN = "ваш_токен"
OPERATORS = [123456789]  # ID операторов
```

3. Инициализировать базу данных:

```bash
python database/init.py
```

4. Запустить бота:

```bash
python main.py
```

## Структура проекта

```
├── handlers/
│   ├── user_verification.py
│   ├── operator_documents.py
│   ├── operator_payments.py
│   ├── operator_video.py
│   ├── operator_requisites.py
├── database/
│   ├── db.py
│   └── init.py
├── keyboards/
│   ├── reply_common.py
│   └── reply_operator.py
├── media/
│   ├── docs/
│   ├── payments/
│   └── videos/
├── states/
│   └── verification.py
├── utils/
│   └── media_saver.py
├── config.py
├── main.py
└── requirements.txt
```

## Авторизация

- Оператор определяется по `user_id` в списке `OPERATORS` из `config.py`.
- Для каждого этапа предусмотрены ограничения доступа.

## Лицензия

MIT — используй свободно, адаптируй под свой проект.

---

> Поддержка: Telegram `@kot_teamlead` | GitHub Issues