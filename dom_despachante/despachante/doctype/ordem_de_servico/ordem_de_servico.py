# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate

CHECKLIST_PADRAO = {
	"Veiculos": [
		"RG e CPF do proprietario",
		"CNH do proprietario",
		"CRLV-e do veiculo",
		"Comprovante de residencia",
		"ATPV-e / CRV assinado",
	],
	"CNH": [
		"RG e CPF",
		"CNH atual",
		"Comprovante de residencia",
		"Exame medico / clinica credenciada",
	],
	"Recurso de Multa": [
		"Notificacao de autuacao",
		"CRLV",
		"CNH do condutor",
		"Comprovante de residencia",
		"Formulario de recurso",
	],
	"Recurso de CNH": [
		"Notificacao de suspensao/cassacao",
		"CNH",
		"RG e CPF",
		"Comprovante de residencia",
	],
	"Nautico": [
		"RG e CPF",
		"Comprovante de residencia",
		"Documento da embarcacao",
		"Comprovante de curso (NORMAM)",
	],
	"SCR-BCB": [
		"RG e CPF",
		"Consentimento do titular (LGPD)",
	],
	"Corretor": [
		"RG e CPF",
		"Documento do veiculo",
		"Apolice / vistoria quando aplicavel",
	],
}


class OrdemdeServico(Document):
	def validate(self):
		self.definir_responsavel()
		self.normalizar_itens()
		self.criar_checklist_padrao()
		self.calcular_totais()
		self.definir_prazos()
		self.definir_conclusao()
		self.formatar_data_abertura()

	def definir_responsavel(self):
		if not self.funcionario_responsavel:
			self.funcionario_responsavel = frappe.session.user
		if self.funcionario_responsavel and not self.matricula:
			self.matricula = frappe.db.get_value("User", self.funcionario_responsavel, "username") or ""

	def normalizar_itens(self):
		for item in self.servicos or []:
			if not item.quantidade:
				item.quantidade = 1
			if not item.status:
				item.status = "Pendente"

	def criar_checklist_padrao(self):
		if self.documentos or not self.categoria_servico:
			return
		for nome in CHECKLIST_PADRAO.get(self.categoria_servico, []):
			self.append("documentos", {"documento": nome, "obrigatorio": 1, "status": "Pendente"})

	def calcular_totais(self):
		honorarios = 0.0
		taxas = 0.0
		for item in self.servicos or []:
			qtd = item.quantidade or 1
			honorarios += (item.valor_honorario or 0) * qtd
			taxas += (item.valor_taxa or 0) * qtd
		self.total_honorarios = honorarios
		self.total_taxas = taxas
		self.total_geral = honorarios + taxas

	def definir_prazos(self):
		if not self.prazo:
			dias = 0
			for item in self.servicos or []:
				if item.servico:
					prazo_servico = frappe.db.get_value("Servico", item.servico, "prazo_dias") or 0
					dias = max(dias, prazo_servico)
			if dias:
				self.prazo = add_days(self.data_abertura or nowdate(), dias)

	def formatar_data_abertura(self):
		self.data_abertura_extenso = (
			getdate(self.data_abertura).strftime("%d/%m/%Y") if self.data_abertura else ""
		)

	def definir_conclusao(self):
		if self.status in ("Concluida", "Entregue") and not self.data_conclusao:
			self.data_conclusao = nowdate()
		if self.status not in ("Concluida", "Entregue"):
			self.data_conclusao = None


@frappe.whitelist()
def resumo_por_categoria(data=None):
	"""Alimenta o dashboard: O.S. abertas na data agrupadas por categoria."""
	data = data or nowdate()
	linhas = frappe.db.sql(
		"""
		select categoria_servico, count(*) as total
		from `tabOrdem de Servico`
		where status in ('Aberta', 'Em andamento', 'Aguardando orgao')
		  and date(data_abertura) <= %s
		group by categoria_servico
		order by total desc
		""",
		(getdate(data),),
		as_dict=True,
	)
	return linhas

# Compatibilidade de nome de classe: o Frappe deriva o nome da classe a partir do
# DocType ("Ordem de Servico"). Mantemos os apelidos para nao depender da regra exata.
OrdemDeServico = OrdemdeServico
OrdemServico = OrdemdeServico
Ordemdeservico = OrdemdeServico