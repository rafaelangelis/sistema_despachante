# -*- coding: utf-8 -*-
"""Recebimentos confirmados no periodo, com totais por forma de pagamento (fechamento de caixa)."""

import frappe
from frappe import _
from frappe.utils import flt, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.de = filters.get("de") or today()
	filters.ate = filters.get("ate") or today()
	linhas = dados(filters)
	return colunas(), linhas, None, grafico(linhas), resumo(linhas)


def colunas():
	return [
		{"fieldname": "data", "label": _("Data"), "fieldtype": "Date", "width": 100},
		{"fieldname": "recebimento", "label": _("Recebimento"), "fieldtype": "Link", "options": "Recebimento", "width": 150},
		{"fieldname": "ordem_de_servico", "label": _("O.S."), "fieldtype": "Link", "options": "Ordem de Servico", "width": 140},
		{"fieldname": "nome_cliente", "label": _("Cliente"), "fieldtype": "Data", "width": 220},
		{"fieldname": "forma_pagamento", "label": _("Forma"), "fieldtype": "Data", "width": 140},
		{"fieldname": "recebido_por", "label": _("Recebido por"), "fieldtype": "Link", "options": "User", "width": 170},
		{"fieldname": "valor", "label": _("Valor"), "fieldtype": "Currency", "width": 120},
	]


def dados(filters):
	cond = ["docstatus = 1", "data between %(de)s and %(ate)s"]
	if filters.get("forma_pagamento"):
		cond.append("forma_pagamento = %(forma_pagamento)s")
	if filters.get("recebido_por"):
		cond.append("recebido_por = %(recebido_por)s")
	return frappe.db.sql(
		f"""
		select data, name as recebimento, ordem_de_servico, nome_cliente, forma_pagamento, recebido_por, valor
		from `tabRecebimento`
		where {" and ".join(cond)}
		order by data asc, creation asc
		""",
		filters,
		as_dict=True,
	)


def _por_forma(linhas):
	formas = {}
	for l in linhas:
		formas[l.forma_pagamento] = formas.get(l.forma_pagamento, 0) + flt(l.valor)
	return formas


def resumo(linhas):
	itens = [{"label": _("Total recebido"), "value": sum(flt(l.valor) for l in linhas), "datatype": "Currency", "indicator": "green"}]
	for forma, valor in sorted(_por_forma(linhas).items()):
		itens.append({"label": forma, "value": valor, "datatype": "Currency", "indicator": "blue"})
	return itens


def grafico(linhas):
	formas = _por_forma(linhas)
	if not formas:
		return None
	return {
		"data": {"labels": list(formas.keys()), "datasets": [{"name": _("Recebido"), "values": list(formas.values())}]},
		"type": "donut",
		"fieldtype": "Currency",
	}
