import frappe
from dom_despachante.tests.utils import DomTestCase


def cliente(cpf="529.982.247-25", **extra):
	return frappe.get_doc(dict({"doctype": "Cliente", "nome_completo": "  maria teste ", "cpf": cpf}, **extra)).insert()


class TestCliente(DomTestCase):
	def setUp(self):
		frappe.db.set_single_value("Configuracao Despachante", "brasilapi_ativo", 0)

	def test_normaliza_nome_e_cpf(self):
		c = cliente()
		self.assertEqual(c.nome_completo, "MARIA TESTE")
		self.assertEqual(c.cpf, "52998224725")

	def test_cpf_invalido(self):
		with self.assertRaises(frappe.ValidationError):
			cliente("111.111.111-11")

	def test_cpf_duplicado(self):
		cliente()
		with self.assertRaises(frappe.ValidationError):
			cliente("52998224725")

	def test_telefone_normalizado_e_principal_padrao(self):
		c = cliente(
			telefones=[
				{"tipo": "Celular Principal", "numero": "(11) 99999-8888", "whatsapp": 1},
				{"tipo": "Recado", "numero": "11 3333-4444"},
			]
		)
		self.assertEqual(c.telefones[0].numero, "5511999998888")
		self.assertEqual(c.telefones[0].principal, 1, "sem principal marcado, o primeiro vira principal")
		self.assertEqual(c.telefones[1].principal, 0)
