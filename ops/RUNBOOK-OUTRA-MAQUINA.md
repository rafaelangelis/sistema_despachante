# Runbook — terminar a instalação em outra máquina

> Siga este arquivo de cima para baixo. Estado atual e decisões pendentes: ops/ESTADO-E-PROXIMOS-PASSOS.md. Referência técnica completa: ops/GUIA-PRODUCAO.md. Especificação original da DOM: ops/especificacao/SISTEMA-DOM.xlsx.

Estado em 25/11/2026: o app está no repositório privado `rafaelangelis/sistema_despachante` (branch `main`, commit `77f7cda`, 52 arquivos). **Nada foi instalado em produção ainda** — nem Docker, nem Frappe, nem banco. Tudo abaixo é a partir do zero na máquina de destino.

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

cd ~/frappe_docker
export APPS_JSON_BASE64=$(base64 -w 0 ~/sistema_despachante/ops/apps.local.json)
docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 \
  --build-arg=APPS_JSON_BASE64="$APPS_JSON_BASE64" \
  --tag=dom-erp:1.0.0 \
  --file=images/custom/Containerfile .
```

**C2 (padrão hoje) repositório público — sem token:**

```bash
git clone https://github.com/rafaelangelis/sistema_despachante.git
git clone https://github.com/frappe/frappe_docker.git
cd ~/frappe_docker
export APPS_JSON_BASE64=$(base64 -w 0 ~/sistema_despachante/ops/apps.json)
docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 \
  --build-arg=APPS_JSON_BASE64="$APPS_JSON_BASE64" \
  --tag=dom-erp:1.0.0 \
  --file=images/custom/Containerfile .
```

**C3 se o build não funcionar com token:** clone o app no host e monte dentro de um container bench de desenvolvimento; nesse caso avise que eu ajusto o `Containerfile`.

Verificação do build:

```bash
docker run --rm dom-erp:1.0.0 ls /home/frappe/frappe-bench/apps
# esperado: frappe  dom_despachante
```

Se `dom_despachante` não estiver lá, o clone falhou dentro do build (token/URL) — o log do `docker build` mostra o erro.

---

## Etapa D — subir a produção e criar o site

```bash
cd ~/frappe_docker
cp example.env .env      # se existir custom/example.env, prefira ele
```

Edite o `.env`:

```env
CUSTOM_IMAGE=dom-erp
CUSTOM_TAG=1.0.0
PULL_POLICY=missing
DB_PASSWORD=troque-por-senha-forte
DB_ROOT_PASSWORD=troque-por-outra-senha-forte
FRAPPE_SITE_NAME_HEADER=despacho.dom.local
LETSENCRYPT_EMAIL=ti@dom.local
```

```bash
docker compose --project-name dom up -d
docker compose --project-name dom ps          # todos Up, db healthy

docker compose --project-name dom exec backend \
  bench new-site despacho.dom.local \
    --mariadb-user-host-login-scope='%' \
    --admin-password 'SENHA-DO-ADMINISTRATOR' \
    --db-root-username root \
    --db-root-password 'SENHA-DB-ROOT' \
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

```bash
cd ~/sistema_despachante/ops
cp .env.exemplo .env
# edite: EVOLUTION_API_KEY, EVOLUTION_DB_PASSWORD, N8N_ENCRYPTION_KEY, N8N_HOST=IP-DA-VM
docker compose -f docker-compose.satelites.yml up -d
docker compose -f docker-compose.satelites.yml ps
```

Frappe, n8n e Evolution precisam se falar pelo nome do container. Rede comum:

```bash
docker network create dom-net
```

E acrescente em **ambos** os compose (`satelites.yml` e o do frappe_docker):

```yaml
networks:
  default:
    name: dom-net
    external: true
```

Depois `docker compose --project-name dom up -d` e `docker compose -f docker-compose.satelites.yml up -d` de novo.

Parear o WhatsApp:

```bash
curl -X POST http://IP-DA-VM:8081/instance/create \
  -H "apikey: SUA_EVOLUTION_API_KEY" -H "Content-Type: application/json" \
  -d '{"instanceName":"dom-cristo","qrcode":true,"integration":"WHATSAPP-BAILEYS"}'

curl http://IP-DA-VM:8081/instance/connect/dom-cristo -H "apikey: SUA_EVOLUTION_API_KEY"
# abra o base64/qr no navegador e leia no celular (WhatsApp > Aparelhos conectados)
```

n8n (`http://IP-DA-VM:5678`): **Workflows → ⋯ → Import from file** → `ops/n8n/alerta-licenciamento.json` → **Activate**.

---

## Etapa F — configurar dentro do sistema

1. **Configuracao Despachante**: webhook `http://n8n:5678/webhook/alerta-dom`, URL Evolution `http://evolution:8080`, instância `dom-cristo`, antecedências `45,30,15,5`, **modo simulação ligado**.
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
docker run --rm dom-erp:1.0.0 ls /home/frappe/frappe-bench/apps
```

Com esses quatro retornos eu identifico se o problema é imagem, banco, site ou app.

---

## Depois, para atualizar o sistema (quando eu mudar o código)

```bash
cd ~/sistema_despachante && git pull
cd ~/frappe_docker
export APPS_JSON_BASE64=$(base64 -w 0 ~/sistema_despachante/ops/apps.local.json)
docker build --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 --build-arg=APPS_JSON_BASE64="$APPS_JSON_BASE64" \
  --tag=dom-erp:1.0.1 --file=images/custom/Containerfile .
sed -i 's/^CUSTOM_TAG=.*/CUSTOM_TAG=1.0.1/' ~/frappe_docker/.env
docker compose --project-name dom up -d
docker compose --project-name dom exec backend bench --site despacho.dom.local migrate
docker compose --project-name dom restart backend scheduler queue-short queue-long
```
