import json

import frappe
from frappe.utils import add_days, today

from dom_despachante import painel
from dom_despachante.tests.utils import DomTestCase


class TestPainel(DomTestCase):
	def test_workspace_instalado_com_cards_e_graficos(self):
		ws = frappe.get_doc("Workspace", "Despachante")
		blocos = json.loads(ws.content)
		cards = [b["data"]["number_card_name"] for b in blocos if b["type"] == "number_card"]
		self.assertEqual(len(cards), 6)
		for nome in cards:
			self.assertTrue(frappe.db.exists("Number Card", nome), nome)
		for b in blocos:
			if b["type"] == "chart":
				self.assertTrue(frappe.db.exists("Dashboard Chart", b["data"]["chart_name"]))

	def test_todos_os_cards_respondem(self):
		for card in frappe.get_all("Number Card", filters={"module": "Despachante"}, fields=["name", "method"]):
			resultado = frappe.get_attr(card.method)()
			self.assertIn("value", resultado, card.name)
			self.assertEqual(resultado["route"][0], "List")

	def test_os_atrasada_e_licenciamento_proximo(self):
		frappe.db.set_single_value("Configuracao Despachante", "brasilapi_ativo", 0)
		cli = frappe.get_doc({"doctype": "Cliente", "nome_completo": "Painel", "cpf": "390.533.447-05"}).insert()
		antes = painel.os_atrasadas()["value"]
		frappe.get_doc(
			{
				"doctype": "Ordem de Servico",
				"cliente": cli.name,
				"categoria_servico": "CNH",
				"status": "Em andamento",
				"data_abertura": add_days(today(), -40),
				"prazo": add_days(today(), -1),
			}
		).insert()
		self.assertEqual(painel.os_atrasadas()["value"], antes + 1)

		v = frappe.get_doc({"doctype": "Veiculo", "placa": "PNL1A11", "uf_emplacamento": "SP"}).insert()
		antes = painel.licenciamentos_30_dias()["value"]
		frappe.db.set_value("Veiculo", v.name, "data_vencimento_licenciamento", add_days(today(), 10))
		self.assertEqual(painel.licenciamentos_30_dias()["value"], antes + 1)

	def test_atendente_ve_o_painel(self):
		email = "atendente.painel@dom.local"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Painel", "send_welcome_email": 0, "roles": [{"role": "Atendente"}]}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		for metodo in ("os_em_aberto", "os_atrasadas", "licenciamentos_30_dias", "cnh_30_dias", "total_a_receber", "recebido_hoje"):
			self.assertIn("value", getattr(painel, metodo)(), metodo)
		# cartao Custom so aparece para quem le o document_type dele: sem isso o Atendente via 0 cartoes
		from frappe.desk.desktop import get_desktop_page

		pagina = get_desktop_page(json.dumps({"name": "Despachante", "title": "Despachante", "public": 1}))
		self.assertEqual(len(pagina["number_cards"]["items"]), 6)
		atalhos = {s["label"] for s in pagina["shortcuts"]["items"]}
		self.assertIn("Nova O.S.", atalhos)
		self.assertNotIn("Caixa do dia", atalhos, "caixa e so do Despachante")

	def test_grafico_os_por_status(self):
		from frappe.desk.doctype.dashboard_chart.dashboard_chart import get as grafico

		frappe.db.set_single_value("Configuracao Despachante", "brasilapi_ativo", 0)
		cli = frappe.get_doc({"doctype": "Cliente", "nome_completo": "Grafico", "cpf": "111.444.777-35"}).insert()
		for status in ("Aberta", "Aberta", "Concluida"):
			frappe.get_doc(
				{"doctype": "Ordem de Servico", "cliente": cli.name, "categoria_servico": "CNH", "status": status}
			).insert()
		r = grafico(chart_name="O.S. por status", refresh=1)
		valores = dict(zip(r["labels"], r["datasets"][0]["values"]))
		self.assertGreaterEqual(valores.get("Aberta", 0), 2)
		self.assertGreaterEqual(valores.get("Concluida", 0), 1)
