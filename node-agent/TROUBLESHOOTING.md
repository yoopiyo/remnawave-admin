# Устранение проблем Node Agent

## Агент запустился, но ничего не происходит

### 1. Проверь уровень логирования

В `.env` установи:
```env
AGENT_LOG_LEVEL=DEBUG
```

Перезапусти агент и проверь логи:
```bash
docker-compose logs -f
```

### 2. Проверь наличие файла логов

```bash
# В контейнере
docker-compose exec node-agent ls -la /var/log/remnanode/

# На хосте
ls -la /var/log/remnanode/access.log
```

### 3. Проверь формат логов

Агент ищет строки с `accepted` в формате:
```
2026/01/28 12:00:00 [Info] app/proxyman/inbound: [user@email] 1.2.3.4:12345 accepted tcp:example.com:443
```

Проверь последние строки лога:
```bash
tail -n 20 /var/log/remnanode/access.log
```

### 4. Проверь права доступа

Агент должен иметь права на чтение файла:
```bash
# Проверь права
ls -la /var/log/remnanode/access.log

# Если нужно, дай права
sudo chmod 644 /var/log/remnanode/access.log
```

### 5. Проверь подключение к Collector API

Проверь, что агент может достучаться до Admin Bot:
```bash
# Из контейнера
docker-compose exec node-agent curl -v https://adminbot.stijoin.com/api/v1/connections/health

# Или с токеном
docker-compose exec node-agent curl -v \
  -H "Authorization: Bearer YOUR_TOKEN" \
  https://adminbot.stijoin.com/api/v1/connections/batch
```

### 6. Проверь логи агента

Ожидаемые сообщения при работе:
```
INFO: Node Agent started: node_uuid=..., collector=..., interval=30s
INFO: Log file found: /var/log/remnanode/access.log (size: X bytes)
DEBUG: Cycle #1: collecting connections...
INFO: Log parsing: total_lines=X accepted_lines=X matched_lines=X connections=X
INFO: Cycle #1: collected X connections, sending batch...
INFO: Batch sent successfully: X connections, response: {...}
```

Если видишь только:
```
INFO: Node Agent started: ...
```

И больше ничего — значит:
- Либо файл логов пустой
- Либо в логах нет строк с `accepted`
- Либо формат логов не совпадает с ожидаемым

### 7. Проверь формат логов Xray

Агент использует регулярное выражение для формата Remnawave:
```regex
(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+from\s+(\d+\.\d+\.\d+\.\d+):(\d+)\s+accepted.*?email:\s*(\d+)
```

Примеры правильных строк (формат Remnawave):
- ✅ `2026/01/28 11:23:18.306521 from 188.170.87.33:20129 accepted tcp:accounts.google.com:443 [Sweden1 >> DIRECT] email: 154`
- ✅ `2026/01/28 11:24:32.944484 from 178.34.158.124:5732 accepted tcp:31.13.72.53:443 [Sweden1 >> DIRECT] email: 12`

**Важно:** В логах Remnawave указан ID пользователя (`email: 154`), а не email. Collector API автоматически ищет пользователя по:
1. `short_uuid` (если ID совпадает)
2. Email (если формат обычный)
3. ID из `raw_data` (поля `id`, `userId`, `user_id`)

Если формат логов другой, нужно обновить регулярное выражение в `src/collectors/xray_log.py`.

### 8. Тестовый запуск с примером лога

Создай тестовый лог:
```bash
mkdir -p test-logs
cat > test-logs/access.log << 'EOF'
2026/01/28 12:00:00 [Info] app/proxyman/inbound: [test@example.com] 192.168.1.100:54321 accepted tcp:example.com:443
2026/01/28 12:00:05 [Info] app/proxyman/inbound: [test2@example.com] 10.0.0.50:12345 accepted tcp:google.com:443
EOF
```

В `docker-compose.yml` закомментируй реальный лог и раскомментируй тестовый:
```yaml
volumes:
  # - /var/log/remnanode:/var/log/remnanode:ro
  - ./test-logs:/var/log/remnanode:ro
```

Перезапусти и проверь логи.

## Ошибки отправки данных

### "Invalid token" или 403

1. Проверь, что токен правильный (без пробелов, полностью скопирован)
2. Проверь, что токен не был отозван в Admin Bot
3. Проверь, что `AGENT_NODE_UUID` соответствует ноде, для которой выдан токен

### "Connection refused" или таймаут

1. Проверь `AGENT_COLLECTOR_URL` — должен быть доступен с ноды
2. Проверь сеть Docker (если используешь `remnawave-network`)
3. Для локального теста используй `http://host.docker.internal:8000`

### "User not found"

Агент находит подключения, но пользователи не найдены в БД:
- Убедись, что синхронизация пользователей работает в Admin Bot
- Проверь, что email в логах Xray совпадает с email в БД

## Полезные команды

```bash
# Просмотр логов в реальном времени
docker-compose logs -f

# Перезапуск агента
docker-compose restart

# Проверка конфигурации
docker-compose config

# Вход в контейнер
docker-compose exec node-agent sh

# Проверка файла логов из контейнера
docker-compose exec node-agent cat /var/log/remnanode/access.log | tail -20
```
