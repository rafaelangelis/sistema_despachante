# -*- coding: utf-8 -*-
"""Recebimento do cliente referente a uma O.S.

Confirmavel (submit): so o recebimento confirmado entra no saldo da O.S.
Para corrigir, cancele e emende (amend) - nunca se apaga dinheiro recebido.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from dom_despachante.financeiro import atualizar_os, total_recebido


class Recebimento(Document):
	def validate(self):
		if not self.recebido_por:
			self.recebido_por = frappe.session.user
		if flt(self.valor) <= 0:
			frappe.throw(_("O valor recebido deve ser maior que zero."))
		os_ = frappe.db.get_value(
			"Ordem de Servico", self.ordem_de_servico, ["status", "total_geral", "cliente"], as_dict=True
		)
		if not os_:
			frappe.throw(_("Ordem de servico {0} nao encontrada.").format(self.ordem_de_servico))
		if os_.status == "Cancelada":
			frappe.throw(_("A O.S. {0} esta cancelada: nao recebe pagamento.").format(self.ordem_de_servico))
		self.cliente = os_.cliente
		saldo = flt(flt(os_.total_geral) - total_recebido(self.ordem_de_servico), 2)
		self.saldo_antes = saldo
		if flt(self.valor, 2) > saldo:
			frappe.throw(
				_("Valor maior que o saldo da O.S. ({0}). Confira os servicos da O.S. ou o valor digitado.").format(
					frappe.format_value(saldo, {"fieldtype": "Currency"})
				)
			)

	def on_submit(self):
		atualizar_os(self.ordem_de_servico)

	def on_cancel(self):
		atualizar_os(self.ordem_de_servico)
