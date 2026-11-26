from unittest.mock import MagicMock, patch

import frappe
from dom_despachante.tests.utils import DomTestCase

from dom_despachante import tasks

HOJE = "2030-06-01"


def config(**valores):
	cfg = frappe.get_single("Configuracao Despachante")
	base = {
		"modo_simulacao": 1,
		"alertar_licenciamento": 1,
		"alertar_cnh": 1,
		"dias_alerta": "45,30,15,5",
		"webhook_url_alertas": "http://n8n:5678/webhook/alerta-dom",
		"brasilapi_ativo": 0,
	}
	base.update(valores)
	cfg.update(base)
	cfg.save(ignore_permissions=True)


def cliente_com_whatsapp(cpf, **extra):
	return frappe.get_doc(
		dict(
			{
				"doctype": "Cliente",
				"nome_completo": "joao alerta",
				"cpf": cpf,
				"telefones": [{"tipo": "Celular Principal", "numero": "11999998888", "whatsapp": 1}],
			},
			**extra,
		)
	).insert()


def veiculo_vencendo(cliente, placa, vencimento):
	v = frappe.get_doc(
		{"doctype": "Veiculo", "placa": placa, "uf_emplacamento": "PR", "exercicio_licenciamento": 2030, "proprietario": cliente}
	).insert()
	frappe.db.set_value("Veiculo", v.name, "data_vencimento_licenciamento", vencimento)
	return v


class TestAlertas(DomTestCase):
	def setUp(self):
		self.patches = [
			patch.object(tasks, "today", return_value=HOJE),
			patch.object(frappe.db, "commit"),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in self.patches:
			p.stop()
		super().tearDown()

	def test_antecedencias(self):
		config(dias_alerta="30; 5, x, 45")
		self.assertEqual(tasks._antecedencias(), [5, 30, 45])
		config(dias_alerta="")
		self.assertEqual(tasks._antecedencias(), [5, 15, 30, 45])

	def test_simulacao_nao_chama_webhook(self):
		config(modo_simulacao=1)
		c = cliente_com_whatsapp("529.982.247-25")
		v = veiculo_vencendo(c.name, "BBB1B21", "2030-06-06")  # hoje + 5
		with patch("requests.post") as post:
			tasks.enviar_alertas_licenciamento()
		post.assert_not_called()
		self.assertIn("5d -> simulado", frappe.db.get_value("Veiculo", v.name, "alerta_enviado_em"))

	def test_envio_real_chama_webhook_e_registra_status(self):
		config(modo_simulacao=0)
		c = cliente_com_whatsapp("390.533.447-05")
		v = veiculo_vencendo(c.name, "BBB1B22", "2030-07-01")  # hoje + 30
		resposta = MagicMock(status_code=500)
		with patch("requests.post", return_value=resposta) as post:
			tasks.enviar_alertas_licenciamento()
		post.assert_called_once()
		payload = post.call_args.kwargs["json"]
		self.assertEqual(payload["cliente"], "5511999998888")
		self.assertIn("BBB1B22", payload["mensagem"])
		self.assertIn("30", payload["mensagem"])
		self.assertIn("30d -> http_500", frappe.db.get_value("Veiculo", v.name, "alerta_enviado_em"))

	def test_fora_da_antecedencia_nao_alerta(self):
		config(modo_simulacao=0)
		c = cliente_com_whatsapp("111.444.777-35")
		veiculo_vencendo(c.name, "BBB1B23", "2030-06-08")  # hoje + 7
		with patch("requests.post") as post:
			tasks.enviar_alertas_licenciamento()
		post.assert_not_called()

	def test_alerta_cnh(self):
		config(modo_simulacao=0)
		cliente_com_whatsapp("714.602.380-01", cnh_validade="2030-06-16", status="Ativo")  # hoje + 15
		with patch("requests.post", return_value=MagicMock(status_code=200)) as post:
			tasks.enviar_alertas_cnh()
		post.assert_called_once()
		self.assertIn("CNH", post.call_args.kwargs["json"]["mensagem"])

	def test_aviso_calendario_proximo_ano(self):
		frappe.get_doc(
			{"doctype": "Veiculo", "placa": "BBB1B24", "uf_emplacamento": "PE", "exercicio_licenciamento": 2030}
		).insert()
		with patch.object(tasks, "today", return_value="2030-11-10"):
			faltando = tasks.verificar_calendario_proximo_ano()
		self.assertIn("PE", faltando)
		self.assertTrue(
			frappe.db.exists("Notification Log", {"subject": ["like", "%calendario de licenciamento 2031%PE%"]})
		)
		with patch.object(tasks, "today", return_value="2030-06-10"):
			self.assertEqual(tasks.verificar_calendario_proximo_ano(), [], "antes de novembro nao avisa")
