# -*- coding: utf-8 -*-
"""Ferramentas LGPD: anonimizacao de cliente (direito de eliminacao do titular).

O que e apagado: dados pessoais do Cliente (nome, CPF, RG, contatos, CNH, gov.br,
endereco, observacoes), o historico de alteracoes dele (Version guarda os valores
antigos) e os comentarios. O que fica: O.S., recebimentos e veiculos (obrigacao
contabil/fiscal), agora apontando para "CLIENTE ANONIMIZADO".
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

CAMPOS_PESSOAIS = (
	"cpf", "rg", "orgao_emissor_rg", "data_nascimento", "email",
	"nivel_conta_govbr", "observacao_govbr",
	"cnh_numero", "cnh_categoria", "cnh_tipo", "cnh_validade", "cnh_primeira_habilitacao",
	"cnh_espelho", "cnh_codigo_seguranca", "cnh_orgao_emissor", "cnh_data_emissao",
	"cep", "logradouro", "numero", "complemento", "bairro", "cidade", "estado",
	"observacoes",
)


@frappe.whitelist()
def anonimizar_cliente(cliente, confirmacao=None):
	frappe.only_for("System Manager")
	if confirmacao != "ANONIMIZAR":
		frappe.throw(_("Digite ANONIMIZAR para confirmar. A operacao nao pode ser desfeita."))
	doc = frappe.get_doc("Cliente", cliente)
	if doc.anonimizado:
		frappe.throw(_("Este cliente ja foi anonimizado."))

	nome_anonimo = "CLIENTE ANONIMIZADO {0}".format(doc.name)
	meta = frappe.get_meta("Cliente")
	valores = {c: None for c in CAMPOS_PESSOAIS if meta.has_field(c)}
	if meta.has_field("tem_conta_gov_br"):
		valores["tem_conta_gov_br"] = 0
	valores.update(
		{
			"nome_completo": nome_anonimo,
			"status": "Inativo" if "Inativo" in (meta.get_field("status").options or "") else doc.status,
			"nao_enviar_whatsapp": 1,
			"anonimizado": 1,
			"data_anonimizacao": now_datetime(),
		}
	)
	# set_value direto: sem validate (CPF vazio) e sem gerar Version nova com os dados antigos
	frappe.db.set_value("Cliente", doc.name, valores, update_modified=True)
	frappe.db.delete("Telefone Cliente", {"parent": doc.name, "parenttype": "Cliente"})
	frappe.db.delete("Vinculo Empresa", {"parent": doc.name, "parenttype": "Cliente"})

	# historico campo a campo e comentarios guardam os valores antigos
	frappe.db.delete("Version", {"ref_doctype": "Cliente", "docname": doc.name})
	frappe.db.delete("Comment", {"reference_doctype": "Cliente", "reference_name": doc.name})

	# copias do nome em outros documentos
	frappe.db.sql("update `tabRecebimento` set nome_cliente = %s where cliente = %s", (nome_anonimo, doc.name))

	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Cliente",
			"reference_name": doc.name,
			"content": _("Dados pessoais anonimizados por {0} a pedido do titular (LGPD).").format(frappe.session.user),
		}
	).insert(ignore_permissions=True)
	return nome_anonimo
