---
name: second-brain-setup
description: "Полная установка Agent Second Brain: VPS, бот, Obsidian, все интеграции"
disable-model-invocation: true
argument-hint: "IP сервера и путь к SSH ключу"
---

Ты помогаешь установить систему Agent Second Brain на VPS с нуля.

## Входные данные
$ARGUMENTS

---

# Agent Second Brain — Полная установка

## Что будет установлено
- Ubuntu VPS с базовой безопасностью
- Python 3.12, Node.js 20, UV, Claude Code CLI
- Telegram-бот который принимает голосовые/текст/фото
- Obsidian vault на сервере (база знаний)
- Интеграции: Deepgram (расшифровка голоса), Todoist (задачи)
- Автозапуск через systemd
- Локальный просмотр через Git + Obsidian на Mac

---

## Шаг 0. Подготовка на Mac

### SSH ключ для сервера
```bash
ssh-keygen -t ed25519 -f ~/.ssh/obsidianssh
# Введи passphrase или оставь пустым
pbcopy < ~/.ssh/obsidianssh.pub
```
Публичный ключ скопирован — добавь его в DigitalOcean при создании Droplet.

### Создание Droplet на DigitalOcean
- Ubuntu 22.04 LTS
- Basic → Regular → $6/мес (1 vCPU, 1GB RAM)
- Регион: Frankfurt или Amsterdam
- Authentication: SSH Key (вставь скопированный ключ)
- Hostname: second-brain

---

## Шаг 1. Подключение к серверу

```bash
# Добавь ключ в агент (если задавал passphrase)
ssh-add ~/.ssh/obsidianssh

# Подключись
ssh -i ~/.ssh/obsidianssh root@YOUR_SERVER_IP
```

---

## Шаг 2. Базовая настройка сервера

Выполни на сервере:

```bash
# Обновление системы
apt update && apt upgrade -y

# Создание пользователя deploy
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy

# Копирование SSH ключа для deploy
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# NOPASSWD для deploy (важно — до отключения root!)
echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deploy
chmod 440 /etc/sudoers.d/deploy

# Firewall
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable
```

> ⚠️ Не отключай root-логин до завершения всей настройки

---

## Шаг 3. Установка стека разработки

```bash
# build-essential + Python 3.12
apt install -y build-essential python3.12 python3.12-venv python3.12-dev

# Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# UV (менеджер Python-пакетов)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Claude Code CLI
npm install -g @anthropic-ai/claude-code
```

### Проверка
```bash
python3.12 --version   # Python 3.12.x
node --version         # v20.x.x
~/.local/bin/uv --version
claude --version
```

---

## Шаг 4. Получи 4 API ключа

| Сервис | Где взять | Зачем |
|--------|-----------|-------|
| Telegram Bot Token | @BotFather → /newbot | Бот в Telegram |
| Твой Telegram ID | @userinfobot | Доступ к боту |
| Deepgram API Key | console.deepgram.com | Расшифровка голоса |
| Todoist API Token | Todoist → Settings → Integrations → Developer | Управление задачами |

---

## Шаг 5. Создай приватный репозиторий на GitHub

1. github.com → **+** → **New repository**
2. Название: `second-brain`
3. Тип: **Private**
4. Нажми **Create repository**

---

## Шаг 6. SSH ключ для GitHub на сервере

```bash
# Генерация ключа
ssh-keygen -t ed25519 -C 'github-second-brain' -f ~/.ssh/github -N ''
cat ~/.ssh/github.pub

# Настройка SSH config
cat > ~/.ssh/config << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github
EOF
chmod 600 ~/.ssh/config

# Тест подключения
ssh -o StrictHostKeyChecking=no -T git@github.com
```

Добавь публичный ключ в GitHub:
→ Репозиторий → **Settings** → **Deploy keys** → **Add deploy key**
→ Поставь галочку **Allow write access**

---

## Шаг 7. Клонирование и настройка проекта

