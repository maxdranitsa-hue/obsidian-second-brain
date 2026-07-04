---
name: second-brain-setup
description: "Переезд второго мозга на VPS: клон личного репо участника, перенос .env, systemd-бот 24/7 + синхра vault в GitHub"
disable-model-invocation: true
argument-hint: "IP сервера, root-пароль, URL приватного репо участника"
---

Ты помогаешь **не-технарю** перенести его второй мозг с ноутбука на VPS. Веди по шагам, тепло и просто.
**Команды выполняй сам.** У человека спрашивай только данные и подтверждения — по одному. После каждого шага коротко скажи, что сделал и что дальше. Если шаг падает — объясни простыми словами и не иди дальше, пока не пройдёт.

## Входные данные
$ARGUMENTS

Ожидаешь три вещи (спроси, чего не хватает):
- **IP сервера** (свежий дроплет DigitalOcean, Ubuntu 22.04)
- **root-пароль** (из письма DO / из UI при создании)
- **URL приватного репо участника** (создан на прошлом шаге, вида `git@github.com:USERNAME/second-brain.git` или `https://github.com/USERNAME/second-brain`)

Скилл запускается **на Mac участника**, в папке его локального проекта дня 1 — поэтому у тебя есть доступ к его локальному `.env` и данным. Это важно: `.env` переносим именно отсюда.

---

# Переезд второго мозга на VPS

**Итог:** бот работает 24/7 на сервере · vault выгружается в приватный GitHub каждые 30 мин · Obsidian на Mac показывает заметки. Ровно архитектура «мозг в трёх местах».

---

## Шаг 1. Беспарольный доступ к серверу (root)

Убедись, что у Mac есть SSH-ключ (если нет — создай):
```bash
[ -f ~/.ssh/id_ed25519.pub ] || ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519
```

Залей публичный ключ Mac на сервер, используя root-пароль (через askpass, без sshpass):
```bash
ASK=$(mktemp); printf '#!/bin/bash\necho "%s"\n' "$ROOT_PASSWORD" > "$ASK"; chmod +x "$ASK"
SSH_ASKPASS="$ASK" SSH_ASKPASS_REQUIRE=force DISPLAY=:0 \
  ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no root@$IP \
  "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys" < ~/.ssh/id_ed25519.pub
rm -f "$ASK"
```
Проверь, что дальше root заходит **без пароля**:
```bash
ssh -o StrictHostKeyChecking=no root@$IP 'echo OK'   # → OK
```
Дальше все команды на сервере — через `ssh root@$IP '...'`.

---

## Шаг 2. Базовая безопасность

```bash
ssh root@$IP 'bash -s' <<'EOF'
apt update
adduser --disabled-password --gecos "" deploy 2>/dev/null || true
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh && cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys
echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deploy && chmod 440 /etc/sudoers.d/deploy
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
EOF
```
> Не отключай root-логин до конца настройки.

---

## Шаг 3. Стек

```bash
ssh root@$IP 'bash -s' <<'EOF'
apt install -y build-essential python3.12 python3.12-venv python3.12-dev
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt install -y nodejs
sudo -iu deploy bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
npm install -g @anthropic-ai/claude-code
EOF
ssh root@$IP 'node -v; claude --version; sudo -iu deploy /home/deploy/.local/bin/uv --version'
```

---

## Шаг 4. Deploy-ключ сервера → в репо участника

Генерируем на сервере ключ и настраиваем git для github:
```bash
ssh root@$IP 'sudo -iu deploy bash -s' <<'EOF'
[ -f ~/.ssh/github ] || ssh-keygen -t ed25519 -C 'second-brain-deploy' -f ~/.ssh/github -N ''
cat > ~/.ssh/config <<CFG
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github
  StrictHostKeyChecking no
CFG
chmod 600 ~/.ssh/config
echo "=== ПУБЛИЧНЫЙ КЛЮЧ (добавь в репо) ==="
cat ~/.ssh/github.pub
EOF
```
Возьми выведенный ключ и добавь его участнику в репо:
**GitHub → его репозиторий → Settings → Deploy keys → Add deploy key → вставить → ✅ Allow write access.**
Спроси участника подтверждение, что добавил, прежде чем идти дальше. Проверь:
```bash
ssh root@$IP 'sudo -iu deploy ssh -o StrictHostKeyChecking=no -T git@github.com'  # → "Hi USERNAME! ..."
```

---

## Шаг 5. Клон ЕГО репо (с его данными дня 1)

```bash
ssh root@$IP "sudo -iu deploy git clone $REPO_SSH_URL /home/deploy/agent-second-brain"
```
> `$REPO_SSH_URL` — обязательно `git@github.com:USERNAME/second-brain.git` (SSH, не https), чтобы работал deploy-ключ.
> В репо уже лежат about.md, goals, MEMORY и заметки — личность мозга переезжает вместе с ними.

---

