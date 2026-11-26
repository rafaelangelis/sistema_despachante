# Runbook — terminar a instalação em outra máquina

> Siga este arquivo de cima para baixo. Estado atual e decisões pendentes: ops/ESTADO-E-PROXIMOS-PASSOS.md. Referência técnica completa: ops/GUIA-PRODUCAO.md. Especificação original da DOM: ops/especificacao/SISTEMA-DOM.xlsx.

Estado em 25/11/2026: o app está no repositório **público** `rafaelangelis/sistema_despachante` (branch `main`). **Produção ainda não foi instalada**, mas o app já rodou de ponta a ponta num Frappe v15 real em Docker no WSL (site criado, 12 DocTypes, sementes, regras de Cliente/Veículo/O.S., procuração e alertas em simulação testados). Tudo abaixo é a partir do zero na máquina de destino. Para desenvolver/testar no Windows sem VM, veja o **Apêndice — rodar no WSL** no fim deste arquivo.

Decisões já tomadas (não precisa decidir de novo):

| Item | Valor |
|---|---|
| Framework | Frappe v15 |
| Nome do site | `despacho.dom.local` |
| Imagem custom | `dom-erp:1.0.0` |
| Projeto compose | `dom` |
| Portas | 8080 (Frappe), 5678 (n8n), 8081 (Evolution) |
| Papéis | `Despachante`, `Atendente` |
| Alertas | 45/30/15/5 dias, **em modo simulação** até validar |

O que você precisa ter em mãos: acesso SSH à VM no Proxmox, seu login do GitHub (`rafaelangelis`), e o número de WhatsApp que vai enviar as mensagens.

---

## Etapa A — preparar o computador de onde você vai trabalhar

Só precisa de `git` e `gh` se você for mexer no código. Para apenas instalar a VM, pode pular direto para a Etapa B e usar `ssh`.

**Windows (PowerShell, como administrador se puder):**

```powershell
winget install --id Git.Git -e --source winget
winget install --id GitHub.cli -e --source winget
# feche e abra o terminal depois de instalar (PATH)
gh auth login --hostname github.com --git-protocol https --web
git config --global user.name rafaelangelis
git config --global user.email rafaelangelis@users.noreply.github.com
```

Se não tiver `winget` (foi o caso da outra máquina), instale portátil:

```powershell
# gh
$rel = Invoke-RestMethod https://api.github.com/repos/cli/cli/releases/latest
$url = ($rel.assets | Where-Object name -match 'windows_amd64\.zip$').browser_download_url
Invoke-WebRequest $url -OutFile "$env:TEMP\gh.zip"; Expand-Archive "$env:TEMP\gh.zip" "$env:LOCALAPPDATA\gh" -Force
# git (MinGit)
$relg = Invoke-RestMethod https://api.github.com/repos/git-for-windows/git/releases/latest
$urlg = ($relg.assets | Where-Object name -match 'MinGit-.*-64-bit\.zip$').browser_download_url
Invoke-WebRequest $urlg -OutFile "$env:TEMP\mingit.zip"; Expand-Archive "$env:TEMP\mingit.zip" "$env:LOCALAPPDATA\git" -Force
```

**Linux (Debian/Ubuntu) ou macOS:**

```bash
sudo apt update && sudo apt install -y git curl      # macOS: brew install git gh
(command -v gh >/dev/null) || (type -p curl >/dev/null) || sudo apt install curl -y
gh auth login --hostname github.com --git-protocol https --web
```

