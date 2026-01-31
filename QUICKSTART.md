# Быстрый старт Node Agent

## Локальный запуск (для тестирования)

### 1. Подготовка

```bash
cd node-agent

# Создай .env файл
cp .env.example .env
```

Отредактируй `.env`:
```env
AGENT_NODE_UUID=твой-uuid-ноды
AGENT_COLLECTOR_URL=http://host.docker.internal:8000
AGENT_AUTH_TOKEN=твой-токен-из-бота
AGENT_XRAY_LOG_PATH=/var/log/remnanode/access.log
```

### 2. Создай тестовый лог (опционально)

```bash
mkdir -p test-logs
cp test-logs/access.log.example test-logs/access.log
# Добавь реальные строки из Xray в test-logs/access.log
```

### 3. Запусти агент

```bash
# Используй локальный compose файл
docker-compose -f docker-compose.local.yml up -d

# Или обычный compose (если логи на хосте)
docker-compose up -d
```

### 4. Проверь работу

```bash
# Логи агента
docker-compose -f docker-compose.local.yml logs -f

# Ожидаемые сообщения:
# INFO: Node Agent started: node_uuid=..., collector=..., interval=30s
# DEBUG: Collected X connections from log
# DEBUG: Batch sent: X connections, response {...}
```

### 5. Остановка

```bash
docker-compose -f docker-compose.local.yml down
```

## Продакшен (на реальной ноде)

### 1. Скопируй агент на сервер

```bash
scp -r node-agent/ user@node-server:/opt/remnawave-node-agent/
```

### 2. Настрой .env

```bash
ssh user@node-server
cd /opt/remnawave-node-agent/node-agent
cp .env.example .env
nano .env  # заполни настройки
```

### 3. Запусти

```bash
docker-compose up -d
docker-compose logs -f
```

## Полезные команды

```bash
# Перезапуск
docker-compose restart

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f

# Пересборка образа
docker-compose build --no-cache
docker-compose up -d
```
