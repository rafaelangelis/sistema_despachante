# -*- coding: utf-8 -*-
"""Aviso ao cliente (WhatsApp, via o mesmo webhook dos alertas) quando a O.S. muda de status."""

import frappe
from frappe.utils import now_datetime

SITUACAO = {
	"Em andamento": "esta em andamento",
	"Aguardando orgao": "foi protocolada e aguarda o retorno do orgao",
	"Concluida": "esta pronta. Ja pode retirar a documentacao",
	"Entregue": "foi entregue. Obrigado pela confianca",
	"Cancelada": "foi cancelada. Qualquer duvida, fale com a gente",
}

TEXTO_PADRAO = "Ola {nome}, sua ordem de servico {os} ({categoria}{placa}) {situacao}. DOM Cristo Despachante."


def status_notificados(config):
	bruto = config.status_notificados or "Aguardando orgao\nConcluida"
	return {linha.strip() for linha in bruto.replace(",", "\n").splitlines() if linha.strip()}


def ao_mudar_status(doc):
	"""Chamado no on_update da O.S.; enfileira o aviso se o status mudou para um da lista."""
	if doc.flags.in_insert or not doc.has_value_changed("status"):
		return
	config = frappe.get_single("Configuracao Despachante")
	if not config.notificar_status_os or doc.status not in status_notificados(config):
		return
	frappe.enqueue(
		"dom_despachante.notificacoes.notificar_status_os",
		queue="short",
		ordem_de_servico=doc.name,
		status=doc.status,
		enqueue_after_commit=True,
		now=frappe.flags.in_test,
	)


def montar_mensagem(os_doc, nome, config):
	placa = ""
	if os_doc.veiculo:
		placa = frappe.db.get_value("Veiculo", os_doc.veiculo, "placa") or ""
	texto = config.texto_status_os or TEXTO_PADRAO
	try:
		return texto.format(
			nome=nome or "",
			os=os_doc.name,
			categoria=os_doc.categoria_servico or "",
			placa=(", placa " + placa) if placa else "",
			situacao=SITUACAO.get(os_doc.status, "mudou para: " + (os_doc.status or "")),
		)
	except (KeyError, IndexError, ValueError):
		# texto configurado com campo invalido: nao deixa de avisar, usa o padrao
		frappe.log_error(frappe.get_traceback(), "Texto de aviso de O.S. invalido")
		return TEXTO_PADRAO.format(
			nome=nome or "", os=os_doc.name, categoria=os_doc.categoria_servico or "",
			placa=(", placa " + placa) if placa else "", situacao=SITUACAO.get(os_doc.status, os_doc.status),
		)


def notificar_status_os(ordem_de_servico, status):
	from dom_despachante.tasks import _enviar, _telefone_whatsapp

	os_doc = frappe.get_doc("Ordem de Servico", ordem_de_servico)
	if os_doc.status != status:
		return "status_mudou_de_novo"  # mudou de novo antes da fila rodar: o aviso novo cobre
	config = frappe.get_single("Configuracao Despachante")
	numero, nome = _telefone_whatsapp(os_doc.cliente)
	if not numero:
		resultado = "sem_whatsapp"
	else:
		resultado = _enviar(montar_mensagem(os_doc, nome, config), numero, "status_{0}_{1}".format(status, ordem_de_servico))
	linha = "{0} {1} -> {2}".format(now_datetime().strftime("%d/%m/%Y %H:%M"), status, resultado)
	frappe.db.set_value(
		"Ordem de Servico",
		ordem_de_servico,
		"avisos_enviados",
		((os_doc.avisos_enviados or "") + "\n" + linha).strip(),
		update_modified=False,
	)
	return resultado
