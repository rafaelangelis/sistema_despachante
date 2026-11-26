import frappe
from frappe.desk.search import search_link

from dom_despachante.tests.utils import DomTestCase


def usuario(email, papel):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": papel,
				"send_welcome_email": 0,
				"user_type": "System User",
				"roles": [{"role": papel}],
			}
		).insert(ignore_permissions=True)
	return email


ATENDENTE = "atendente.teste@dom.local"
DESPACHANTE = "despachante.teste@dom.local"


class TestPermissoes(DomTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		usuario(ATENDENTE, "Atendente")
		usuario(DESPACHANTE, "Despachante")
		if not frappe.db.exists("Servico", "PERM Servico"):
			frappe.get_doc(
				{"doctype": "Servico", "nome_servico": "PERM Servico", "categoria": "Veiculos", "ativo": 1}
			).insert()
		frappe.db.commit()

	def pode(self, user, doctype, ptype):
		return frappe.has_permission(doctype, ptype, user=user)

	def test_atendente_opera_o_balcao(self):
		for dt in ("Cliente", "Empresa", "Veiculo", "Ordem de Servico"):
			for p in ("read", "create", "write", "print"):
				self.assertTrue(self.pode(ATENDENTE, dt, p), f"Atendente deveria ter {p} em {dt}")

	def test_atendente_escolhe_servico_e_responsavel_na_os(self):
		frappe.set_user(ATENDENTE)
		servicos = search_link("Servico", "PERM")
		self.assertTrue(any(r["value"] == "PERM Servico" for r in servicos), "Atendente nao acha o servico na O.S.")
		usuarios = search_link("User", "despachante.teste")
		self.assertTrue(any(r["value"] == DESPACHANTE for r in usuarios), "Atendente nao acha o responsavel")

	def test_atendente_nao_altera_cadastros_de_gestao(self):
		for dt in ("Servico", "Calendario Licenciamento", "Configuracao Despachante"):
			self.assertFalse(self.pode(ATENDENTE, dt, "write"), f"Atendente nao deveria editar {dt}")
		self.assertFalse(self.pode(ATENDENTE, "Servico", "create"))

	def test_atendente_nao_exporta_dados_pessoais_em_massa(self):
		for dt in ("Cliente", "Empresa", "Veiculo"):
			self.assertFalse(self.pode(ATENDENTE, dt, "export"), f"Atendente nao deveria exportar {dt} (LGPD)")

	def test_ninguem_alem_do_admin_apaga(self):
		for user in (ATENDENTE, DESPACHANTE):
			for dt in ("Cliente", "Veiculo", "Ordem de Servico"):
				self.assertFalse(self.pode(user, dt, "delete"), f"{user} nao deveria apagar {dt}")

	def test_despachante_gerencia(self):
		for dt in ("Servico", "Calendario Licenciamento", "Configuracao Despachante"):
			self.assertTrue(self.pode(DESPACHANTE, dt, "write"), f"Despachante deveria editar {dt}")
		for dt in ("Cliente", "Veiculo", "Ordem de Servico"):
			self.assertTrue(self.pode(DESPACHANTE, dt, "export"))

	def test_atendente_cria_os_completa(self):
		frappe.set_user(ATENDENTE)
		cli = frappe.get_doc({"doctype": "Cliente", "nome_completo": "Balcao", "cpf": "111.444.777-35"}).insert()
		os_ = frappe.get_doc(
			{
				"doctype": "Ordem de Servico",
				"cliente": cli.name,
				"categoria_servico": "Veiculos",
				"servicos": [{"servico": "PERM Servico", "valor_honorario": 100}],
			}
		).insert()
		self.assertEqual(os_.funcionario_responsavel, ATENDENTE)
		self.assertEqual(os_.total_geral, 100)
