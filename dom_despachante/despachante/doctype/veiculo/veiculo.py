# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

from dom_despachante.validadores import (
	so_digitos,
	valida_chassi,
	valida_placa,
	valida_renavam,
)

GRUPO_CAMINHOES = "Caminhoes e Caminhoes-Tratores"
GRUPO_LEVES = "Automoveis, Motos, Utilitarios, Onibus e Reboques"
TIPOS_CAMINHAO = ("CAMINHAO", "CAMINHAO-TRATOR")


class Veiculo(Document):
	def validate(self):
		self.normalizar_campos()
		self.validar_placa()
		self.definir_exercicio()
		self.definir_vencimento_licenciamento()

	def normalizar_campos(self):
		if self.placa:
			self.placa = self.placa.replace("-", "").replace(" ", "").upper()
		if self.chassi:
			self.chassi = self.chassi.upper()
		if self.renavam:
			self.renavam = so_digitos(self.renavam)
		if self.tipo_veiculo:
			self.tipo_veiculo = self.tipo_veiculo.strip().upper()
		self.final_placa = self.placa[-1] if self.placa else ""

	def validar_placa(self):
		if not self.placa:
			frappe.throw(_("Placa e obrigatoria."))
		if not valida_placa(self.placa):
			frappe.throw(_("Placa invalida: {0}").format(self.placa))
		if self.chassi and not valida_chassi(self.chassi):
			frappe.throw(_("Chassi invalido (17 caracteres, sem I, O, Q)."))
		if self.renavam and not valida_renavam(self.renavam):
			frappe.throw(_("RENAVAM deve ter 11 digitos."))

	def definir_exercicio(self):
		if not self.exercicio_licenciamento:
			self.exercicio_licenciamento = int((nowdate() or "2026")[:4])

	def grupo_licenciamento(self):
		if (self.tipo_veiculo or "").upper() in TIPOS_CAMINHAO:
			return GRUPO_CAMINHOES
		return GRUPO_LEVES

	def definir_vencimento_licenciamento(self):
		"""Calcula o vencimento a partir da tabela Calendario Licenciamento (UF + ano + grupo + final)."""
		if not (self.uf_emplacamento and self.exercicio_licenciamento and self.final_placa):
			return
		regra = frappe.db.get_value(
			"Calendario Licenciamento",
			{
				"uf": self.uf_emplacamento,
				"ano": self.exercicio_licenciamento,
				"grupo": self.grupo_licenciamento(),
				"final_placa": self.final_placa,
			},
			["mes_limite", "dia_limite"],
			as_dict=True,
		)
		if regra and regra.mes_limite and regra.dia_limite:
			self.data_vencimento_licenciamento = "{0}-{1:02d}-{2:02d}".format(
				int(self.exercicio_licenciamento), int(regra.mes_limite), int(regra.dia_limite)
			)
		else:
			frappe.msgprint(
				_("Sem regra de licenciamento para {0}/{1}/{2}/{3}. Cadastre em Calendario Licenciamento.").format(
					self.uf_emplacamento, self.exercicio_licenciamento, self.grupo_licenciamento(), self.final_placa
				),
				indicator="orange",
				alert=True,
			)