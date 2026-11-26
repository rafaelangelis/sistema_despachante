# Estado do projeto e próximos passos

Documento para retomar o trabalho em qualquer máquina, com ou sem o histórico da conversa anterior. Última atualização: **26/11/2026**.

## Onde as coisas estão

| O quê | Onde |
|---|---|
| Código (app Frappe + operação) | repositório **público** `rafaelangelis/sistema_despachante`, branch `main` |
| Guia completo (referência) | `ops/GUIA-PRODUCAO.md` |
| Instalação linear do zero em outra máquina | `ops/RUNBOOK-OUTRA-MAQUINA.md` |
| Especificação original (planilha da DOM) | `ops/especificacao/SISTEMA-DOM.xlsx` |
| Cópia de trabalho nesta máquina (Windows) | `C:\Users\Administrator\Desktop\sistema_despachante` |
| Ambiente de desenvolvimento rodando (WSL) | Ubuntu 24.04 no WSL: `~/sistema_despachante` + `~/frappe_docker`, em `http://localhost:8080` (passo a passo no Apêndice do runbook) |

## O que já está feito

- **Pesquisa e decisão de stack** (não refazer): não existe sistema de despachante open-source maduro no GitHub. Os repos do nicho têm 0–3 estrelas e quase nenhum tem licença, então não são reaproveitáveis. A escolha foi **Frappe v15** (MIT) + peças maduras, porque a especificação é CRUD com prazo, documento, impressão e auditoria.
- **App `dom_despachante` completo**, instalável: 12 DocTypes (Cliente, Telefone Cliente, Empresa, Contato Setor, Vinculo Empresa, Veiculo, Servico, Ordem de Servico, OS Servico, OS Documento, Calendario Licenciamento, Configuracao Despachante).
- **Regras de negócio**: validação de CPF/CNPJ/placa/RENAVAM/chassi, CEP e CNPJ via BrasilAPI, final de placa e vencimento de licenciamento calculados, checklist de documentos automático por categoria de serviço, totais da O.S., histórico de alterações campo a campo.
- **Alertas** de licenciamento e de CNH em 45/30/15/5 dias (rotina diária) com saída por webhook → n8n → Evolution API/WhatsApp, começando em **modo simulação**.
- **Print Format** de procuração particular em PDF/Jinja.
- **Operação**: `apps.json`, `docker-compose.satelites.yml` (Evolution `v2.3.8` + n8n), workflow n8n importável, scripts de build e backup, `.env.exemplo`.
- **Sementes na instalação**: papéis `Despachante`/`Atendente`, 14 serviços, calendário de licenciamento SP/2026 (vindo da planilha).
- **Primeira execução real (25/11/2026, Docker no WSL)**: `bench new-site --install-app` passou; 12 DocTypes, sementes e papéis conferidos. Teste de fumaça aprovado: Cliente (CPF válido aceito, inválido e duplicado recusados), Veículo (placa normalizada, vencimento calculado pelo calendário), O.S. (checklist de 5 documentos, totais, prazo), procuração renderizada, alertas de CNH e licenciamento em simulação. Bugs encontrados e corrigidos nessa execução:
  - 7 DocTypes sem controller `.py` (o Frappe exige um por DocType) — a instalação parava no primeiro;
  - `patches.txt` sem a seção `[pre_model_sync]`;
  - Calendário Licenciamento: `autoname: field:chave` roda antes do `validate`, então a chave passou a ser montada em `before_naming`;
  - procuração usava `frappe.db.get_singles_dict`, que o Jinja seguro do Frappe bloqueia (trocado por `frappe.get_doc`);
  - **O.S. zerava honorário/taxa ao salvar**: `fetch_from` sem `fetch_if_empty` sobrescrevia o valor digitado com o do catálogo (que vem zerado).
