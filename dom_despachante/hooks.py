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
		# enviar_alertas_licenciamento tambem chama a virada antes de calcular os alertas
		"dom_despachante.tasks.atualizar_exercicio_veiculos",
		"dom_despachante.tasks.enviar_alertas_licenciamento",
		"dom_despachante.tasks.enviar_alertas_cnh",
	],
	"weekly": [
		"dom_despachante.tasks.verificar_calendario_proximo_ano",
	],
}

# Exporta o historico de alteracoes por documento (campo a campo) - nativo do Frappe
track_changes = True