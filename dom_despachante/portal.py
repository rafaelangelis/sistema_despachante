# -*- coding: utf-8 -*-
"""Consulta publica do andamento da O.S. (pagina /status-os).

Seguranca: exige numero da O.S. + CPF/CNPJ do titular, responde igual para "nao existe"
e "documento nao confere" (nao da para descobrir numeros de O.S.), limita tentativas por
IP e devolve so status, prazo e documentos pendentes (sem valores nem dados pessoais).
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import formatdate

from dom_despachante.notificacoes import SITUACAO
from dom_despachante.validadores import so_digitos

NAO_ENCONTRADA = _("Nao encontramos uma O.S. com esse numero e esse documento. Confira os dados ou fale com o despachante.")


def _documento_confere(os_, documento):
	doc = so_digitos(documento)
	if len(doc) not in (11, 14):
		return False
	if os_.cliente and frappe.db.get_value("Cliente", os_.cliente, "cpf") == doc:
		return True
	if os_.empresa and frappe.db.get_value("Empresa", os_.empresa, "cnpj") == doc:
		return True
	return False


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60 * 10)
def consultar_os(numero, documento):
	numero = (numero or "").strip().upper()
	os_ = frappe.db.get_value(
		"Ordem de Servico",
		numero,
		["name", "cliente", "empresa", "status", "categoria_servico", "prazo", "data_abertura", "data_conclusao", "veiculo"],
		as_dict=True,
	) if numero else None
	if not os_ or not _documento_confere(os_, documento):
		return {"encontrada": False, "mensagem": NAO_ENCONTRADA}

	pendentes = frappe.get_all(
		"OS Documento",
		# o que o cliente ainda precisa trazer: nao entregue ou reprovado
		filters={"parent": os_.name, "parenttype": "Ordem de Servico", "status": ["in", ["Pendente", "Reprovado"]]},
		pluck="documento",
		order_by="idx asc",
	)
	placa = frappe.db.get_value("Veiculo", os_.veiculo, "placa") if os_.veiculo else ""
	return {
		"encontrada": True,
		"numero": os_.name,
		"status": os_.status,
		"situacao": SITUACAO.get(os_.status, ""),
		"categoria": os_.categoria_servico,
		"placa": (placa[:3] + "-" + placa[3:]) if placa else "",
		"abertura": formatdate(os_.data_abertura, "dd/MM/yyyy") if os_.data_abertura else "",
		"prazo": formatdate(os_.prazo, "dd/MM/yyyy") if os_.prazo else "",
		"conclusao": formatdate(os_.data_conclusao, "dd/MM/yyyy") if os_.data_conclusao else "",
		"documentos_pendentes": pendentes if os_.status not in ("Concluida", "Entregue", "Cancelada") else [],
	}
