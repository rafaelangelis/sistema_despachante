# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.model.document import Document


class CalendarioLicenciamento(Document):
	def before_naming(self):
		# autoname = field:chave roda antes do validate, entao a chave precisa existir aqui
		self.definir_chave()

	def validate(self):
		self.definir_chave()
		if self.mes_limite and not (1 <= int(self.mes_limite) <= 12):
			frappe.throw(_("Mes limite deve estar entre 1 e 12."))
		if self.dia_limite and not (1 <= int(self.dia_limite) <= 31):
			frappe.throw(_("Dia limite deve estar entre 1 e 31."))
		if self.final_placa is not None and str(self.final_placa).strip() not in [str(i) for i in range(10)]:
			frappe.throw(_("Final de placa deve ser um digito de 0 a 9."))
		self.final_placa = str(self.final_placa).strip()

	def definir_chave(self):
		self.chave = "{0}-{1}-{2}-{3}".format(
			(self.uf or "").upper(),
			self.ano or "",
			"CAM" if "Caminh" in (self.grupo or "") else "AUT",
			self.final_placa or "",
		).replace(" ", "")

	def on_update(self):
		recalcular_veiculos(self.uf, self.ano, self.final_placa)

	def on_trash(self):
		frappe.db.after_commit.add(lambda: recalcular_veiculos(self.uf, self.ano, self.final_placa))


def recalcular_veiculos(uf, ano, final_placa):
	"""Recalcula o vencimento dos veiculos afetados por uma regra do calendario."""
	from dom_despachante.despachante.doctype.veiculo.veiculo import calcular_vencimento, grupo_por_tipo

	veiculos = frappe.get_all(
		"Veiculo",
		filters={"uf_emplacamento": uf, "exercicio_licenciamento": int(ano or 0), "final_placa": str(final_placa)},
		fields=["name", "tipo_veiculo", "data_vencimento_licenciamento", "vencimento_estimado"],
	)
	alterados = 0
	for v in veiculos:
		data, estimado = calcular_vencimento(uf, ano, grupo_por_tipo(v.tipo_veiculo), final_placa)
		if not data:
			continue
		if str(v.data_vencimento_licenciamento or "") != data or int(v.vencimento_estimado or 0) != int(estimado):
			frappe.db.set_value(
				"Veiculo", v.name, {"data_vencimento_licenciamento": data, "vencimento_estimado": 1 if estimado else 0}
			)
			alterados += 1
	return alterados


@frappe.whitelist()
def copiar_calendario(uf, ano_origem, ano_destino):
	"""Copia as regras de um ano para outro (ponto de partida; confira depois no site do DETRAN)."""
	frappe.only_for(("System Manager", "Despachante"))
	ano_origem, ano_destino = int(ano_origem), int(ano_destino)
	regras = frappe.get_all(
		"Calendario Licenciamento",
		filters={"uf": uf, "ano": ano_origem},
		fields=["grupo", "final_placa", "mes_limite", "dia_limite"],
	)
	if not regras:
		frappe.throw(_("Nao ha calendario {0}/{1} para copiar.").format(uf, ano_origem))
	criadas = 0
	for r in regras:
		doc = frappe.get_doc(
			{
				"doctype": "Calendario Licenciamento",
				"uf": uf,
				"ano": ano_destino,
				"grupo": r.grupo,
				"final_placa": r.final_placa,
				"mes_limite": r.mes_limite,
				"dia_limite": r.dia_limite,
				"observacao": "Copiado de {0}/{1} - CONFIRA no site do DETRAN".format(uf, ano_origem),
			}
		)
		doc.definir_chave()
		if frappe.db.exists("Calendario Licenciamento", doc.chave):
			continue
		doc.insert()
		criadas += 1
	return criadas
