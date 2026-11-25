# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.model.document import Document

from dom_despachante.validadores import (
	consulta_cep,
	normaliza_telefone,
	so_digitos,
	valida_cpf,
)


class Cliente(Document):
	def validate(self):
		self.normalizar_campos()
		self.validar_cpf()
		self.preencher_endereco_por_cep()

	def normalizar_campos(self):
		if self.nome_completo:
			self.nome_completo = self.nome_completo.strip().upper()
		if self.cpf:
			self.cpf = so_digitos(self.cpf)
		if self.cep:
			self.cep = so_digitos(self.cep)
		if self.cnh_categoria:
			self.cnh_categoria = self.cnh_categoria.strip().upper()
		for tel in self.telefones or []:
			tel.numero = normaliza_telefone(tel.numero)
		# garante apenas um telefone principal / um whatsapp principal
		if self.telefones and not any(t.principal for t in self.telefones):
			self.telefones[0].principal = 1

	def validar_cpf(self):
		if not self.cpf:
			return
		if not valida_cpf(self.cpf):
			frappe.throw(_("CPF invalido: {0}").format(self.cpf))
		duplicado = frappe.db.get_value(
			"Cliente", {"cpf": self.cpf, "name": ["!=", self.name or ""]}, "name"
		)
		if duplicado:
			frappe.throw(_("Ja existe o cliente {0} com este CPF.").format(duplicado))

	def preencher_endereco_por_cep(self):
		if not self.cep or len(self.cep) != 8 or self.logradouro:
			return
		if not frappe.db.get_single_value("Configuracao Despachante", "brasilapi_ativo"):
			return
		dados = consulta_cep(self.cep)
		if not dados:
			return
		self.logradouro = dados.get("street") or self.logradouro
		self.bairro = dados.get("neighborhood") or self.bairro
		self.cidade = dados.get("city") or self.cidade
		self.estado = dados.get("state") or self.estado