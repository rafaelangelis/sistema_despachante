from unittest.mock import MagicMock, patch

import frappe

from dom_despachante.tests.utils import DomTestCase


def configurar(**valores):
	cfg = frappe.get_single("Configuracao Despachante")
	cfg.update(
		dict(
			{
				"notificar_status_os": 1,
				"status_notificados": "Aguardando orgao\nConcluida",
				"modo_simulacao": 0,
				"webhook_url_alertas": "http://n8n:5678/webhook/alerta-dom",
				"brasilapi_ativo": 0,
				"texto_status_os": "",
			},
			**valores,
		)
	)
	cfg.save(ignore_permissions=True)


def nova_os(com_whatsapp=True, placa=None):
	tel = [{"tipo": "Celular Principal", "numero": "11977776666", "whatsapp": 1}] if com_whatsapp else []
	cli = frappe.get_doc(
		{"doctype": "Cliente", "nome_completo": "ana souza", "cpf": "529.982.247-25", "telefones": tel}
	).insert()
	veiculo = None
	if placa:
		veiculo = frappe.get_doc({"doctype": "Veiculo", "placa": placa, "uf_emplacamento": "SP"}).insert().name
	return frappe.get_doc(
		{"doctype": "Ordem de Servico", "cliente": cli.name, "categoria_servico": "Veiculos", "veiculo": veiculo}
	).insert()


class TestAvisoStatus(DomTestCase):
	def mudar(self, o, status):
		o.status = status
		with patch("requests.post", return_value=MagicMock(status_code=200)) as post:
			o.save()
		return post

	def test_avisa_quando_conclui(self):
		configurar()
		o = nova_os(placa="NTF1A23")
		post = self.mudar(o, "Concluida")
		post.assert_called_once()
		corpo = post.call_args.kwargs["json"]
		self.assertEqual(corpo["cliente"], "5511977776666")
		self.assertIn("Ana", corpo["mensagem"])
		self.assertIn(o.name, corpo["mensagem"])
		self.assertIn("placa NTF1A23", corpo["mensagem"])
		self.assertIn("pronta", corpo["mensagem"])
		self.assertIn("Concluida -> http_200", frappe.db.get_value("Ordem de Servico", o.name, "avisos_enviados"))

	def test_status_fora_da_lista_nao_avisa(self):
		configurar()
		o = nova_os()
		self.mudar(o, "Em andamento").assert_not_called()

	def test_desligado_nao_avisa(self):
		configurar(notificar_status_os=0)
		o = nova_os()
		self.mudar(o, "Concluida").assert_not_called()

	def test_salvar_sem_mudar_status_nao_repete(self):
		configurar()
		o = nova_os()
		self.mudar(o, "Concluida").assert_called_once()
		o.reload()
		o.observacoes = "so uma anotacao"
		self.mudar(o, "Concluida").assert_not_called()

	def test_criar_os_nao_avisa(self):
		configurar(status_notificados="Aberta")
		with patch("requests.post") as post:
			nova_os()
		post.assert_not_called()

	def test_simulacao_registra_sem_enviar(self):
		configurar(modo_simulacao=1)
		o = nova_os()
		self.mudar(o, "Aguardando orgao").assert_not_called()
		self.assertIn("-> simulado", frappe.db.get_value("Ordem de Servico", o.name, "avisos_enviados"))

	def test_cliente_sem_whatsapp(self):
		configurar()
		o = nova_os(com_whatsapp=False)
		self.mudar(o, "Concluida").assert_not_called()
		self.assertIn("sem_whatsapp", frappe.db.get_value("Ordem de Servico", o.name, "avisos_enviados"))

	def test_texto_personalizado_e_texto_quebrado(self):
		configurar(texto_status_os="Oi {nome}! O.S. {os}: {situacao}")
		o = nova_os()
		post = self.mudar(o, "Concluida")
		self.assertTrue(post.call_args.kwargs["json"]["mensagem"].startswith("Oi Ana! O.S. "))
		configurar(texto_status_os="Oi {nome} {campo_que_nao_existe}")
		o.reload()
		post = self.mudar(o, "Aguardando orgao")
		self.assertIn("aguarda o retorno do orgao", post.call_args.kwargs["json"]["mensagem"])
