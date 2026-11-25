# Estado do projeto e próximos passos

Documento para retomar o trabalho em qualquer máquina, com ou sem o histórico da conversa anterior. Última atualização: **25/11/2026**.

## Onde as coisas estão

| O quê | Onde |
|---|---|
| Código (app Frappe + operação) | repositório privado `rafaelangelis/sistema_despachante`, branch `main` |
| Guia completo (referência) | `ops/GUIA-PRODUCAO.md` |
| Instalação linear do zero em outra máquina | `ops/RUNBOOK-OUTRA-MAQUINA.md` |
| Especificação original (planilha da DOM) | `ops/especificacao/SISTEMA-DOM.xlsx` |
| Cópia de trabalho nesta máquina (Windows) | `C:\Users\Administrator\Desktop\sistema_despachante` |

## O que já está feito

- **Pesquisa e decisão de stack** (não refazer): não existe sistema de despachante open-source maduro no GitHub. Os repos do nicho têm 0–3 estrelas e quase nenhum tem licença, então não são reaproveitáveis. A escolha foi **Frappe v15** (MIT) + peças maduras, porque a especificação é CRUD com prazo, documento, impressão e auditoria.
- **App `dom_despachante` completo**, instalável: 12 DocTypes (Cliente, Telefone Cliente, Empresa, Contato Setor, Vinculo Empresa, Veiculo, Servico, Ordem de Servico, OS Servico, OS Documento, Calendario Licenciamento, Configuracao Despachante).
- **Regras de negócio**: validação de CPF/CNPJ/placa/RENAVAM/chassi, CEP e CNPJ via BrasilAPI, final de placa e vencimento de licenciamento calculados, checklist de documentos automático por categoria de serviço, totais da O.S., histórico de alterações campo a campo.
- **Alertas** de licenciamento e de CNH em 45/30/15/5 dias (rotina diária) com saída por webhook → n8n → Evolution API/WhatsApp, começando em **modo simulação**.
- **Print Format** de procuração particular em PDF/Jinja.
- **Operação**: `apps.json`, `docker-compose.satelites.yml` (Evolution `v2.3.8` + n8n), workflow n8n importável, scripts de build e backup, `.env.exemplo`.
- **Sementes na instalação**: papéis `Despachante`/`Atendente`, 14 serviços, calendário de licenciamento SP/2026 (vindo da planilha).

## O que ainda NÃO foi feito (em ordem)

| # | Pendência | Observação |
|---|---|---|
| 1 | Instalar em produção (VM do Proxmox) | Siga `ops/RUNBOOK-OUTRA-MAQUINA.md`. Nada foi executado em Docker ainda: o app nunca rodou em um bench real |
| 2 | Decidir repositório privado + token **ou** público | Enquanto for privado, o build da imagem custom exige token de leitura |
| 3 | Confirmar o calendário de licenciamento no site do DETRAN | O de SP/2026 foi semeado a partir da planilha; regra muda a cada ano e pode variar por UF |
| 4 | Financeiro | Contas a receber, repasse de taxas ao órgão, inadimplência. Opção: módulo Accounts do ERPNext, ou DocType de Recebimento ligado à O.S. |
| 5 | Portal do cliente / status por WhatsApp | Web Form nativo do Frappe resolve sem código |
| 6 | OCR de CNH/CRLV/ATPV para preencher cadastro | Referências: `stackchain/ocr-cnh-2-json` (MPL-2.0), `gardim1/Leitor_De_CRLV` |
| 7 | RPA nos portais DETRAN/gov.br | Só com credenciamento oficial. Prova de conceito: `JConfessor/CRLV-Auto-Downloader` (MIT). **Não** usar scraping SINESP |
| 8 | Dashboard da página principal | Dashboard Chart + Number Card nativos, ou Metabase sobre o MariaDB |
| 9 | App de campo para vistoria (fotos) | Frappe PWA / `frappe-ui` |

## Decisões pendentes (precisam da DOM)

1. **Repositório público ou privado?** Público simplifica build e máquinas novas; o código é MIT e não contém segredo.
2. **SCR-BCB**: é serviço que a DOM pretende vender? Só é integrável via birô licenciado (Serasa/SPC/Quod) — o SCR do Banco Central é de acesso restrito a instituições autorizadas e ao titular. Definir antes de qualquer linha de código.
3. **WhatsApp**: Evolution API (não oficial, risco de banimento, grátis) ou Cloud API oficial da Meta (template aprovado, custo por conversa). A escolha afeta o volume de disparo permitido.
4. **Campo "login do gov.br" com alerta de 45 dias** (planilha): é alerta de senha/conta gov.br ou de validade da CNH? Hoje o sistema trata validade de CNH; senha gov.br nunca deve ser armazenada.

## Riscos conhecidos

- O app **nunca rodou em Frappe real**. Os JSONs foram validados sintaticamente e a correspondência DocType↔pasta foi conferida (`Ordem de Servico` → `ordem_de_servico/`), mas erros de schema só aparecem no `bench migrate` / `new-site`.
- `bench new-site --install-app` é o primeiro ponto de falha provável; o segundo é a rede Docker entre Frappe, n8n e Evolution.
- Escritório pequeno, um site: sem multi-tenancy. Multi-empresa exigiria Frappe multisite.

## Como retomar o trabalho com o Claude

Abra o Claude Code na pasta do projeto e mande algo assim:

> "Projeto DOM Cristo Despachante. Leia `ops/ESTADO-E-PROXIMOS-PASSOS.md` e `ops/RUNBOOK-OUTRA-MAQUINA.md` no repositório `rafaelangelis/sistema_despachante`. Parei na etapa X, aconteceu Y. Quero continuar daí."

Se você levar apenas este repositório para outra máquina, o contexto necessário está todo aqui: o estado, as decisões, as pendências e os motivos. O histórico da conversa anterior não é necessário.

## Comandos de uso diário (depois de instalado)

```bash
# atualizar o sistema depois de mudança no código
cd ~/sistema_despachante && git pull
cd ~/frappe_docker
export APPS_JSON_BASE64=$(base64 -w 0 ~/sistema_despachante/ops/apps.local.json)
docker build --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 --build-arg=APPS_JSON_BASE64="$APPS_JSON_BASE64" \
  --tag=dom-erp:1.0.1 --file=images/custom/Containerfile .
sed -i 's/^CUSTOM_TAG=.*/CUSTOM_TAG=1.0.1/' ~/frappe_docker/.env
docker compose --project-name dom up -d
docker compose --project-name dom exec backend bench --site despacho.dom.local migrate

# rodar os alertas na mão (teste)
docker compose --project-name dom exec backend bench --site despacho.dom.local \
  execute dom_despachante.tasks.enviar_alertas_licenciamento

# backup imediato
SITE=despacho.dom.local COMPOSE_DIR=~/frappe_docker ~/sistema_despachante/ops/scripts/backup.sh
```
