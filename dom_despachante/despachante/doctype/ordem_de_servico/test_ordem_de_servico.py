import frappe
from dom_despachante.tests.utils import DomTestCase
from frappe.utils import add_days, getdate, nowdate


def servico(nome, honorario=0, taxa=0, prazo=10, categoria="Veiculos"):
	if frappe.db.exists("Servico", nome):
		frappe.delete_doc("Servico", nome, force=True)
	return frappe.get_doc(
		{
			"doctype": "Servico",
			"nome_servico": nome,
			"categoria": categoria,
			"orgao": "DETRAN-SP",
			"prazo_dias": prazo,
			"valor_honorario": honorario,
			"valor_taxa": taxa,
			"ativo": 1,
		}
	).insert()


def cliente():
	nome = frappe.db.get_value("Cliente", {"cpf": "39053344705"}, "name")
	if nome:
		return frappe.get_doc("Cliente", nome)
	frappe.db.set_single_value("Configuracao Despachante", "brasilapi_ativo", 0)
	return frappe.get_doc({"doctype": "Cliente", "nome_completo": "Cliente OS", "cpf": "390.533.447-05"}).insert()


def os_(itens, categoria="Veiculos", **extra):
	return frappe.get_doc(
		dict(
			{"doctype": "Ordem de Servico", "cliente": cliente().name, "categoria_servico": categoria, "servicos": itens},
			**extra,
		)
	).insert()


class TestOrdemDeServico(DomTestCase):
	def test_totais_respeitam_valor_digitado(self):
		servico("TST Transferencia", honorario=0, taxa=0)
		o = os_([{"servico": "TST Transferencia", "valor_honorario": 150, "valor_taxa": 80, "quantidade": 2}])
		self.assertEqual(o.total_honorarios, 300)
		self.assertEqual(o.total_taxas, 160)
		self.assertEqual(o.total_geral, 460)

	def test_valor_vazio_puxa_do_catalogo(self):
		servico("TST Licenciamento", honorario=120, taxa=160.5)
		o = os_([{"servico": "TST Licenciamento"}])
		self.assertEqual(o.servicos[0].valor_honorario, 120)
		self.assertEqual(o.servicos[0].quantidade, 1)
		self.assertEqual(o.total_geral, 280.5)

	def test_checklist_padrao_por_categoria(self):
		servico("TST CNH", categoria="CNH")
		o = os_([{"servico": "TST CNH"}], categoria="CNH")
		self.assertEqual(len(o.documentos), 4)
		self.assertTrue(all(d.status == "Pendente" for d in o.documentos))

	def test_prazo_pelo_maior_servico(self):
		servico("TST Rapido", prazo=5)
		servico("TST Lento", prazo=30)
		o = os_([{"servico": "TST Rapido"}, {"servico": "TST Lento"}], data_abertura=nowdate())
		self.assertEqual(getdate(o.prazo), getdate(add_days(nowdate(), 30)))

	def test_data_conclusao_acompanha_status(self):
		servico("TST Status")
		o = os_([{"servico": "TST Status"}])
		o.status = "Concluida"
		o.save()
		self.assertEqual(getdate(o.data_conclusao), getdate(nowdate()))
		o.status = "Em andamento"
		o.save()
		self.assertIsNone(o.data_conclusao)

	def test_procuracao_renderiza(self):
		servico("TST Procuracao")
		o = os_([{"servico": "TST Procuracao"}])
		html = frappe.get_print("Ordem de Servico", o.name, print_format="procuracao")
		self.assertIn("CLIENTE OS", html)
