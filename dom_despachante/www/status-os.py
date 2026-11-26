import frappe

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.nome_empresa = frappe.db.get_single_value("Configuracao Despachante", "nome_empresa") or ""
	return context
