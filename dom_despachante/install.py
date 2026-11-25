# -*- coding: utf-8 -*-
"""Criacao de papeis e dados iniciais na instalacao do app."""

import frappe

ROLES = ("Despachante", "Atendente")

# Calendario de licenciamento 2026 (SP), conforme a planilha SISTEMA DOM.
# Ajuste/amplie em Calendario Licenciamento quando o DETRAN publicar o calendario do ano.
CALENDARIO_2026 = {
	"Caminhoes e Caminhoes-Tratores": {
		"1": (9, 30), "2": (9, 30), "3": (10, 31), "4": (10, 31), "5": (10, 31),
		"6": (11, 30), "7": (11, 30), "8": (11, 30), "9": (12, 31), "0": (12, 31),
	},
	"Automoveis, Motos, Utilitarios, Onibus e Reboques": {
		"1": (7, 31), "2": (7, 31), "3": (8, 31), "4": (8, 31), "5": (9, 30),
		"6": (9, 30), "7": (10, 31), "8": (10, 31), "9": (11, 30), "0": (12, 31),
	},
}

SERVICOS = [
	("Transferencia de propriedade", "Veiculos", "DETRAN-SP", 15),
	("Licenciamento anual", "Veiculos", "DETRAN-SP", 5),
	("Emplacamento / 1o emplacamento", "Veiculos", "DETRAN-SP", 10),
	("2a via de CRLV", "Veiculos", "DETRAN-SP", 5),
	("Baixa de veiculo", "Veiculos", "DETRAN-SP", 15),
	("Mudanca de municipio / UF", "Veiculos", "DETRAN-SP", 15),
	("Renovacao de CNH", "CNH", "DETRAN-SP", 20),
	("2a via de CNH", "CNH", "DETRAN-SP", 10),
	("Mudanca de categoria de CNH", "CNH", "DETRAN-SP", 30),
	("Recurso de multa", "Recurso de Multa", "DETRAN-SP", 30),
	("Indicacao de condutor infrator", "Recurso de Multa", "DETRAN-SP", 15),
	("Defesa previa / recurso de CNH", "Recurso de CNH", "DETRAN-SP", 30),
	("Regularizacao de embarcacao", "Nautico", "Marinha", 30),
	("Consulta SCR-BCB", "SCR-BCB", "Banco Central", 1),
]


def criar_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def before_migrate(*args, **kwargs):
	criar_roles()
	frappe.db.commit()


def after_install(*args, **kwargs):
	criar_roles()
	semear_calendario()
	semear_servicos()
	configurar_padroes()
	frappe.reload_doc("despachante", "print_format", "procuracao", force=True)
	frappe.db.commit()


def semear_calendario():
	if frappe.db.count("Calendario Licenciamento"):
		return
	for grupo, finais in CALENDARIO_2026.items():
		for final, (mes, dia) in finais.items():
			doc = frappe.get_doc(
				{
					"doctype": "Calendario Licenciamento",
					"uf": "SP",
					"ano": 2026,
					"grupo": grupo,
					"final_placa": final,
					"mes_limite": mes,
					"dia_limite": dia,
					"observacao": "Semente inicial - confira no site do DETRAN",
				}
			)
			doc.insert(ignore_permissions=True)


def semear_servicos():
	for nome, categoria, orgao, prazo in SERVICOS:
		if frappe.db.exists("Servico", nome):
			continue
		frappe.get_doc(
			{
				"doctype": "Servico",
				"nome_servico": nome,
				"categoria": categoria,
				"orgao": orgao,
				"prazo_dias": prazo,
				"ativo": 1,
			}
		).insert(ignore_permissions=True)


def configurar_padroes():
	config = frappe.get_single("Configuracao Despachante")
	if not config.nome_empresa:
		config.nome_empresa = "DOM CRISTO DESPACHANTE"
	config.modo_simulacao = 1
	config.save(ignore_permissions=True)