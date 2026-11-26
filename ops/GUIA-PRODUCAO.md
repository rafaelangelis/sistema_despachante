# DOM Despachante — esqueleto pronto para produção

> **COMECE POR ops/RUNBOOK-OUTRA-MAQUINA.md** se o objetivo é instalar do zero em outra máquina: é a versão linear, com checkpoints de verificação.
> Estado atual, pendências e como retomar o projeto: ops/ESTADO-E-PROXIMOS-PASSOS.md. Este arquivo é a referência completa (arquitetura, ciclo de mudança, roadmap, links e troubleshooting).

Sistema de O.S. para despachante (veículos, CNH, recursos de multa, náutico, SCR-BCB, corretor) montado sobre **Frappe v15** com quatro peças maduras reaproveitadas, em vez de tudo do zero.

## O que já está pronto nesta pasta

```
sistema_despachante/            <- repositorio (privado)
├── pyproject.toml               <- raiz do app: precisa ficar aqui para o build do frappe_docker
├── license.txt                  (MIT)
├── README.md                    <- README do app
├── dom_despachante/             <- codigo do app (DocTypes, hooks, tasks, print format)
└── ops/                         <- tudo de operacao/deploy
    ├── RUNBOOK-OUTRA-MAQUINA.md    <- COMECE AQUI: instalacao do zero, passo a passo
    ├── ESTADO-E-PROXIMOS-PASSOS.md <- estado atual, pendencias e como retomar
    ├── GUIA-PRODUCAO.md            <- referencia completa (arquitetura, ciclo, links)
    ├── apps.json                   <- lista de apps para o build da imagem custom
    ├── docker-compose.satelites.yml <- WhatsApp (Evolution API) + n8n
    ├── .env.exemplo                <- copie para .env e troque os valores
    ├── n8n/alerta-licenciamento.json <- workflow pronto para importar
    ├── especificacao/SISTEMA-DOM.xlsx <- planilha original da DOM
    └── scripts/build-imagem.sh + backup.sh
```

### O que foi reaproveitado (e não escrito do zero)

