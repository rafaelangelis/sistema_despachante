# -*- coding: utf-8 -*-
"""O.S. com saldo a receber (inadimplencia), da mais antiga para a mais nova."""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return colunas(), dados(filters), None, None, resumo(filters)


def colunas():
	return [
		{"fieldname": "ordem_de_servico", "label": _("O.S."), "fieldtype": "Link", "options": "Ordem de Servico", "width": 140},
		{"fieldname": "cliente", "label": _("Cliente"), "fieldtype": "Link", "options": "Cliente", "width": 110},
		{"fieldname": "nome_cliente", "label": _("Nome"), "fieldtype": "Data", "width": 220},
		{"fieldname": "whatsapp", "label": _("WhatsApp"), "fieldtype": "Data", "width": 130},
		{"fieldname": "data_abertura", "label": _("Abertura"), "fieldtype": "Date", "width": 100},
		{"fieldname": "dias_em_aberto", "label": _("Dias em aberto"), "fieldtype": "Int", "width": 110},
		{"fieldname": "status", "label": _("Status da O.S."), "fieldtype": "Data", "width": 130},
		{"fieldname": "total_geral", "label": _("Total"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "valor_recebido", "label": _("Recebido"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "saldo", "label": _("Saldo"), "fieldtype": "Currency", "width": 110},
	]


def _condicoes(filters):
	cond = ["os.docstatus < 2", "os.status != 'Cancelada'", "os.saldo > 0"]
	valores = {}
	if filters.get("cliente"):
		cond.append("os.cliente = %(cliente)s")
		valores["cliente"] = filters.cliente
	if filters.get("ate_data"):
		cond.append("os.data_abertura <= %(ate_data)s")
		valores["ate_data"] = filters.ate_data
	if filters.get("min_dias"):
		cond.append("os.data_abertura <= %(limite)s")
		valores["limite"] = frappe.utils.add_days(today(), -int(filters.min_dias))
	return " and ".join(cond), valores


def dados(filters):
	cond, valores = _condicoes(filters)
	linhas = frappe.db.sql(
		f"""
		select os.name as ordem_de_servico, os.cliente, c.nome_completo as nome_cliente,
			os.data_abertura, os.status, os.total_geral, os.valor_recebido, os.saldo
		from `tabOrdem de Servico` os
		left join `tabCliente` c on c.name = os.cliente
		where {cond}
		order by os.data_abertura asc, os.name asc
		""",
		valores,
		as_dict=True,
	)
	hoje = getdate(today())
	for linha in linhas:
		linha.dias_em_aberto = date_diff(hoje, linha.data_abertura) if linha.data_abertura else None
		linha.whatsapp = _whatsapp(linha.cliente)
	return linhas


def _whatsapp(cliente):
	if not cliente:
		return ""
	tel = frappe.get_all(
		"Telefone Cliente",
		filters={"parent": cliente, "parenttype": "Cliente", "whatsapp": 1},
		fields=["numero", "principal"],
		order_by="principal desc",
		limit=1,
	)
	return tel[0].numero if tel else ""


def resumo(filters):
	linhas = dados(filters)
	total = sum(flt(l.saldo) for l in linhas)
	acima_30 = sum(flt(l.saldo) for l in linhas if (l.dias_em_aberto or 0) > 30)
	return [
		{"label": _("O.S. com saldo"), "value": len(linhas), "datatype": "Int", "indicator": "blue"},
		{"label": _("Total a receber"), "value": total, "datatype": "Currency", "indicator": "orange"},
		{"label": _("Em aberto ha mais de 30 dias"), "value": acima_30, "datatype": "Currency", "indicator": "red"},
	]
