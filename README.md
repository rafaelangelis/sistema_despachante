# dom_despachante

App Frappe v15 com o sistema da DOM Cristo Despachante: clientes, empresas, veiculos,
catalogo de servicos, ordens de servico com checklist de documentos, calendario de
licenciamento por UF/ano e alertas diarios de vencimento (licenciamento e CNH) via webhook.

Instalacao (dentro de um bench):

    bench get-app dom_despachante https://github.com/SEU-USUARIO/dom_despachante
    bench --site SEU_SITE install-app dom_despachante

O guia de producao completo (Docker, Evolution API, n8n, backup) esta em ops/GUIA-PRODUCAO.md.