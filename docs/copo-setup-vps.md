# Setup para copo — Claude Code + bot de Telegram en la VPS compartida

Todo esto se ejecuta con tu propio usuario `copo` por SSH a la VPS. No necesitas sudo para
ninguno de estos pasos.

```
ssh copo@167.235.58.235
```

## 1. Node.js sin sudo (nvm)

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install --lts
node -v
```

## 2. Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

## 3. Login con tu propia cuenta/suscripción de Claude

```bash
claude
```

Sigue el flujo de login normal (navegador) con tu propia cuenta — no uses la de diego.

## 4. Traer el proyecto

```bash
git clone git@github.com:gueco99/Bounty_VilIA.git ~/claude-bug-bounty
```

(Es el repo privado del equipo, no el público `shuvonsec/claude-bug-bounty` del que parte el
proyecto — necesitarás que diego te dé acceso al repo en GitHub si no lo tienes ya, y tener tu
clave SSH de GitHub configurada en tu cuenta `copo` de la VPS.)

## 5. Conectar tu memoria a la carpeta compartida

Diego ya te dio acceso (vía ACL, sin sudo) a:
```
/home/diego/claude-bug-bounty/memory-shared/
```
Comprueba que entras y que ves los archivos reales de memoria (no solo `copo/`/`diego/`, que ya
no se usan — todo va a la raíz de esta carpeta):
```bash
ls /home/diego/claude-bug-bounty/memory-shared/
cat /home/diego/claude-bug-bounty/memory-shared/MEMORY.md | head
```

**Importante:** el enlace va en la ruta real donde Claude Code guarda la memoria de este proyecto
(`~/.claude/projects/<hash-de-la-ruta>/memory`), no en el proyecto en sí. Arráncalo primero una
vez para que Claude Code cree esa carpeta sola, luego reemplázala por el enlace:

```bash
cd ~/claude-bug-bounty
claude   # ábrelo y ciérralo (ctrl+c) una vez, solo para que se cree ~/.claude/projects/.../memory

# busca la carpeta que se creó (el nombre depende de la ruta exacta de tu proyecto):
ls ~/.claude/projects/

# sustitúyela por el enlace a la carpeta compartida (ajusta el nombre exacto que veas arriba):
MEMDIR=~/.claude/projects/-home-copo-claude-bug-bounty/memory
rm -rf "$MEMDIR"
ln -s /home/diego/claude-bug-bounty/memory-shared "$MEMDIR"
```

A partir de aquí, todo lo que tu Claude vaya encontrando y todo lo que encuentre el de diego cae
en el mismo sitio — memoria realmente compartida, no solo una carpeta con permisos.

## 6. Bun (dependencia del plugin de Telegram)

Esta VPS no tiene `unzip` y no hay sudo para instalarlo, así que el instalador oficial de Bun
falla — usa la vía npm en su lugar:
```bash
npm install -g bun
bun --version
```

## 7. Plugin oficial de Telegram para Claude Code

```bash
claude plugin marketplace add anthropics/claude-plugins-official
claude plugin install telegram@claude-plugins-official
```

## 8. Crea tu propio bot en Telegram

No reutilices el bot de diego — cada canal va ligado a una sesión/cuenta distinta.

1. Habla con **@BotFather** en Telegram, manda `/newbot`.
2. Dale un nombre y un username que termine en `bot`.
3. Copia el token que te da (formato `123456789:AAxxxxx...`).

## 9. Configura el token

```bash
mkdir -p ~/.claude/channels/telegram
umask 177
printf "TELEGRAM_BOT_TOKEN=%s\n" "TU_TOKEN_AQUI" > ~/.claude/channels/telegram/.env
chmod 600 ~/.claude/channels/telegram/.env
```

## 10. Lánzalo y empareja tu cuenta

```bash
cd ~/claude-bug-bounty
claude --channels plugin:telegram@claude-plugins-official
```
La primera vez te pedirá tema, confirmar que confías en la carpeta, y login (ya deberías estar
logueado del paso 3). Luego:

1. Desde Telegram, escríbele cualquier mensaje a tu bot.
2. Te responde con un código de 6 caracteres.
3. En la sesión de Claude Code, ejecuta:
   ```
   /telegram:access pair <código>
   /telegram:access policy allowlist
   ```
   Esto deja el bot bloqueado solo para tu cuenta de Telegram.

## 11. Déjalo persistente (systemd, sin sudo)

```bash
loginctl enable-linger copo

cat > ~/claude-bug-bounty/telegram-bot-watchdog.sh <<'EOF'
#!/bin/bash
source ~/.nvm/nvm.sh
cd /home/copo/claude-bug-bounty
while true; do
  echo "[$(date)] starting claude --channels telegram"
  claude --channels plugin:telegram@claude-plugins-official --dangerously-skip-permissions
  echo "[$(date)] claude exited, restarting in 5s"
  sleep 5
done
EOF
chmod +x ~/claude-bug-bounty/telegram-bot-watchdog.sh

mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/telegram-bot.service <<EOF
[Unit]
Description=Claude Code Telegram channel watchdog (tmux)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/tmux new-session -d -s telegram-bot /home/copo/claude-bug-bounty/telegram-bot-watchdog.sh
ExecStop=/usr/bin/tmux kill-session -t telegram-bot

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now telegram-bot.service
systemctl --user status telegram-bot.service --no-pager
```

La primera vez que arranque el watchdog te va a pedir otra vez el "confío en esta carpeta" y
aceptar el modo bypass permissions (`--dangerously-skip-permissions`) de forma interactiva —
entra con `tmux attach -t telegram-bot`, acéptalo una vez, y luego `Ctrl+B` `D` para salir sin
matar la sesión. A partir de ahí queda automático y sobrevive a reinicios de la VPS.

**Nota de seguridad:** `--dangerously-skip-permissions` significa que tu bot ejecutará acciones
sin pedirte confirmación, igual que el de diego. Decide tú si quieres ese mismo nivel de
autonomía o prefieres quitar ese flag para revisar cada acción a mano.

## 12. Verifica

Mándale un mensaje a tu bot por Telegram — algo como "¿qué hay en el lead board?" — y confirma
que responde.