## Шаг 6. Перенос `.env` с Mac на сервер

`.env` в git не коммитится (токены) — копируем из локальной папки участника:
```bash
scp ./.env deploy@$IP:/home/deploy/agent-second-brain/.env
ssh root@$IP 'chown deploy:deploy /home/deploy/agent-second-brain/.env && chmod 600 /home/deploy/agent-second-brain/.env'
```
Если локального `.env` нет (день 1 не заполняли) — собери 4 ключа заново по одному (Telegram Bot Token, Telegram ID, Deepgram, Todoist) и запиши в `.env` на сервере в формате:
```
TELEGRAM_BOT_TOKEN=...
DEEPGRAM_API_KEY=...
TODOIST_API_KEY=...
VAULT_PATH=./vault
ALLOWED_USER_IDS=[...]
```

---

## Шаг 7. Зависимости + авторизация Claude на сервере

```bash
ssh root@$IP 'sudo -iu deploy bash -c "cd ~/agent-second-brain && ~/.local/bin/uv sync"'
```
Авторизуй Claude CLI под `deploy` (нужно для daily-обработки) — долгоживущим токеном:
```bash
ssh -t root@$IP 'sudo -iu deploy claude setup-token'
```
Пройди вход в браузере, скопируй токен `sk-ant-oat01-…` и пропиши его в systemd drop-in:
```bash
ssh root@$IP "mkdir -p /etc/systemd/system/second-brain.service.d && \
cat > /etc/systemd/system/second-brain.service.d/claude-token.conf <<'CONF'
[Service]
Environment=CLAUDE_CODE_OAUTH_TOKEN=ВСТАВЬ_ТОКЕН
CONF
chmod 600 /etc/systemd/system/second-brain.service.d/claude-token.conf"
```

---

## Шаг 8. systemd: бот 24/7 + синхра vault каждые 30 мин

```bash
ssh root@$IP 'bash -s' <<'EOF'
# --- бот ---
cat > /etc/systemd/system/second-brain.service <<'SVC'
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
SVC

# --- синхра vault → GitHub (использует scripts/git-sync.sh из репо) ---
chmod +x /home/deploy/agent-second-brain/scripts/git-sync.sh
cat > /etc/systemd/system/vault-sync.service <<'SVC'
[Unit]
Description=Vault Git Sync

[Service]
Type=oneshot
User=deploy
Environment=HOME=/home/deploy
ExecStart=/home/deploy/agent-second-brain/scripts/git-sync.sh
SVC
cat > /etc/systemd/system/vault-sync.timer <<'TMR'
[Unit]
Description=Vault sync every 30 min

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min

[Install]
WantedBy=timers.target
TMR

# на сервере тоже задать git-идентичность, чтобы коммиты синхры не падали
sudo -iu deploy bash -c 'cd ~/agent-second-brain && git config user.email "bot@second-brain" && git config user.name "second-brain"'

systemctl daemon-reload
systemctl enable --now second-brain.service
systemctl enable --now vault-sync.timer
systemctl is-active second-brain.service
EOF
```

---

## Шаг 9. Проверка

1. Участник пишет своему боту в Telegram голосовое или текст → бот отвечает **с сервера**.
2. Логи, если тишина: `ssh root@$IP 'journalctl -u second-brain -n 40 --no-pager'`
3. Проверь синхру: `ssh root@$IP 'sudo -iu deploy /home/deploy/agent-second-brain/scripts/git-sync.sh'` → должен запушить.

---

## Шаг 10. Выключаем локального бота

Чтобы не было двух ботов на одном токене (конфликт polling):
```bash
launchctl unload ~/Library/LaunchAgents/*second-brain*.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/*voicememos*.plist 2>/dev/null || true
```
Если бот дня 1 крутился просто в терминале — попроси участника закрыть то окно (Ctrl+C).

---

## Шаг 11. Mac становится окном (Obsidian)

Локальная папка участника уже указывает на его репо — просто обновляем:
```bash
git pull
```
Открой Obsidian → **Open folder as vault** → папка `vault/`. Теперь: пишешь боту с телефона → сервер сохраняет → через 30 мин `git pull` → заметка в Obsidian.

---

## Готово

У участника: бот в облаке 24/7 · приватный GitHub-хаб · Obsidian на Mac. Ноут можно закрыть.

## Частые затыки
- **root просит пароль после Шага 1** → ключ не залился; повтори Шаг 1, проверь `PubkeyAuthentication=no` в первой команде.
- **`git clone` Permission denied** → deploy-ключ не добавлен в репо или без write access (Шаг 4).
- **Бот отвечает дважды** → локальный не выключен (Шаг 10).
- **`second-brain.service` inactive** → `journalctl -u second-brain -n 50`; чаще всего пустой `.env` или не прошёл `uv sync`.
- **daily-обработка не идёт / 401** → протух токен Claude; повтори Шаг 7 (`claude setup-token`) и обнови drop-in.
