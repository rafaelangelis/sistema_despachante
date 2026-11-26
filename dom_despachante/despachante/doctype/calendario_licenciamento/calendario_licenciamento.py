# -*- coding: utf-8 -*-
import frappe
from frappe.model.document import Document


class CalendarioLicenciamento(Document):
	def before_naming(self):
		# autoname = field:chave roda antes do validate, entao a chave precisa existir aqui
		self.definir_chave()

	def validate(self):
		self.definir_chave()
		if self.mes_limite and not (1 <= int(self.mes_limite) <= 12):
			frappe.throw("Mes limite deve estar entre 1 e 12.")

	def definir_chave(self):
		self.chave = "{0}-{1}-{2}-{3}".format(
			(self.uf or "").upper(),
			self.ano or "",
			"CAM" if "Caminh" in (self.grupo or "") else "AUT",
			self.final_placa or "",
		).replace(" ", "")