```bash
cd /root
git clone https://github.com/maxdranitsa-hue/agent-second-brain
cd agent-second-brain

# Меняем remote на свой приватный репозиторий
git remote set-url origin git@github.com:YOUR_GITHUB_USERNAME/second-brain.git
```

---

## Шаг 8. Заполни личные файлы

### .env
```bash
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН
DEEPGRAM_API_KEY=ВАШ_КЛЮЧ
TODOIST_API_KEY=ВАШ_КЛЮЧ
VAULT_PATH=./vault
ALLOWED_USER_IDS=[ВАШ_TELEGRAM_ID]
EOF
```

### О себе — `vault/.claude/skills/dbrain-processor/references/about.md`
Заполни:
- Имя, возраст, роль, компания
- Чем занимаешься
- Команда
- Часовой пояс и рабочие часы
- Ключевые клиенты/проекты

### Классификация — `vault/.claude/skills/dbrain-processor/references/classification.md`
Настрой под свои рабочие домены:
- Типы задач (продажи, проекты, операционка и т.д.)
- Ключевые слова для каждого типа
- Куда сохранять (Todoist, ideas, learnings и т.д.)

### Цели — `vault/goals/`
- `0-vision-3y.md` — видение на 3 года
- `1-yearly-YYYY.md` — цели на год
- `2-monthly.md` — фокус на месяц
- `3-weekly.md` — фокус на неделю

---

## Шаг 9. Установка зависимостей

```bash
cd /root/agent-second-brain
~/.local/bin/uv sync
```

---

## Шаг 10. Первый коммит в свой репозиторий

```bash
git config user.email "your@email.com"
git config user.name "Your Name"
git add -A
git commit -m "Personal setup"
git push origin main
```

---

## Шаг 11. Systemd сервис

```bash
# Создаём пользователя deploy с проектом
cp -r /root/agent-second-brain /home/deploy/agent-second-brain
cp -r /root/.local /home/deploy/.local
chown -R deploy:deploy /home/deploy/agent-second-brain
chown -R deploy:deploy /home/deploy/.local

# Создаём systemd service
cat > /etc/systemd/system/second-brain.service << 'EOF'
[Unit]
Description=Second Brain Telegram Bot
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/agent-second-brain
ExecStart=/home/deploy/.local/bin/uv run python -m d_brain
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=HOME=/home/deploy
EnvironmentFile=/home/deploy/agent-second-brain/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable second-brain
systemctl start second-brain
systemctl status second-brain
```

---

## Шаг 12. Авторизация Claude Code

**Критически важно!** Бот использует Claude CLI — его нужно авторизовать от имени deploy:

```bash
# На своём Mac подключись как deploy
ssh -i ~/.ssh/obsidianssh deploy@YOUR_SERVER_IP

# Авторизуй Claude
claude /login
```

Пройди авторизацию через браузер. После этого перезапусти сервис:
```bash
# Из root SSH сессии
systemctl restart second-brain
```

---

## Шаг 13. Obsidian на Mac

```bash
# Клонируй vault локально
git clone https://github.com/YOUR_USERNAME/second-brain.git ~/second-brain
```

1. Установи Obsidian с obsidian.md
2. **Open folder as vault** → выбери `~/second-brain/vault`

### Обновление vault
```bash
cd ~/second-brain && git pull
```

---

## Проверка работы

1. Напиши боту любое сообщение → должен ответить "Сохранено"
2. Отправь голосовое → должен расшифровать и сохранить
3. Нажми `/process` → Claude обработает и ответит отчётом

---

## Ежедневное использование

| Действие | Что делать |
|----------|-----------|
| Задача с дедлайном | Голосовое/текст боту → уйдёт в Todoist |
| Идея | Текст боту → сохранится в thoughts/ideas/ |
| После встречи | Голосовое → CRM-карточка клиента |
| Обработка за день | /process → отчёт + задачи |
| Обновить Obsidian на Mac | cd ~/second-brain && git pull |
