# -*- coding: utf-8 -*-
"""Taxas de orgao (DETRAN etc.) lancadas nas O.S. e ainda nao pagas pelo despachante."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	linhas = dados(filters)
	total = sum(flt(l.valor_taxa) for l in linhas)
	recebido = sum(flt(l.valor_taxa) for l in linhas if l.status_pagamento == "Pago")
	resumo = [
		{"label": _("Taxas a pagar"), "value": total, "datatype": "Currency", "indicator": "orange"},
		{"label": _("Destas, de O.S. ja quitadas pelo cliente"), "value": recebido, "datatype": "Currency", "indicator": "red"},
	]
	return colunas(), linhas, None, None, resumo


def colunas():
	return [
		{"fieldname": "ordem_de_servico", "label": _("O.S."), "fieldtype": "Link", "options": "Ordem de Servico", "width": 140},
		{"fieldname": "nome_cliente", "label": _("Cliente"), "fieldtype": "Data", "width": 200},
		{"fieldname": "servico", "label": _("Servico"), "fieldtype": "Link", "options": "Servico", "width": 200},
		{"fieldname": "orgao", "label": _("Orgao"), "fieldtype": "Data", "width": 110},
		{"fieldname": "protocolo", "label": _("Protocolo"), "fieldtype": "Data", "width": 120},
		{"fieldname": "data_abertura", "label": _("Abertura da O.S."), "fieldtype": "Date", "width": 110},
		{"fieldname": "status_pagamento", "label": _("Cliente pagou?"), "fieldtype": "Data", "width": 110},
		{"fieldname": "valor_taxa", "label": _("Taxa"), "fieldtype": "Currency", "width": 110},
	]


def dados(filters):
	cond = ["os.status != 'Cancelada'", "item.taxa_paga = 0", "item.valor_taxa > 0", "item.status != 'Cancelado'"]
	if filters.get("orgao"):
		cond.append("item.orgao = %(orgao)s")
	return frappe.db.sql(
		f"""
		select os.name as ordem_de_servico, c.nome_completo as nome_cliente, item.servico, item.orgao,
			item.protocolo, os.data_abertura, os.status_pagamento,
			item.valor_taxa * coalesce(nullif(item.quantidade, 0), 1) as valor_taxa
		from `tabOS Servico` item
		join `tabOrdem de Servico` os on os.name = item.parent and item.parenttype = 'Ordem de Servico'
		left join `tabCliente` c on c.name = os.cliente
		where {" and ".join(cond)}
		order by os.data_abertura asc, os.name asc
		""",
		filters,
		as_dict=True,
	)
