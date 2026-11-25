# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.model.document import Document

from dom_despachante.validadores import consulta_cnpj, so_digitos, valida_cnpj


class Empresa(Document):
	def validate(self):
		self.normalizar_campos()
		self.validar_cnpj()
		self.preencher_por_cnpj()

	def normalizar_campos(self):
		if self.razao_social:
			self.razao_social = self.razao_social.strip().upper()
		if self.cnpj:
			self.cnpj = so_digitos(self.cnpj)
		if self.cep:
			self.cep = so_digitos(self.cep)

	def validar_cnpj(self):
		if not self.cnpj:
			return
		if not valida_cnpj(self.cnpj):
			frappe.throw(_("CNPJ invalido: {0}").format(self.cnpj))
		duplicado = frappe.db.get_value(
			"Empresa", {"cnpj": self.cnpj, "name": ["!=", self.name or ""]}, "name"
		)
		if duplicado:
			frappe.throw(_("Ja existe a empresa {0} com este CNPJ.").format(duplicado))

	def preencher_por_cnpj(self):
		if not self.cnpj or self.razao_social:
			return
		if not frappe.db.get_single_value("Configuracao Despachante", "brasilapi_ativo"):
			return
		dados = consulta_cnpj(self.cnpj)
		if not dados:
			return
		self.razao_social = (dados.get("razao_social") or "").upper()
		self.nome_fantasia = dados.get("nome_fantasia") or self.nome_fantasia
		self.cep = so_digitos(dados.get("cep"))
		self.logradouro = dados.get("descricao_tipo_de_logradouro") or self.logradouro
		self.bairro = dados.get("bairro") or self.bairro
		self.cidade = dados.get("municipio") or self.cidade
		self.estado = dados.get("uf") or self.estado