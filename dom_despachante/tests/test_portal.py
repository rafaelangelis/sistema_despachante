import frappe

from dom_despachante.portal import NAO_ENCONTRADA, consultar_os
from dom_despachante.tests.utils import DomTestCase


def preparar():
	frappe.db.set_single_value("Configuracao Despachante", "brasilapi_ativo", 0)
	cli = frappe.get_doc({"doctype": "Cliente", "nome_completo": "Portal Teste", "cpf": "529.982.247-25"}).insert()
	emp = frappe.get_doc({"doctype": "Empresa", "razao_social": "Empresa Portal", "cnpj": "11.222.333/0001-81"}).insert()
	v = frappe.get_doc({"doctype": "Veiculo", "placa": "PTL1A23", "uf_emplacamento": "SP"}).insert()
	o = frappe.get_doc(
		{"doctype": "Ordem de Servico", "cliente": cli.name, "empresa": emp.name, "veiculo": v.name,
		 "categoria_servico": "Veiculos", "status": "Aguardando orgao"}
	).insert()
	return o


class TestPortal(DomTestCase):
	def test_consulta_com_cpf(self):
		o = preparar()
		r = consultar_os(o.name.lower(), "529.982.247-25")
		self.assertTrue(r["encontrada"])
		self.assertEqual(r["status"], "Aguardando orgao")
		self.assertEqual(r["placa"], "PTL-1A23")
		self.assertEqual(len(r["documentos_pendentes"]), 5, "checklist padrao de Veiculos ainda pendente")

	def test_consulta_com_cnpj_da_empresa(self):
		o = preparar()
		self.assertTrue(consultar_os(o.name, "11222333000181")["encontrada"])

	def test_documento_errado_e_os_inexistente_respondem_igual(self):
		o = preparar()
		errado = consultar_os(o.name, "390.533.447-05")
		inexistente = consultar_os("OS-2099-99999", "529.982.247-25")
		vazio = consultar_os("", "")
		self.assertEqual(errado, {"encontrada": False, "mensagem": NAO_ENCONTRADA})
		self.assertEqual(errado, inexistente)
		self.assertEqual(errado, vazio)

	def test_nao_expoe_valores_nem_dados_pessoais(self):
		o = preparar()
		r = consultar_os(o.name, "52998224725")
		texto = frappe.as_json(r).lower()
		for proibido in ("portal teste", "52998224725", "total", "saldo", "valor", "empresa portal"):
			self.assertNotIn(proibido, texto, proibido)

	def test_documentos_entregues_saem_da_lista(self):
		o = preparar()
		for d in o.documentos[:3]:
			d.status = "Recebido"
		o.documentos[3].status = "Reprovado"
		o.save()
		r = consultar_os(o.name, "52998224725")
		self.assertEqual(len(r["documentos_pendentes"]), 2, "fica o pendente e o reprovado")

	def test_concluida_nao_lista_pendencias(self):
		o = preparar()
		o.status = "Concluida"
		o.save()
		self.assertEqual(consultar_os(o.name, "52998224725")["documentos_pendentes"], [])

	def test_pagina_publica_renderiza(self):
		from frappe.website.serve import get_response_content

		frappe.set_user("Guest")
		html = get_response_content("status-os")
		self.assertIn("Acompanhe sua ordem de servico", html)
		self.assertIn("dom_despachante.portal.consultar_os", html)
