# -*- coding: utf-8 -*-
"""Indicadores do painel (Number Cards do tipo Custom). Cada funcao devolve valor + rota filtrada."""

import frappe
from frappe.utils import add_days, flt, today

ABERTAS = ["Aberta", "Em andamento", "Aguardando orgao"]


def _card(valor, fieldtype, doctype, route_options=None):
	return {
		"value": valor,
		"fieldtype": fieldtype,
		"route": ["List", doctype],
		"route_options": route_options or {},
	}


def _permitido(doctype):
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(frappe._("Sem permissao para {0}").format(doctype), frappe.PermissionError)


@frappe.whitelist()
def os_em_aberto(filters=None):
	_permitido("Ordem de Servico")
	n = frappe.db.count("Ordem de Servico", {"status": ["in", ABERTAS]})
	return _card(n, "Int", "Ordem de Servico", {"status": ["in", ABERTAS]})


@frappe.whitelist()
def os_atrasadas(filters=None):
	_permitido("Ordem de Servico")
	filtros = {"status": ["in", ABERTAS], "prazo": ["<", today()]}
	return _card(frappe.db.count("Ordem de Servico", filtros), "Int", "Ordem de Servico", filtros)


@frappe.whitelist()
def licenciamentos_30_dias(filters=None):
	_permitido("Veiculo")
	filtros = {"data_vencimento_licenciamento": ["between", [today(), add_days(today(), 30)]]}
	return _card(frappe.db.count("Veiculo", filtros), "Int", "Veiculo", filtros)


@frappe.whitelist()
def cnh_30_dias(filters=None):
	_permitido("Cliente")
	filtros = {"cnh_validade": ["between", [today(), add_days(today(), 30)]], "status": "Ativo"}
	return _card(frappe.db.count("Cliente", filtros), "Int", "Cliente", filtros)


@frappe.whitelist()
def total_a_receber(filters=None):
	_permitido("Ordem de Servico")
	valor = frappe.db.sql(
		"select coalesce(sum(saldo), 0) from `tabOrdem de Servico` where status != 'Cancelada' and saldo > 0"
	)[0][0]
	return _card(flt(valor, 2), "Currency", "Ordem de Servico", {"saldo": [">", 0], "status": ["!=", "Cancelada"]})


@frappe.whitelist()
def recebido_hoje(filters=None):
	_permitido("Recebimento")
	valor = frappe.db.sql(
		"select coalesce(sum(valor), 0) from `tabRecebimento` where docstatus = 1 and data = %s", today()
	)[0][0]
	return _card(flt(valor, 2), "Currency", "Recebimento", {"data": today(), "docstatus": 1})
