from unittest.mock import MagicMock, patch

import frappe

from dom_despachante import tasks
from dom_despachante.lgpd import anonimizar_cliente
from dom_despachante.tests.utils import DomTestCase


def cliente_completo(**extra):
	frappe.db.set_single_value("Configuracao Despachante", "brasilapi_ativo", 0)
	return frappe.get_doc(
		dict(
			{
				"doctype": "Cliente",
				"nome_completo": "Carlos Privado",
				"cpf": "111.444.777-35",
				"rg": "123456789",
				"email": "carlos@exemplo.com",
				"cnh_numero": "01234567890",
				"cnh_codigo_seguranca": "999",
				"logradouro": "Rua Secreta",
				"observacoes": "mora com a mae",
				"telefones": [{"tipo": "Celular Principal", "numero": "11955554444", "whatsapp": 1}],
			},
			**extra,
		)
	).insert()


class TestLGPD(DomTestCase):
	def test_oposicao_bloqueia_whatsapp_e_registra_data(self):
		c = cliente_completo(nao_enviar_whatsapp=1)
		self.assertIsNotNone(c.data_oposicao_whatsapp)
		numero, _ = tasks._telefone_whatsapp(c.name)
		self.assertEqual(numero, "")

	def test_oposicao_vale_para_alerta_de_licenciamento(self):
		cfg = frappe.get_single("Configuracao Despachante")
		cfg.update({"modo_simulacao": 0, "alertar_licenciamento": 1, "dias_alerta": "5",
			"webhook_url_alertas": "http://n8n:5678/webhook/alerta-dom"})
		cfg.save()
		c = cliente_completo(nao_enviar_whatsapp=1)
		v = frappe.get_doc(
			{"doctype": "Veiculo", "placa": "LGP1D00", "uf_emplacamento": "MG", "exercicio_licenciamento": 2030, "proprietario": c.name}
		).insert()
		frappe.db.set_value("Veiculo", v.name, "data_vencimento_licenciamento", "2030-06-06")
		with patch.object(tasks, "today", return_value="2030-06-01"), patch.object(frappe.db, "commit"), patch(
			"requests.post", return_value=MagicMock(status_code=200)
		) as post:
			tasks.enviar_alertas_licenciamento()
		post.assert_not_called()

	def test_anonimizar_apaga_dados_e_historico(self):
		c = cliente_completo()
		c.email = "novo@exemplo.com"
		c.save(ignore_version=False)  # gera Version com o e-mail antigo (em teste o Frappe pula por padrao)
		self.assertTrue(frappe.db.exists("Version", {"ref_doctype": "Cliente", "docname": c.name}))
		os_ = frappe.get_doc({"doctype": "Ordem de Servico", "cliente": c.name, "categoria_servico": "CNH"}).insert()

		with self.assertRaises(frappe.ValidationError):
			anonimizar_cliente(c.name, confirmacao="sim")
		anonimizar_cliente(c.name, confirmacao="ANONIMIZAR")

		c.reload()
		self.assertTrue(c.nome_completo.startswith("CLIENTE ANONIMIZADO"))
		for campo in ("cpf", "rg", "email", "cnh_numero", "cnh_codigo_seguranca", "logradouro", "observacoes"):
			self.assertFalse(c.get(campo), campo)
		self.assertEqual(len(c.telefones), 0)
		self.assertTrue(c.anonimizado)
		self.assertFalse(frappe.db.exists("Version", {"ref_doctype": "Cliente", "docname": c.name}))
		self.assertTrue(frappe.db.exists("Ordem de Servico", os_.name), "O.S. continua existindo")
		self.assertEqual(frappe.db.get_value("Ordem de Servico", os_.name, "cliente"), c.name)
		with self.assertRaises(frappe.ValidationError):
			anonimizar_cliente(c.name, confirmacao="ANONIMIZAR")

	def test_so_system_manager_anonimiza(self):
		c = cliente_completo()
		email = "despachante.lgpd@dom.local"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Lgpd", "send_welcome_email": 0, "roles": [{"role": "Despachante"}]}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		# frappe.only_for nao checa nada quando in_test esta ligado: desliga so aqui
		# (frappe._dict nao aceita patch.object, por isso o liga/desliga manual)
		frappe.local.flags.in_test = False
		try:
			with self.assertRaises(frappe.PermissionError):
				anonimizar_cliente(c.name, confirmacao="ANONIMIZAR")
		finally:
			frappe.local.flags.in_test = True