- **Build/compose atualizados** para o frappe_docker atual (apps.json como build secret, Python 3.11, MariaDB 10.6, `COMPOSE_FILE` no `.env`).
- **Alertas ponta a ponta (25/11/2026, WSL)**: Frappe → n8n 2.49.6 → Evolution v2.3.8 pela rede `dom-net`, com instância `dom-cristo` criada e **ainda não pareada**. A rotina real `enviar_alertas_licenciamento` chamou o webhook e registrou `http_500` no histórico do veículo, que é o esperado sem celular conectado. Corrigido nessa etapa:
  - **fuso vazio** → o Frappe assumia Asia/Kolkata e `today()` virava o dia seguinte a partir das ~18h30 de Brasília (alertas com data errada). Agora `install.configurar_regionais` define `America/Sao_Paulo` + formatos BR, e um patch aplica isso em sites já instalados;
  - webhook do n8n respondia 200 **antes** de enviar (`onReceived`) e o Frappe marcava tudo como enviado; agora é `lastNode`;
  - n8n fixado em 2.49.6 com `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (o 2.x bloqueia o `$env` que o workflow usa);
  - workflow com `id` fixo, importado e publicado pela CLI.
- **Rodada de 25-26/11/2026** (tudo no PR #1, com testes):
  - **Virada anual do exercício**: nenhuma rotina avançava o exercício do veículo, então um veículo de 2026 nunca mais gerava alerta. Agora roda diariamente, e também no início dos alertas.
  - **Calendário**: sem o calendário do ano, o vencimento usa o do ano anterior e fica marcado como *estimado*. Cadastrar ou corrigir uma regra recalcula os veículos. Há o botão *Copiar calendario* e, a partir de novembro, um aviso semanal no sininho quando falta o calendário do ano seguinte.
  - **Permissões** testadas por papel: o Atendente não conseguia escolher o serviço na O.S. (corrigido) e podia exportar clientes em massa (removido).
  - **Backup/restore**: o `backup.sh` não funcionava (faltava `--project-name`). Foi reescrito, e o `restore.sh` foi criado e testado, incluindo a `encryption_key`.
  - **Financeiro**: Recebimento confirmável e cancelável; saldo e situação calculados na O.S.; repasse de taxas ao órgão; relatórios Contas a Receber, Caixa Recebimentos e Taxas a Repassar; recibo com valor por extenso.
  - **Painel** (workspace *Despachante*): 6 indicadores, 3 gráficos e atalhos, também para o Atendente.
  - **Aviso de andamento da O.S.** ao cliente pelo WhatsApp (vem desligado; respeita simulação e oposição).
  - **LGPD**: pedido de "não receber WhatsApp" e anonimização do cliente, que também apaga o histórico de alterações.
  - **Portal público** `/status-os`: o cliente vê o status e os documentos pendentes com número da O.S. + CPF/CNPJ, com limite de tentativas e sem dados pessoais nem valores.
  - **Testes automatizados** (79) e **CI no GitHub Actions** (Frappe v15 limpo a cada PR).
  - **Build**: `CACHE_BUST` obrigatório. Sem ele a imagem "nova" saía com o código antigo, e isso foi confirmado em teste.

## O que ainda NÃO foi feito (em ordem)

| # | Pendência | Observação |
|---|---|---|
| 1 | Juntar o PR #1 ao `main` | O build da produção usa o `main` (`ops/apps.json`); sem o merge a VM sobe a versão antiga, com os bugs |
| 2 | Instalar em produção (VM do Proxmox) | Siga `ops/RUNBOOK-OUTRA-MAQUINA.md`. Etapas C, D, E e G validadas no WSL; falta a VM, **parear o celular do WhatsApp** (QR) e o aceite (Etapa H) |
| 3 | Calendário 2027 do DETRAN | ⚠️ **Antes de janeiro/2027.** Sem ele os vencimentos de 2027 ficam *estimados* pelo de 2026. Use *Copiar calendario* e confira cada final de placa no site do DETRAN |
| 4 | Honorários e taxas dos 14 serviços | Vêm zerados: toda O.S. sai com R$ 0,00 até ajustar |
| 5 | Importar clientes/veículos existentes | Levantar se há sistema ou planilha anterior; o Frappe tem *Data Import* nativo (CSV/XLSX) |
| 6 | OCR de CNH/CRLV/ATPV para preencher cadastro | Referências: `stackchain/ocr-cnh-2-json` (MPL-2.0), `gardim1/Leitor_De_CRLV`. Precisa de documentos reais de amostra para calibrar |
| 7 | RPA nos portais DETRAN/gov.br | Só com credenciamento oficial. Prova de conceito: `JConfessor/CRLV-Auto-Downloader` (MIT). **Não** usar scraping SINESP |
| 8 | App de campo para vistoria (fotos) | Frappe PWA / `frappe-ui` |
| ~~—~~ | ~~Financeiro, painel, portal do cliente~~ | **Feitos em 26/11/2026** (ver acima) |

## Decisões pendentes (precisam da DOM)

1. ~~Repositório público ou privado?~~ **Resolvido: público** (código MIT, sem segredo e sem dado pessoal). Build e clone não exigem credencial.
2. **SCR-BCB**: é serviço que a DOM pretende vender? Só é integrável via birô licenciado (Serasa/SPC/Quod) — o SCR do Banco Central é de acesso restrito a instituições autorizadas e ao titular. Definir antes de qualquer linha de código.
3. **WhatsApp**: Evolution API (não oficial, risco de banimento, grátis) ou Cloud API oficial da Meta (template aprovado, custo por conversa). A escolha afeta o volume de disparo permitido.
4. **Campo "login do gov.br" com alerta de 45 dias** (planilha): é alerta de senha/conta gov.br ou de validade da CNH? Hoje o sistema trata validade de CNH; senha gov.br nunca deve ser armazenada.
5. **LGPD (política)**: por quanto tempo guardar os dados de quem deixou de ser cliente; se os alertas de licenciamento, que oferecem serviço, precisam de consentimento prévio; e quem pode ver o **código de segurança da CNH** (hoje todo papel que lê Cliente vê). As ferramentas técnicas (oposição e anonimização) já existem.
6. **Aviso de andamento da O.S.**: ligar ou não, e em quais status (vem desligado).
7. **Consulta pública `/status-os` na internet**: hoje só funciona na rede do escritório. Publicar exige domínio + HTTPS e abrir a porta, e é uma decisão de segurança.

## Riscos conhecidos

- O envio real de WhatsApp nunca foi testado: depende de parear um celular. Evolution é API **não oficial**; risco de banimento do número em disparos em volume (ver decisão 3).
- No WSL, a distro desliga sozinha quando nenhum terminal está aberto e leva o Docker junto: nesse estado o sistema fica fora do ar e a rotina diária de alertas não roda. Serve para desenvolver, não para produção.
- O frappe_docker muda sem aviso (em 2026 trocou o jeito de passar o `apps.json` e o Python padrão). Se o build sair sem o `dom_despachante`, compare `images/custom/Containerfile` com `ops/scripts/build-imagem.sh`.
- Os 14 serviços semeados vêm com honorário e taxa zerados: ajuste os valores antes de abrir O.S. de verdade.
- Reiniciar o `backend` sem o `frontend` deixa o site em **502**, porque o nginx guarda o IP antigo. Os comandos do runbook já reiniciam os dois.
- O.S. e recebimentos de antes do financeiro: o campo *pago* era manual e agora é calculado pelos Recebimentos. Em produção ainda não existem dados antigos; se for importar O.S. já pagas, lance os recebimentos correspondentes.

## Testes

```bash
# num site SEPARADO (os testes criam e desfazem dados): ex. test.dom.local com allow_tests
docker compose --project-name dom exec backend bench --site test.dom.local set-config allow_tests true
docker compose --project-name dom exec backend bench --site test.dom.local run-tests --app dom_despachante
```

O GitHub Actions (`.github/workflows/ci.yml`) roda os mesmos testes em todo PR e push no `main`.
- Escritório pequeno, um site: sem multi-tenancy. Multi-empresa exigiria Frappe multisite.

## Como retomar o trabalho com o Claude

Abra o Claude Code na pasta do projeto e mande algo assim:

> "Projeto DOM Cristo Despachante. Leia `ops/ESTADO-E-PROXIMOS-PASSOS.md` e `ops/RUNBOOK-OUTRA-MAQUINA.md` no repositório `rafaelangelis/sistema_despachante`. Parei na etapa X, aconteceu Y. Quero continuar daí."

Se você levar apenas este repositório para outra máquina, o contexto necessário está todo aqui: o estado, as decisões, as pendências e os motivos. O histórico da conversa anterior não é necessário.

## Comandos de uso diário (depois de instalado)

```bash
# atualizar o sistema depois de mudança no código
cd ~/sistema_despachante && git pull
~/sistema_despachante/ops/scripts/build-imagem.sh ~/frappe_docker dom-erp:1.0.1
sed -i 's/^CUSTOM_TAG=.*/CUSTOM_TAG=1.0.1/' ~/frappe_docker/.env
cd ~/frappe_docker
docker compose --project-name dom up -d
docker compose --project-name dom exec backend bench --site despacho.dom.local migrate

# rodar os alertas na mão (teste)
docker compose --project-name dom exec backend bench --site despacho.dom.local \
  execute dom_despachante.tasks.enviar_alertas_licenciamento

# backup imediato
SITE=despacho.dom.local COMPOSE_DIR=~/frappe_docker ~/sistema_despachante/ops/scripts/backup.sh
```
