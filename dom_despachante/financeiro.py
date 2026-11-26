# -*- coding: utf-8 -*-
"""Financeiro da O.S.: recebimentos do cliente e repasse das taxas ao orgao."""

import frappe
from frappe.utils import flt


def total_recebido(ordem_de_servico):
	"""Soma dos Recebimentos CONFIRMADOS (docstatus 1) da O.S."""
	valor = frappe.db.sql(
		"select coalesce(sum(valor), 0) from `tabRecebimento` where ordem_de_servico = %s and docstatus = 1",
		ordem_de_servico,
	)[0][0]
	return flt(valor, 2)


def situacao_pagamento(total, recebido):
	total, recebido = flt(total, 2), flt(recebido, 2)
	if total <= 0:
		return "Sem valor"
	if recebido <= 0:
		return "Pendente"
	if recebido < total:
		return "Parcial"
	return "Pago"


def aplicar_financeiro(doc, recebido=None):
	"""Preenche os campos financeiros de uma O.S. em memoria (usado no validate)."""
	if recebido is None:
		recebido = total_recebido(doc.name) if doc.name and not doc.is_new() else 0
	doc.valor_recebido = flt(recebido, 2)
	doc.saldo = flt(flt(doc.total_geral) - doc.valor_recebido, 2)
	doc.status_pagamento = situacao_pagamento(doc.total_geral, doc.valor_recebido)
	doc.pago = 1 if doc.status_pagamento == "Pago" else 0
	if doc.pago and not doc.data_pagamento:
		doc.data_pagamento = ultima_data_recebimento(doc.name) if doc.name else None
	if not doc.pago:
		doc.data_pagamento = None


def ultima_data_recebimento(ordem_de_servico):
	return frappe.db.sql(
		"select max(data) from `tabRecebimento` where ordem_de_servico = %s and docstatus = 1",
		ordem_de_servico,
	)[0][0]


def atualizar_os(ordem_de_servico):
	"""Recalcula e grava os campos financeiros da O.S. (chamado ao confirmar/cancelar Recebimento)."""
	doc = frappe.get_doc("Ordem de Servico", ordem_de_servico)
	aplicar_financeiro(doc)
	frappe.db.set_value(
		"Ordem de Servico",
		ordem_de_servico,
		{
			"valor_recebido": doc.valor_recebido,
			"saldo": doc.saldo,
			"status_pagamento": doc.status_pagamento,
			"pago": doc.pago,
			"data_pagamento": doc.data_pagamento,
		},
	)
	return doc


def valor_por_extenso(valor):
	"""1234.56 -> 'mil duzentos e trinta e quatro reais e cinquenta e seis centavos' (para o recibo)."""
	try:
		from num2words import num2words

		return num2words(flt(valor, 2), lang="pt_BR", to="currency").replace(",", "")
	except Exception:
		return ""
