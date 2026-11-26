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
		return grupo_por_tipo(self.tipo_veiculo)

	def definir_vencimento_licenciamento(self, avisar=True):
		"""Calcula o vencimento pela tabela Calendario Licenciamento (UF + ano + grupo + final).

		Sem calendario do ano, usa o do ano mais recente anterior (mesmo dia/mes) e marca
		vencimento_estimado; quando o calendario oficial e cadastrado, CalendarioLicenciamento
		recalcula os veiculos afetados.
		"""
		if not (self.uf_emplacamento and self.exercicio_licenciamento and self.final_placa):
			return
		data, estimado = calcular_vencimento(
			self.uf_emplacamento, self.exercicio_licenciamento, self.grupo_licenciamento(), self.final_placa
		)
		if data:
			self.data_vencimento_licenciamento = data
			self.vencimento_estimado = 1 if estimado else 0
			if estimado and avisar:
				frappe.msgprint(
					_("Ainda nao ha calendario de licenciamento {0}/{1}: vencimento estimado pelo calendario anterior. Cadastre o calendario oficial em Calendario Licenciamento.").format(
						self.uf_emplacamento, self.exercicio_licenciamento
					),
					indicator="orange",
					alert=True,
				)
		elif avisar:
			frappe.msgprint(
				_("Sem regra de licenciamento para {0}/{1}/{2}/{3}. Cadastre em Calendario Licenciamento.").format(
					self.uf_emplacamento, self.exercicio_licenciamento, self.grupo_licenciamento(), self.final_placa
				),
				indicator="orange",
				alert=True,
			)


def grupo_por_tipo(tipo_veiculo):
	return GRUPO_CAMINHOES if (tipo_veiculo or "").strip().upper() in TIPOS_CAMINHAO else GRUPO_LEVES


def _montar_data(ano, mes, dia):
	"""Data ISO; 29/02 em ano nao bissexto vira 28/02."""
	import calendar

	ano, mes, dia = int(ano), int(mes), int(dia)
	dia = min(dia, calendar.monthrange(ano, mes)[1])
	return "{0}-{1:02d}-{2:02d}".format(ano, mes, dia)


def calcular_vencimento(uf, ano, grupo, final_placa):
	"""Retorna (data_iso, estimado). (None, False) se nao houver regra nem no ano nem antes."""
	filtros = {"uf": uf, "grupo": grupo, "final_placa": str(final_placa)}
	regra = frappe.db.get_value(
		"Calendario Licenciamento", dict(filtros, ano=int(ano)), ["mes_limite", "dia_limite"], as_dict=True
	)
	if regra and regra.mes_limite and regra.dia_limite:
		return _montar_data(ano, regra.mes_limite, regra.dia_limite), False
	anteriores = frappe.get_all(
		"Calendario Licenciamento",
		filters=dict(filtros, ano=["<", int(ano)]),
		fields=["mes_limite", "dia_limite"],
		order_by="ano desc",
		limit=1,
	)
	if anteriores and anteriores[0].mes_limite and anteriores[0].dia_limite:
		return _montar_data(ano, anteriores[0].mes_limite, anteriores[0].dia_limite), True
	return None, False