| Peça | Origem | Licença | O que resolve |
|---|---|---|---|
| Framework | [frappe/frappe](https://github.com/frappe/frappe) | MIT | Formulário, listagem, permissões, anexos, histórico campo a campo, dashboard, impressão, agendador |
| CEP / CNPJ | [BrasilAPI/BrasilAPI](https://github.com/BrasilAPI/BrasilAPI) | MIT | Preenchimento automático de endereço e dados da empresa |
| WhatsApp | [EvolutionAPI/evolution-api](https://github.com/EvolutionAPI/evolution-api) | Apache-2.0 | Envio das mensagens de vencimento |
| Automação | [n8n-io/n8n](https://github.com/n8n-io/n8n) | Sustainable Use (fair-code) | Recebe o webhook do Frappe e chama a Evolution |
| Deploy | [frappe/frappe_docker](https://github.com/frappe/frappe_docker) | MIT | Compose de produção (db, redis, workers, scheduler, frontend) |

Opcionais que você pluga depois, quando doer: [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) (GPL-3.0) para acervo com OCR e [docusealco/docuseal](https://github.com/docusealco/docuseal) (AGPL-3.0) para assinatura. **Atenção:** AGPL obriga abrir suas modificações se o serviço for oferecido pela rede — como é uso interno da DOM, não te afeta; só te afetaria se um dia virar produto para terceiros.

### Modelo de dados que saiu da planilha

| DocType | Papel |
|---|---|
| `Cliente` | PF: dados, telefones (tabela), gov.br (sem senha), CNH completa, endereço com CEP, vínculos com empresas |
| `Telefone Cliente` / `Vinculo Empresa` / `Contato Setor` | tabelas filhas |
| `Empresa` | PJ: razão social, fantasia, CNPJ, IE, contrato social JUCESP + status OK/Pendente/Vencido, contatos por setor |
| `Veiculo` | placa, final calculado, RENAVAM, chassi, tipo/combustível/categoria, dados de pesados, situação, e **vencimento de licenciamento calculado** pela tabela de calendário |
| `Servico` | catálogo (categoria, órgão, prazo, honorário e taxa padrão) — já semeado com 14 serviços |
| `Ordem de Servico` | O.S. com categoria, status, responsável/matrícula, itens de serviço, checklist automático de documentos, totais e pagamento |
| `OS Servico` / `OS Documento` | tabelas filhas (valores por item, protocolo, anexo, status do documento) |
| `Calendario Licenciamento` | regra por UF + ano + grupo + final de placa — já semeado com SP/2026 da sua planilha |
| `Configuracao Despachante` | dados da empresa, antecedências de alerta, textos, webhook, Evolution API, modo simulação |

Auditoria "quem fez o quê": `track_changes` está ligado em todos os DocTypes e `funcionario_responsavel` + `matricula` na O.S. O histórico campo a campo aparece na aba **Versions** de cada documento; o histórico de O.S. por funcionário sai de um relatório simples sobre `tabVersion`.

---

## Pré-requisitos

- VM Linux (Debian 12 ou Ubuntu 22.04/24.04) no Proxmox, 4 vCPU / 8 GB RAM / 80 GB SSD (mínimo confortável para Frappe + satélites).
- Docker Engine + plugin compose.
- Rede: portas 8080 (Frappe), 5678 (n8n), 8081 (Evolution) acessíveis na LAN. Não exponha nada direto na internet.
- Um repositório seu no GitHub para o app (privado serve).

```bash
# Docker em Debian/Ubuntu (script oficial)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"   # depois saia e entre de novo na sessão
```

---

## Etapa 1 — Teste rápido (20 minutos, sem imagem custom)

Serve para ver o sistema rodando antes de investir no build. Usa o compose de desenvolvimento do próprio frappe_docker.

```bash
cd ~
git clone https://github.com/frappe/frappe_docker.git
cd frappe_docker
cp example.env .env
docker compose -f pwd.yml up -d
docker compose -f pwd.yml logs -f create-site     # Ctrl+C quando aparecer "Site frontend created"
```

Acesse `http://IP-DA-VM:8080` → usuário `Administrator`, senha `admin`.

Nesse modo o app **não** está instalado (ele entra na imagem custom, Etapa 3). O objetivo aqui é só validar Docker + portas + banco. Depois:

```bash
docker compose -f pwd.yml down
```

---

## Etapa 2 — Repositório (já feito em 25/11/2026)

O código já está no repositório privado **`rafaelangelis/sistema_despachante`**, branch `main`, com o app na raiz e todo o material de operação em `ops/`. Para instalar em uma máquina nova, basta clonar:

```bash
git clone https://github.com/rafaelangelis/sistema_despachante.git
```

Só use o bloco abaixo se um dia precisar publicar em outro repositório:

```bash
cd ~/sistema_despachante
git init && git add . && git commit -m "app dom_despachante"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/NOVO-REPO.git
git push -u origin main
```

O repositório é **público** desde 25/11/2026, então o build da imagem (que clona o repo de dentro do container, sem as suas credenciais) funciona direto com `ops/apps.json`. Se um dia ele voltar a ser privado, use a variante descrita no caminho C1 do `RUNBOOK-OUTRA-MAQUINA.md` (token de leitura em `ops/apps.local.json`, fora do git).

```bash
gh repo edit rafaelangelis/sistema_despachante --visibility public --accept-visibility-change-consequences
```

Com o repositório público, `ops/apps.json` já funciona como está — o token deixa de existir em qualquer máquina.

---

## Etapa 3 — Gerar a imagem com o app embutido

O build precisa do frappe_docker e lê o `apps.json`.

```bash
cd ~/sistema_despachante/ops
chmod +x scripts/*.sh
./scripts/build-imagem.sh ~/frappe_docker dom-erp:1.0.0
```

Por baixo, o script faz exatamente isto (documentado em <https://github.com/frappe/frappe_docker>):

```bash
docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 \
  --build-arg=PYTHON_VERSION=3.11.9 \
  --build-arg=DEBIAN_BASE=bookworm \
  --secret=id=apps_json,src=$HOME/sistema_despachante/ops/apps.json \
  --build-arg=CACHE_BUST=$(date +%s) \
  --tag=dom-erp:1.0.0 \
  --file=images/custom/Containerfile .
```

O frappe_docker lê o `apps.json` (passado como *build secret*) e instala `frappe` + `dom_despachante` no bench da imagem.

> **Mudou no frappe_docker (verificado em 25/11/2026):** o antigo `--build-arg=APPS_JSON_BASE64` é **ignorado sem erro** — a imagem sai só com o `frappe`. E o padrão da imagem virou Python 3.14 / Debian trixie (pensado para a v16); o Frappe v15 exige Python 3.10–3.12, por isso `PYTHON_VERSION=3.11.9` + `DEBIAN_BASE=bookworm`. O `compose.mariadb.yaml` atual também usa MariaDB 11.8; para a v15 fixe `mariadb:10.6` num override.

---

## Etapa 4 — Subir a produção e criar o site

```bash
cd ~/frappe_docker
cp custom/example.env .env        # se não existir, use example.env
```

Edite o `.env` (valores do `.env.exemplo` desta pasta):

```env
CUSTOM_IMAGE=dom-erp
CUSTOM_TAG=1.0.0
PULL_POLICY=missing
DB_PASSWORD=<senha-forte>
DB_ROOT_PASSWORD=<outra-senha-forte>
FRAPPE_SITE_NAME_HEADER=despacho.dom.local
LETSENCRYPT_EMAIL=ti@dom.local
```

```bash
docker compose --project-name dom up -d

# criar o site já com o app instalado
docker compose --project-name dom exec backend \
  bench new-site despacho.dom.local \
    --mariadb-user-host-login-scope='%' \
    --admin-password '<senha-do-Administrator>' \
    --db-root-username root \
    --db-root-password '<DB_ROOT_PASSWORD>' \
    --install-app dom_despachante

# definir como site padrão e habilitar o agendador (necessário para os alertas)
docker compose --project-name dom exec backend bench use despacho.dom.local
docker compose --project-name dom exec backend bench --site despacho.dom.local enable-scheduler
docker compose --project-name dom exec backend bench --site despacho.dom.local set-config host_name http://despacho.dom.local:8080
docker compose --project-name dom restart backend scheduler queue-short queue-long
```

Acesse `http://IP-DA-VM:8080`. Para nome de domínio interno, aponte `despacho.dom.local` no DNS do MikroTik ou no `hosts` das máquinas.

**Verificação pós-instalação (deve rodar sem erro):**

```bash
docker compose --project-name dom exec backend bench --site despacho.dom.local list-apps
# esperado: frappe 15.x, dom_despachante 0.0.1

docker compose --project-name dom exec backend bench --site despacho.dom.local execute dom_despachante.tasks.enviar_alertas_licenciamento
```

---

## Etapa 5 — Satélites: WhatsApp e n8n

```bash
cd ~/sistema_despachante/ops
cp .env.exemplo .env      # troque as chaves: EVOLUTION_API_KEY, N8N_ENCRYPTION_KEY, N8N_HOST
docker compose -f docker-compose.satelites.yml up -d
docker compose -f docker-compose.satelites.yml logs -f evolution    # Ctrl+C quando estabilizar
```

Criar a instância do WhatsApp e parear o número:

```bash
curl -X POST http://IP-DA-VM:8081/instance/create \
  -H "apikey: SUA_EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"instanceName":"dom-cristo","qrcode":true,"integration":"WHATSAPP-BAILEYS"}'

# ler o QR Code no celular (WhatsApp → Aparelhos conectados)
curl http://IP-DA-VM:8081/instance/connect/dom-cristo -H "apikey: SUA_EVOLUTION_API_KEY"
```

A mesma rede do compose: **os três containers (Frappe, n8n, Evolution) precisam se falar**. Se o compose do Frappe estiver com outro nome de projeto, crie uma rede externa comum:

```bash
docker network create dom-net
# adicione em ambos os arquivos compose:
# networks: { default: { name: dom-net, external: true } }
```

Importe o workflow no n8n (`http://IP-DA-VM:5678`): **Workflows → ⋯ → Import from file** → `ops/n8n/alerta-licenciamento.json` → **Activate**. Ele escuta `POST /webhook/alerta-dom` e chama `POST /message/sendText/dom-cristo` na Evolution.

---

## Etapa 6 — Ligar os alertas

No sistema: **Configuracao Despachante** (busque na barra de busca).

| Campo | Valor |
|---|---|
| Webhook do n8n para WhatsApp | `http://n8n:5678/webhook/alerta-dom` (se estiverem na mesma rede Docker) |
| URL da Evolution API | `http://evolution:8080` |
| Instância | `dom-cristo` |
| Antecedências | `45,30,15,5` |
| Modo simulação | **ligado** no começo |

Com **modo simulação ligado**, nada vai para o WhatsApp: cada disparo é gravado em **Error Log**. Faça o teste com um veículo cadastrado e vencimento daqui a 45 dias:

```bash
docker compose --project-name dom exec backend \
  bench --site despacho.dom.local execute dom_despachante.tasks.enviar_alertas_licenciamento
```

Depois veja **Error Log** no sistema. Quando estiver certo, desligue o modo simulação. O agendador roda a rotina diariamente (madrugada, horário do servidor).

---

## Etapa 7 — Cadastros iniciais

1. **Usuários:** crie um usuário por funcionário e dê os papéis `Despachante` (tudo) ou `Atendente` (sem excluir). A matrícula vai no campo `username` do usuário e é copiada para a O.S.
2. **Serviços:** 14 já vêm semeados — ajuste honorários e taxas reais em `Servico`.
3. **Calendário:** SP/2026 já vem semeado a partir da sua planilha. **Confirme no site do DETRAN antes de confiar** e cadastre o ano seguinte quando publicar: `https://www.detran.sp.gov.br`.
4. **Campos novos sem código:** use **Customize Form** (menu ⋯ de qualquer DocType). As mudanças ficam no banco do site e sobrevivem a atualizações de imagem — é o caminho para ajustar o sistema sem rebuild.
5. **Procuração:** o Print Format `procuracao` vem marcado como padrão (standard = somente leitura). Para customizar o texto: duplique (**Duplicate**) e edite a cópia.

---

## Etapa 8 — Backup (não pule)

```bash
chmod +x ~/sistema_despachante/ops/scripts/backup.sh
sudo crontab -e
# troque SEU_USUARIO pelo usuario da VM
# 0 2 * * * SITE=despacho.dom.local COMPOSE_DIR=/home/SEU_USUARIO/frappe_docker /home/SEU_USUARIO/sistema_despachante/ops/scripts/backup.sh >> /var/log/dom-backup.log 2>&1
```

Testar restore uma vez, em ambiente separado:

```bash
docker compose --project-name dom exec backend bench --site site-teste restore /home/frappe/frappe-bench/sites/despacho.dom.local/private/backups/<arquivo>.sql.gz --with-files
```

---

## Etapa 9 — Ciclo de mudança (você toca o código)

```bash
# 1. alterou DocType/print format/py no repo do app
cd ~/sistema_despachante
git add . && git commit -m "ajuste" && git push

# 2. nova tag de imagem e rebuild
cd ~/sistema_despachante/ops
./scripts/build-imagem.sh ~/frappe_docker dom-erp:1.1.0

# 3. subir e migrar
cd ~/frappe_docker
sed -i 's/^CUSTOM_TAG=.*/CUSTOM_TAG=1.1.0/' .env
docker compose --project-name dom up -d
docker compose --project-name dom exec backend bench --site despacho.dom.local migrate
docker compose --project-name dom restart backend scheduler queue-short queue-long
```

---

## Checklist de produção

- [ ] Senha do `Administrator` trocada; usuário `Administrator` sem uso diário
- [ ] Um usuário por funcionário, com papel `Despachante` ou `Atendente`
- [ ] `modo_simulacao` desligado **só** depois de validar o envio no WhatsApp
- [ ] `.env` fora do git; `chmod 600 .env`
- [ ] Backup diário rodando e restore testado
- [ ] Firewall: portas 8080/8081/5678 só na LAN (MikroTik) — nada de port forward
- [ ] `bench --site ... enable-scheduler` habilitado e conferido em **Scheduled Job Log**
- [ ] LGPD: base legal para tratar CPF/CNH; **nunca** armazenar senha gov.br (use o campo de observação)
- [ ] Conversa com o jurídico sobre SCR-BCB (dado restrito do BCB — só via birô licenciado) e sobre scraping de portais (não usar em produção)

---

## O que ainda não está feito (roadmap honesto)

| Falta | Como atacar |
|---|---|
| Portal do cliente / status de O.S. por WhatsApp | Web Form do Frappe (formulário público sem código) + link mágico |
| Financeiro completo (contas a receber, repasse de taxas, inadimplência) | Módulo Accounts do ERPNext, ou DocType próprio de "Recebimento" ligado à O.S. |
| RPA nos portais DETRAN/gov.br | Playwright + credenciamento oficial; **não** use scraping SINESP. Ver `JConfessor/CRLV-Auto-Downloader` (MIT) como prova de conceito |
| Leitura automática de CNH/CRLV/ATPV para preencher o cadastro | OCR: `stackchain/ocr-cnh-2-json` (MPL-2.0), `gardim1/Leitor_De_CRLV` |
| Dashboard visual da página principal | Dashboard Chart + Number Card (nativo), ou Metabase sobre o MariaDB |
| App de campo (vistoria com foto) | Frappe PWA/`frappe-ui`, ou app mobile lendo a API REST nativa |

## Links usados

- Frappe framework — <https://github.com/frappe/frappe> · docs <https://docs.frappe.io/framework>
- Frappe Docker — <https://github.com/frappe/frappe_docker>
- DocTypes, Customize Form — <https://docs.frappe.io/framework/user/en/basics/doctypes>
- Print Format (Jinja) — <https://docs.frappe.io/framework/user/en/guides/print-format>
- Scheduler / alertas — <https://docs.frappe.io/framework/user/en/guides/scheduled-jobs>
- BrasilAPI (CEP, CNPJ, FIPE) — <https://brasilapi.com.br/docs>
- Evolution API — <https://github.com/EvolutionAPI/evolution-api> · docs <https://doc.evolution-api.com>
- n8n — <https://github.com/n8n-io/n8n> · docs <https://docs.n8n.io>
- DETRAN-SP (calendário de licenciamento) — <https://www.detran.sp.gov.br>
- LGPD / ANPD — <https://www.gov.br/anpd>

## Troubleshooting

| Sintoma | Causa provável / solução |
|---|---|
| `bench new-site` erro de permissão no MariaDB | falta `--mariadb-user-host-login-scope='%'` |
| App não aparece em `list-apps` | não foi instalado no site: `bench --site <site> install-app dom_despachante` |
| Permissões dos papéis não aparecem | rode `bench --site <site> migrate` uma vez (o hook `before_migrate` cria `Despachante`/`Atendente`) |
| Alertas não disparam | scheduler desabilitado, ou `data_vencimento_licenciamento` vazio (depende do `Calendario Licenciamento` cadastrado) |
| Webhook retorna erro de container desconhecido | Frappe e n8n em redes diferentes — crie `dom-net` externa (Etapa 5) |
| QR Code da Evolution não gera | instância já existente: `DELETE /instance/logout/dom-cristo` e recrie |
| Erro ao validar CPF de teste | use CPF com dígito válido (ex.: 111.444.777-35) |
| Criei um DocType novo e as validações Python não rodam | o Frappe procura o controller em `doctype/<nome_minusculo_com_underscore>/`, gerado por `scrub` do nome: `Ordem de Servico` → `ordem_de_servico`. Se a pasta não bater com o nome, o Frappe cai no controller base e ignora seu `.py` |

**Regra de ouro ao criar DocType novo:** pasta e arquivos = nome do DocType em minúsculas, espaços e hífens trocados por `_` (ex.: `Ordem de Servico` → `ordem_de_servico/ordem_de_servico.json` + `.py`). O `name` dentro do JSON continua com o nome legível.