(Se `gh` não estiver no apt da sua distro, siga <https://github.com/cli/cli#installation>.)

**Clonar o repositório privado:**

```bash
git clone https://github.com/rafaelangelis/sistema_despachante.git
cd sistema_despachante
```

Sem `gh`, use um token fine-grained (`Contents: read` neste repositório):

```bash
git clone https://SEU_TOKEN@github.com/rafaelangelis/sistema_despachante.git
```

---

## Etapa B — preparar a VM de destino (Proxmox)

Requisitos: Debian 12 ou Ubuntu 22.04/24.04, 4 vCPU, 8 GB RAM, 80 GB SSD.

> Antes de começar: tire um **snapshot da VM** no Proxmox. Se algo der errado, você volta em 30 segundos.

```bash
# na VM (via ssh usuario@IP-DA-VM)
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
newgrp docker            # ou saia e entre na sessão de novo
docker --version && docker compose version
```

Portas que precisam estar acessíveis na LAN: 8080, 5678, 8081 (nenhuma exposta para a internet).

---

## Etapa C — gerar a imagem com o app embutido

> **O repositório é PÚBLICO desde 25/11/2026.** Use o caminho **C2** (o de baixo): sem token, sem credencial. O caminho C1 fica aqui só como fallback, caso um dia o repositório volte a ser privado.

**C1 (fallback, só se o repositório voltar a ser privado) token só no build, fora do git:**

```bash
cd ~
gh auth login --hostname github.com --git-protocol https --web   # se ainda não fez nesta máquina
git clone https://github.com/rafaelangelis/sistema_despachante.git
git clone https://github.com/frappe/frappe_docker.git
cd sistema_despachante

# crie um apps.local.json (NÃO commite) com o token de leitura
cat > ops/apps.local.json <<'JSON'
[
  { "url": "https://SEU_TOKEN@github.com/rafaelangelis/sistema_despachante", "branch": "main" }
]
JSON
# garanta que ele não entra no git
grep -q 'apps.local.json' .gitignore || echo 'ops/apps.local.json' >> .gitignore

APPS_JSON=~/sistema_despachante/ops/apps.local.json \
  ~/sistema_despachante/ops/scripts/build-imagem.sh ~/frappe_docker dom-erp:1.0.0
```

**C2 (padrão hoje) repositório público — sem token:**

```bash
git clone https://github.com/rafaelangelis/sistema_despachante.git
git clone https://github.com/frappe/frappe_docker.git
chmod +x ~/sistema_despachante/ops/scripts/*.sh
~/sistema_despachante/ops/scripts/build-imagem.sh ~/frappe_docker dom-erp:1.0.0
```

O script faz, por baixo:

```bash
cd ~/frappe_docker
docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 \
  --build-arg=PYTHON_VERSION=3.11.9 \
  --build-arg=DEBIAN_BASE=bookworm \
  --secret=id=apps_json,src=$HOME/sistema_despachante/ops/apps.json \
  --tag=dom-erp:1.0.0 \
  --file=images/custom/Containerfile .
```

> **Atenção (mudou no frappe_docker):** o `apps.json` agora vai como **build secret** (`--secret id=apps_json`). O antigo `--build-arg=APPS_JSON_BASE64` é **ignorado sem erro** e a imagem sai só com o `frappe`. O padrão também virou Python 3.14 (Frappe v16); a v15 precisa de Python 3.10–3.12.

**C3 se o build não funcionar com token:** clone o app no host e monte dentro de um container bench de desenvolvimento; nesse caso avise que eu ajusto o `Containerfile`.

Verificação do build:

```bash
docker run --rm --entrypoint ls dom-erp:1.0.0 /home/frappe/frappe-bench/apps
# esperado: frappe  dom_despachante
```

Se `dom_despachante` não estiver lá, o clone falhou dentro do build (token/URL) — o log do `docker build` mostra o erro.

---

## Etapa D — subir a produção e criar o site

```bash
cd ~/frappe_docker
cp example.env .env
cp ~/sistema_despachante/ops/frappe-overrides/compose.dom.yaml overrides/
```

Edite o `.env` (troque o conteúdo por este):

```env
# O compose.yaml sozinho nao tem banco nem redis: os overrides abaixo sao obrigatorios.
# Com COMPOSE_FILE aqui, todo "docker compose --project-name dom ..." ja usa todos eles.
COMPOSE_FILE=compose.yaml:overrides/compose.mariadb.yaml:overrides/compose.redis.yaml:overrides/compose.noproxy.yaml:overrides/compose.dom.yaml
CUSTOM_IMAGE=dom-erp
CUSTOM_TAG=1.0.0
PULL_POLICY=never
# senha do root do MariaDB (o compose.mariadb.yaml usa DB_PASSWORD como MYSQL_ROOT_PASSWORD)
DB_PASSWORD=troque-por-senha-forte
FRAPPE_SITE_NAME_HEADER=despacho.dom.local
HTTP_PUBLISH_PORT=8080
```

```bash
docker compose --project-name dom up -d
docker compose --project-name dom ps          # todos Up, db healthy

docker compose --project-name dom exec backend \
  bench new-site despacho.dom.local \
    --mariadb-user-host-login-scope='%' \
    --admin-password 'SENHA-DO-ADMINISTRATOR' \
    --db-root-username root \
    --db-root-password 'A-MESMA-DO-DB_PASSWORD' \
    --install-app dom_despachante

docker compose --project-name dom exec backend bench use despacho.dom.local
docker compose --project-name dom exec backend bench --site despacho.dom.local enable-scheduler
docker compose --project-name dom exec backend bench --site despacho.dom.local set-config host_name http://despacho.dom.local:8080
docker compose --project-name dom restart backend scheduler queue-short queue-long
```

**Checkpoint 1 — aceite desta etapa:**

```bash
docker compose --project-name dom exec backend bench --site despacho.dom.local list-apps
# esperado: frappe 15.x  e  dom_despachante 0.0.1

docker compose --project-name dom exec backend bench --site despacho.dom.local console <<'PY'
import frappe
print(frappe.get_all("DocType", filters={"module": "Despachante"}, pluck="name"))
PY
# esperado: 12 doctypes (Cliente, Empresa, Veiculo, Servico, Ordem de Servico, ...)
```

Acesse `http://IP-DA-VM:8080` com `Administrator` e a senha definida. Se aparecer o menu **Despachante** com Cliente/Empresa/Veículo/O.S., o app instalou.

---

## Etapa E — WhatsApp (Evolution) + n8n

> Validado de ponta a ponta no WSL em 25/11/2026 (Frappe → n8n 2.49.6 → Evolution v2.3.8), sem celular pareado.

**Rede:** não precisa criar nem editar nada. O `overrides/compose.dom.yaml` da Etapa D já dá ao Frappe a rede `dom-net`, e o `docker-compose.satelites.yml` entra nela como externa. Por isso o **Frappe tem que estar de pé antes** (Etapa D). Se você fez a Etapa D com uma versão antiga do override (sem `networks:`), recopie o arquivo e rode `docker compose --project-name dom down` + `up -d`. O `down` sem `-v` não apaga banco nem site; um `up -d` direto falha com "network dom_default not found".

```bash
cd ~/sistema_despachante/ops
cp .env.exemplo .env && chmod 600 .env
# troque os valores; para gerar chaves: openssl rand -hex 24
# N8N_HOST = IP da VM (ou localhost no WSL)
docker compose -p dom-satelites -f docker-compose.satelites.yml up -d
docker compose -p dom-satelites -f docker-compose.satelites.yml ps     # 4 serviços Up, postgres healthy

# Frappe enxerga os dois pelo nome?
cd ~/frappe_docker
docker compose --project-name dom exec backend curl -s http://n8n:5678/healthz
docker compose --project-name dom exec backend curl -s http://evolution:8080/
cd ~/sistema_despachante/ops
# esperado: {"status":"ok"} e "Welcome to the Evolution API"
```

**Workflow do n8n pela linha de comando** (o JSON tem `id` fixo, então importar de novo substitui em vez de duplicar):

```bash
N="docker compose -p dom-satelites -f docker-compose.satelites.yml"
docker cp n8n/alerta-licenciamento.json dom-satelites-n8n-1:/tmp/wf.json
$N exec n8n n8n import:workflow --input=/tmp/wf.json
$N exec n8n n8n publish:workflow --id=DomAlertaWpp0001      # n8n 2.x: "publish" = ativar
$N restart n8n
```

Na primeira vez que abrir `http://IP-DA-VM:5678`, o n8n pede para criar a conta de dono; o workflow já aparece publicado lá.

**Criar a instância do WhatsApp e parear** (aqui é preciso o celular que vai enviar as mensagens):

```bash
. ./.env
curl -s -X POST http://localhost:8081/instance/create \
  -H "apikey: $EVOLUTION_API_KEY" -H "Content-Type: application/json" \
  -d '{"instanceName":"dom-cristo","qrcode":true,"integration":"WHATSAPP-BAILEYS"}'
```

Para ler o QR, o caminho mais simples é o painel da própria Evolution: **http://IP-DA-VM:8081/manager**. Entre com a `EVOLUTION_API_KEY`, abra a instância `dom-cristo` e leia o QR no celular (WhatsApp → Aparelhos conectados). Confira depois:

```bash
curl -s http://localhost:8081/instance/connectionState/dom-cristo -H "apikey: $EVOLUTION_API_KEY"
# "state":"open" = pareado; "close" = não pareado
```

**Teste da cadeia sem celular** (não envia nada; serve para provar rede, `$env` do n8n e chave da Evolution):

```bash
curl -s -X POST http://localhost:5678/webhook/alerta-dom -H 'Content-Type: application/json' \
  -d '{"cliente":"5500000000000","mensagem":"teste","referencia":"teste"}'
```

| Resposta | Significa |
|---|---|
| erro 500 com `instance does not exist` (no log do n8n) | cadeia OK, falta criar a instância |
| erro 500 com `onWhatsApp` / `Connection Closed` | cadeia OK, instância criada mas **não pareada** |
| erro 401 da Evolution | `EVOLUTION_API_KEY` do n8n difere da Evolution (mesmo `.env`? `up -d` de novo) |
| `getaddrinfo ENOTFOUND evolution` | n8n fora da `dom-net` |
| `access to env vars denied` | faltou `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (já vem no compose) |

O webhook usa `responseMode: lastNode`: o Frappe recebe o resultado **real** do envio, e o histórico do veículo (`alerta_enviado_em`) registra `http_200` só quando a Evolution aceitou a mensagem. Antes ele respondia 200 na hora e o Frappe marcava tudo como enviado.

---

## Etapa F — configurar dentro do sistema

1. **Configuracao Despachante**: webhook `http://n8n:5678/webhook/alerta-dom`, URL Evolution `http://evolution:8080`, instância `dom-cristo`, antecedências `45,30,15,5`, **modo simulação ligado**.
   Confira também em **System Settings** o fuso `America/Sao_Paulo`: o app já configura na instalação, mas o assistente de primeiro login do Frappe pode trocar. Com fuso errado, os alertas diários saem com a data errada.
2. **Teste do alerta** (sem enviar nada): cadastre um Veículo com `exercicio_licenciamento` do ano corrente e veja o vencimento ser calculado pelo calendário; depois:

```bash
docker compose --project-name dom exec backend \
  bench --site despacho.dom.local execute dom_despachante.tasks.enviar_alertas_licenciamento
```

   Confira em **Error Log** a mensagem gerada. Só então desligue o modo simulação.
3. **Usuários**: um por funcionário, com papel `Despachante` ou `Atendente` (o `username` do usuário é a matrícula que aparece na O.S.).
4. **Serviços**: 14 já vêm semeados — ajuste honorários e taxas.
5. **Calendário**: SP/2026 vem semeado da sua planilha; **confira no site do DETRAN** antes de confiar.
6. **Procuração**: imprima uma O.S. e veja o PDF gerado pelo Print Format `procuracao`.

---

## Etapa G — backup

```bash
chmod +x ~/sistema_despachante/ops/scripts/backup.sh
sudo crontab -e
# 0 2 * * * SITE=despacho.dom.local COMPOSE_DIR=/home/SEU_USUARIO/frappe_docker /home/SEU_USUARIO/sistema_despachante/ops/scripts/backup.sh >> /var/log/dom-backup.log 2>&1
```

Rode uma vez na mão e confirme que o `.tar.gz` aparece em `/var/backups/dom-despachante`.

---

## Etapa H — checklist final (aceite)

- [ ] `list-apps` mostra `dom_despachante` e `ps` mostra todos os containers `Up`
- [ ] Consegui criar Cliente (com CPF válido), Empresa (CNPJ válido) e Veículo (placa Mercosul)
- [ ] Veículo calculou `data_vencimento_licenciamento` sozinho
- [ ] Criei uma O.S. e o checklist de documentos apareceu automático
- [ ] Imprimi a procuração em PDF
- [ ] Alerta de licenciamento gerou mensagem no Error Log (modo simulação)
- [ ] Mensagem chegou no WhatsApp de teste (simulação desligada)
- [ ] Backup gerado + restore testado em site de teste
- [ ] Senha do `Administrator` trocada e usuários criados
- [ ] Portas 8080/5678/8081 fechadas para fora da LAN

---

## Se alguma etapa falhar, me mande exatamente isto

```bash
docker compose --project-name dom ps
docker compose --project-name dom logs backend --tail 200
docker compose --project-name dom exec backend bench --site despacho.dom.local list-apps
docker run --rm --entrypoint ls dom-erp:1.0.0 /home/frappe/frappe-bench/apps
```

Com esses quatro retornos eu identifico se o problema é imagem, banco, site ou app.

---

## Depois, para atualizar o sistema (quando eu mudar o código)

```bash
cd ~/sistema_despachante && git pull
cd ~/frappe_docker && git pull
~/sistema_despachante/ops/scripts/build-imagem.sh ~/frappe_docker dom-erp:1.0.1
sed -i 's/^CUSTOM_TAG=.*/CUSTOM_TAG=1.0.1/' ~/frappe_docker/.env
cd ~/frappe_docker
docker compose --project-name dom up -d
docker compose --project-name dom exec backend bench --site despacho.dom.local migrate
docker compose --project-name dom restart backend scheduler queue-short queue-long
```

> Se o build reaproveitar o clone antigo do app (camada em cache), rode-o com `--no-cache` ou acrescente `--build-arg=CACHE_BUST=$(date +%s)` no `docker build` do script.

---

## Apêndice — rodar no WSL (Windows, desenvolvimento/teste)

Testado em 25/11/2026 num Windows 10 com WSL2 + Ubuntu 24.04 (systemd ligado). Usa **Docker Engine dentro do WSL**, não Docker Desktop. É o mesmo caminho das Etapas C e D, com dois ajustes: a porta fica em `localhost` do Windows, e o código do app é montado dentro dos containers, então você edita e testa sem gerar imagem nova.

```bash
# 1) Docker dentro do WSL (uma vez)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"      # feche e abra o terminal do WSL
sudo systemctl enable --now docker

# 2) Código + imagem (igual à Etapa C, caminho C2)
cd ~
git clone https://github.com/rafaelangelis/sistema_despachante.git
git clone https://github.com/frappe/frappe_docker.git
chmod +x ~/sistema_despachante/ops/scripts/*.sh
~/sistema_despachante/ops/scripts/build-imagem.sh ~/frappe_docker dom-erp:1.0.0   # 15-30 min

# 3) Compose com o override de desenvolvimento
cd ~/frappe_docker
cp example.env .env
cp ~/sistema_despachante/ops/frappe-overrides/compose.dom*.yaml overrides/
```

No `.env`, use o mesmo conteúdo da Etapa D, trocando a linha `COMPOSE_FILE` por esta (acrescenta o `compose.dom-dev.yaml`) e adicionando `DOM_APP_SRC` com o caminho **absoluto** do clone (rode `echo $HOME` para saber o seu):

```env
COMPOSE_FILE=compose.yaml:overrides/compose.mariadb.yaml:overrides/compose.redis.yaml:overrides/compose.noproxy.yaml:overrides/compose.dom.yaml:overrides/compose.dom-dev.yaml
DOM_APP_SRC=/home/SEU_USUARIO/sistema_despachante
```

> Não use `~` no `DOM_APP_SRC`: com `sudo docker compose` ele vira `/root`, o Docker cria uma pasta vazia e a monta por cima do app — o site passa a responder 502.

Depois siga a Etapa D a partir do `docker compose --project-name dom up -d` (use `set-config host_name http://localhost:8080`). O sistema abre no navegador do Windows em **http://localhost:8080**.

Ciclo de desenvolvimento no WSL:

```bash
cd ~/frappe_docker
# mudou só Python/Jinja:
docker compose --project-name dom restart backend scheduler queue-short queue-long
# mudou DocType (JSON), patches ou hooks:
docker compose --project-name dom exec backend bench --site despacho.dom.local migrate
```

Dicas que custaram tempo na primeira instalação:

- Do PowerShell, rodar `wsl -e bash -c "..."` com aspas aninhadas quebra fácil; prefira abrir o terminal do Ubuntu ou mandar um `.sh` para o `wsl -e bash arquivo.sh`.
- `docker run --rm dom-erp:1.0.0 ls ...` **sem** `--entrypoint ls` mostra a saída do entrypoint e parece que o app não está na imagem.
- O WSL encaminha as portas para o `localhost` do Windows: confira antes que 8080/5678/8081 não estejam em uso no Windows.
