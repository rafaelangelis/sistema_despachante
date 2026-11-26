# dom_despachante

App **Frappe v15** com o sistema da DOM Cristo Despachante.

- **Cadastros**: clientes (CPF validado, CEP pela BrasilAPI), empresas (CNPJ pela BrasilAPI), veículos (placa Mercosul, RENAVAM, chassi).
- **Ordens de serviço**: catálogo de serviços, checklist de documentos automático por categoria, prazos e procuração em PDF.
- **Licenciamento**: calendário por UF/ano/final de placa, vencimento calculado (ou *estimado* quando falta o calendário do ano), virada anual automática do exercício.
- **Alertas** de licenciamento e CNH (45/30/15/5 dias) e **aviso de andamento da O.S.** pelo WhatsApp (webhook → n8n → Evolution API), com modo simulação.
- **Financeiro**: recebimentos (PIX, dinheiro, cartão...), saldo da O.S., repasse de taxas ao órgão, relatórios *Contas a Receber*, *Caixa Recebimentos* e *Taxas a Repassar*, e recibo com valor por extenso.
- **Painel** *Despachante* com indicadores e gráficos.
- **Consulta pública** `/status-os`: o cliente acompanha a O.S. com o número + CPF/CNPJ.
- **LGPD**: oposição a mensagens e anonimização de cliente.
- **Papéis**: `Despachante` (gestão) e `Atendente` (balcão).

## Instalação

Produção com Docker (frappe_docker), passo a passo testado: **[ops/RUNBOOK-OUTRA-MAQUINA.md](ops/RUNBOOK-OUTRA-MAQUINA.md)**. O apêndice cobre rodar no WSL do Windows.

Num bench já existente:

    bench get-app dom_despachante https://github.com/rafaelangelis/sistema_despachante
    bench --site SEU_SITE install-app dom_despachante

Estado do projeto, decisões e próximos passos: [ops/ESTADO-E-PROXIMOS-PASSOS.md](ops/ESTADO-E-PROXIMOS-PASSOS.md).
Referência técnica: [ops/GUIA-PRODUCAO.md](ops/GUIA-PRODUCAO.md).

## Testes

    bench --site SITE_DE_TESTE set-config allow_tests true
    bench --site SITE_DE_TESTE run-tests --app dom_despachante

Use um site separado: os testes criam e desfazem dados. O GitHub Actions roda a suíte em todo pull request.
