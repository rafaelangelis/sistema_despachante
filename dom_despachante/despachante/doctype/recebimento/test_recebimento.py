import frappe
from frappe.utils import getdate, nowdate

from dom_despachante.financeiro import valor_por_extenso
from dom_despachante.tests.utils import DomTestCase


def preparar_os(honorario=150, taxa=80, quantidade=2):
	frappe.db.set_single_value("Configuracao Despachante", "brasilapi_ativo", 0)
	if not frappe.db.exists("Servico", "FIN Transferencia"):
		frappe.get_doc(
			{"doctype": "Servico", "nome_servico": "FIN Transferencia", "categoria": "Veiculos", "orgao": "DETRAN-SP", "ativo": 1}
		).insert()
	cli = frappe.db.get_value("Cliente", {"cpf": "52998224725"}, "name") or frappe.get_doc(
		{
			"doctype": "Cliente",
			"nome_completo": "Pagador Teste",
			"cpf": "529.982.247-25",
			"telefones": [{"tipo": "Celular Principal", "numero": "11988887777", "whatsapp": 1}],
		}
	).insert().name
	return frappe.get_doc(
		{
			"doctype": "Ordem de Servico",
			"cliente": cli,
			"categoria_servico": "Veiculos",
			"servicos": [
				{"servico": "FIN Transferencia", "valor_honorario": honorario, "valor_taxa": taxa, "quantidade": quantidade}
			],
		}
	).insert()


def receber(os_name, valor, forma="PIX", submeter=True):
	rec = frappe.get_doc(
		{"doctype": "Recebimento", "ordem_de_servico": os_name, "valor": valor, "forma_pagamento": forma}
	).insert()
	if submeter:
		rec.submit()
	return rec


class TestRecebimento(DomTestCase):
	def test_os_nova_fica_pendente(self):
		o = preparar_os()
		self.assertEqual(o.total_geral, 460)
		self.assertEqual(o.saldo, 460)
		self.assertEqual(o.status_pagamento, "Pendente")
		self.assertFalse(o.pago)

	def test_parcial_e_quitacao(self):
		o = preparar_os()
		receber(o.name, 200)
		o.reload()
		self.assertEqual((o.valor_recebido, o.saldo, o.status_pagamento), (200, 260, "Parcial"))
		receber(o.name, 260, forma="Dinheiro")
		o.reload()
		self.assertEqual((o.saldo, o.status_pagamento, o.pago), (0, "Pago", 1))
		self.assertEqual(getdate(o.data_pagamento), getdate(nowdate()))

	def test_rascunho_nao_conta(self):
		o = preparar_os()
		receber(o.name, 100, submeter=False)
		o.reload()
		self.assertEqual(o.valor_recebido, 0)

	def test_cancelar_recebimento_reabre_saldo(self):
		o = preparar_os()
		rec = receber(o.name, 460)
		rec.cancel()
		o.reload()
		self.assertEqual((o.saldo, o.status_pagamento, o.pago), (460, "Pendente", 0))
		self.assertIsNone(o.data_pagamento)

	def test_nao_recebe_acima_do_saldo(self):
		o = preparar_os()
		receber(o.name, 400)
		with self.assertRaises(frappe.ValidationError):
			receber(o.name, 100)

	def test_valor_zero_ou_negativo(self):
		o = preparar_os()
		for valor in (0, -10):
			with self.assertRaises(frappe.ValidationError):
				receber(o.name, valor, submeter=False)

	def test_os_cancelada_nao_recebe(self):
		o = preparar_os()
		o.status = "Cancelada"
		o.save()
		with self.assertRaises(frappe.ValidationError):
			receber(o.name, 10, submeter=False)

	def test_nao_reduz_os_abaixo_do_recebido(self):
		o = preparar_os()
		receber(o.name, 300)
		o.reload()
		o.servicos[0].quantidade = 1  # total cairia para 230
		with self.assertRaises(frappe.ValidationError):
			o.save()

	def test_editar_os_recalcula_saldo(self):
		o = preparar_os()
		receber(o.name, 100)
		o.reload()
		o.servicos[0].quantidade = 3  # 690
		o.save()
		self.assertEqual((o.total_geral, o.valor_recebido, o.saldo), (690, 100, 590))

	def test_repasse_de_taxas(self):
		o = preparar_os()
		self.assertEqual((o.total_taxas_pagas, o.taxas_a_repassar), (0, 160))
		o.servicos[0].taxa_paga = 1
		o.save()
		self.assertEqual((o.total_taxas_pagas, o.taxas_a_repassar), (160, 0))
		self.assertEqual(getdate(o.servicos[0].data_taxa_paga), getdate(nowdate()))

	def test_relatorios(self):
		from dom_despachante.despachante.report.caixa_recebimentos.caixa_recebimentos import execute as caixa
		from dom_despachante.despachante.report.contas_a_receber.contas_a_receber import execute as contas
		from dom_despachante.despachante.report.taxas_a_repassar.taxas_a_repassar import execute as taxas

		o = preparar_os()
		receber(o.name, 100, forma="PIX")
		receber(o.name, 50, forma="Dinheiro")

		_, linhas, _, _, resumo = contas({"cliente": o.cliente})
		self.assertEqual([(l.ordem_de_servico, l.saldo) for l in linhas], [(o.name, 310)])
		self.assertEqual(linhas[0].whatsapp, "5511988887777")
		self.assertEqual(resumo[1]["value"], 310)

		_, linhas, _, grafico, resumo = caixa({"de": nowdate(), "ate": nowdate()})
		minhas = [l for l in linhas if l.ordem_de_servico == o.name]
		self.assertEqual(sum(l.valor for l in minhas), 150)
		formas = {r["label"]: r["value"] for r in resumo}
		self.assertGreaterEqual(formas["PIX"], 100)
		self.assertIsNotNone(grafico)

		_, linhas, _, _, _ = taxas({})
		self.assertIn((o.name, 160), [(l.ordem_de_servico, l.valor_taxa) for l in linhas])

	def test_recibo(self):
		o = preparar_os()
		rec = receber(o.name, 1234.56 if o.total_geral >= 1234.56 else 100)
		html = frappe.get_print("Recebimento", rec.name, print_format="recibo")
		self.assertIn("RECIBO", html)
		self.assertIn("PAGADOR TESTE", html)
		self.assertIn("cem reais", html)
		self.assertIn(rec.name, html)

	def test_valor_por_extenso(self):
		self.assertEqual(valor_por_extenso(1234.56), "mil duzentos e trinta e quatro reais e cinquenta e seis centavos")
		self.assertEqual(valor_por_extenso(1.01), "um real e um centavo")

	def test_atendente_confirma_mas_nao_cancela(self):
		self.assertTrue(frappe.has_permission("Recebimento", "submit", user=self._atendente()))
		self.assertFalse(frappe.has_permission("Recebimento", "cancel", user=self._atendente()))
		self.assertFalse(frappe.has_permission("Recebimento", "delete", user=self._atendente()))

	def _atendente(self):
		email = "atendente.fin@dom.local"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Fin", "send_welcome_email": 0, "roles": [{"role": "Atendente"}]}
			).insert(ignore_permissions=True)
		return email
