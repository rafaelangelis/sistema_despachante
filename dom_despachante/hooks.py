app_name = "dom_despachante"
app_title = "DOM Despachante"
app_publisher = "DOM Cristo Despachante"
app_description = "Gestao de ordens de servico para despachante de veiculos, CNH, multas e nautico"
app_email = "ti@dom.local"
app_license = "MIT"
app_version = "0.0.1"

# Garante os papeis antes do sync dos DocTypes (para as permissoes colarem na 1a instalacao)
before_migrate = ["dom_despachante.install.before_migrate"]

after_install = "dom_despachante.install.after_install"

scheduler_events = {
	"daily": [
		"dom_despachante.tasks.enviar_alertas_licenciamento",
		"dom_despachante.tasks.enviar_alertas_cnh",
	]
}

# Exporta o historico de alteracoes por documento (campo a campo) - nativo do Frappe
track_changes = True