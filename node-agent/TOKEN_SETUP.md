# Настройка токена агента

## Что такое токен агента?

**Токен агента** — это секретный ключ, который выдаётся в Admin Bot для каждой ноды. Агент использует его для аутентификации при отправке данных в Collector API.

Без токена агент **не сможет** отправлять данные — Collector API отклонит запрос.

## Как получить токен для ноды?

### Вариант 1: Через Admin Bot (Telegram)

В будущем будет команда/кнопка в админ-панели:
- Выбрать ноду → "Сгенерировать токен агента" → скопировать токен

### Вариант 2: Через базу данных (временно)

Пока нет UI, можно сгенерировать токен напрямую в БД:

```sql
-- Сгенерировать токен для ноды (замените YOUR_NODE_UUID)
UPDATE nodes 
SET agent_token = encode(gen_random_bytes(32), 'base64')
WHERE uuid = 'YOUR_NODE_UUID';

-- Посмотреть токен
SELECT uuid, name, agent_token FROM nodes WHERE uuid = 'YOUR_NODE_UUID';
```

### Вариант 3: Через Python утилиту

```python
from src.utils.agent_tokens import generate_agent_token, set_node_agent_token
from src.services.database import DatabaseService

db = DatabaseService()
await db.connect()

token = await set_node_agent_token(db, "YOUR_NODE_UUID")
print(f"Agent token: {token}")
```

## Использование токена

После получения токена, укажите его в `.env` агента:

```env
AGENT_NODE_UUID=your-node-uuid
AGENT_AUTH_TOKEN=your-generated-token-here
AGENT_COLLECTOR_URL=http://localhost:8000
```

## Безопасность

- Токен должен быть **секретным** — не коммитьте его в Git
- Каждая нода имеет **свой уникальный** токен
- Если токен скомпрометирован — отзовите его (установите `NULL` в БД) и сгенерируйте новый
- Токен можно отозвать в любой момент через Admin Bot или SQL

## Отзыв токена

```sql
-- Отозвать токен (агент перестанет работать)
UPDATE nodes SET agent_token = NULL WHERE uuid = 'YOUR_NODE_UUID';
```
