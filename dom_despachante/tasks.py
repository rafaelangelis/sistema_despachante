# -*- coding: utf-8 -*-
"""Alertas automaticos de vencimento (licenciamento e CNH).

Roda no agendador do Frappe (scheduler_events daily) e envia para o webhook do n8n,
que repassa para a Evolution API (WhatsApp).
"""

import frappe
from frappe.utils import add_days, format_date, today

TIPOS_LICENCIAMENTO = ("SEM RESTRICAO", "RESTRICAO ADMINISTRATIVA", "LEILAO", "SINISTRO")


def _config():
	return frappe.get_single("Configuracao Despachante")


def _antecedencias():
	config = _config()
	bruto = (config.dias_alerta or "45,30,15,5").replace(";", ",")
	dias = []
	for parte in bruto.split(","):
		parte = parte.strip()
		if parte.isdigit():
			dias.append(int(parte))
	return sorted(set(dias)) or [45, 30, 15, 5]


def _telefone_whatsapp(cliente):
	if not cliente:
		return "", ""
	doc = frappe.get_doc("Cliente", cliente)
	nome = (doc.nome_completo or "").split(" ")[0].title()
	telefones = [t for t in (doc.telefones or []) if t.whatsapp and t.numero]
	if not telefones:
		return "", nome
	principal = next((t for t in telefones if t.principal), telefones[0])
	return principal.numero, nome


def _enviar(mensagem, numero, referencia):
	config = _config()
	if config.modo_simulacao:
		frappe.log_error(message=mensagem, title="[SIMULACAO] alerta {0}".format(referencia))
		return "simulado"
	if not config.webhook_url_alertas:
		frappe.log_error(message=str(numero), title="Webhook de alertas nao configurado")
		return "sem_webhook"
	try:
		import requests

		resp = requests.post(
			config.webhook_url_alertas,
			json={"cliente": numero, "mensagem": mensagem, "referencia": referencia},
			timeout=20,
		)
		return "http_{0}".format(resp.status_code)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Erro ao chamar webhook de alertas")
		return "erro"


def enviar_alertas_licenciamento():
	config = _config()
	if not config.alertar_licenciamento:
		return
	# a ordem dos jobs diarios nao e garantida com varios workers: garante a virada aqui tambem
	atualizar_exercicio_veiculos()
	texto_padrao = config.texto_alerta_licenciamento or (
		"Ola {nome}, o licenciamento do veiculo {placa} vence em {data} (faltam {dias} dias)."
	)
	enviados = 0
	for dias in _antecedencias():
		alvo = add_days(today(), dias)
		veiculos = frappe.get_all(
			"Veiculo",
			filters={"data_vencimento_licenciamento": alvo},
			fields=["name", "placa", "marca_modelo", "proprietario", "proprietario_empresa", "data_vencimento_licenciamento"],
		)
		for veiculo in veiculos:
			contato = veiculo.proprietario
			if not contato and veiculo.proprietario_empresa:
				contato = frappe.db.get_value("Empresa", veiculo.proprietario_empresa, "representante_legal")
			numero, nome = _telefone_whatsapp(contato)
			if not numero:
				continue
			mensagem = texto_padrao.format(
				nome=nome,
				placa=veiculo.placa,
				data=format_date(veiculo.data_vencimento_licenciamento),
				dias=dias,
			)
			resultado = _enviar(mensagem, numero, "licenciamento_{0}d_{1}".format(dias, veiculo.name))
			_registrar_historico(veiculo.name, "licenciamento", dias, resultado)
			enviados += 1
	if enviados:
		frappe.log_error(
			message="Alertas de licenciamento processados: {0}".format(enviados),
			title="Rotina de alertas",
		)


def enviar_alertas_cnh():
	config = _config()
	if not config.alertar_cnh:
		return
	texto_padrao = config.texto_alerta_cnh or (
		"Ola {nome}, sua CNH vence em {data} (faltam {dias} dias)."
	)
	for dias in _antecedencias():
		alvo = add_days(today(), dias)
		clientes = frappe.get_all(
			"Cliente",
			filters={"cnh_validade": alvo, "status": "Ativo"},
			fields=["name", "nome_completo", "cnh_validade"],
		)
		for cliente in clientes:
			numero, nome = _telefone_whatsapp(cliente.name)
			if not numero:
				continue
			mensagem = texto_padrao.format(
				nome=nome, data=format_date(cliente.cnh_validade), dias=dias
			)
			_enviar(mensagem, numero, "cnh_{0}d_{1}".format(dias, cliente.name))


def atualizar_exercicio_veiculos():
	"""Leva cada veiculo para o exercicio (ano) corrente e recalcula o vencimento.

	Sem isso um veiculo cadastrado em 2026 ficaria com vencimento em 2026 para sempre
	e nunca mais geraria alerta. Roda diariamente, antes dos alertas.
	"""
	from frappe.utils import getdate

	ano = getdate(today()).year
	nomes = frappe.get_all(
		"Veiculo",
		filters={"exercicio_licenciamento": ["<", ano]},
		pluck="name",
	)
	atualizados = 0
	for nome in nomes:
		try:
			doc = frappe.get_doc("Veiculo", nome)
			doc.exercicio_licenciamento = ano
			doc.flags.ignore_permissions = True
			doc.save()
			atualizados += 1
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Falha ao virar exercicio do veiculo {0}".format(nome))
	frappe.db.commit()
	return atualizados


def verificar_calendario_proximo_ano():
	"""A partir de novembro, avisa (sininho) Despachantes se falta o calendario do ano seguinte.

	Roda semanalmente. Lista so as UFs que tem veiculo cadastrado.
	"""
	from frappe.utils import getdate

	hoje = getdate(today())
	if hoje.month < 11:
		return []
	proximo = hoje.year + 1
	ufs = [
		r.uf_emplacamento
		for r in frappe.get_all("Veiculo", fields=["uf_emplacamento"], distinct=True)
		if r.uf_emplacamento
	]
	faltando = [uf for uf in sorted(set(ufs)) if not frappe.db.exists("Calendario Licenciamento", {"uf": uf, "ano": proximo})]
	if not faltando:
		return []
	assunto = "Falta o calendario de licenciamento {0} para: {1}".format(proximo, ", ".join(faltando))
	corpo = (
		"Sem o calendario oficial, os vencimentos de {0} serao ESTIMADOS pelo calendario anterior. "
		"Cadastre em Calendario Licenciamento (ou use 'Copiar calendario' e ajuste pelo site do DETRAN)."
	).format(proximo)
	usuarios = set(
		frappe.get_all(
			"Has Role",
			filters={"role": ["in", ["Despachante", "System Manager"]], "parenttype": "User"},
			pluck="parent",
		)
	) - {"Guest"}
	for usuario in usuarios:
		if not frappe.db.get_value("User", usuario, "enabled"):
			continue
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": usuario,
				"type": "Alert",
				"document_type": "Calendario Licenciamento",
				"subject": assunto,
				"email_content": corpo,
			}
		).insert(ignore_permissions=True)
	return faltando


def _registrar_historico(veiculo, tipo, dias, resultado):
	try:
		atual = frappe.db.get_value("Veiculo", veiculo, "alerta_enviado_em") or ""
		linha = "{0} {1} {2}d -> {3}".format(today(), tipo, dias, resultado)
		frappe.db.set_value("Veiculo", veiculo, "alerta_enviado_em", (atual + "\n" + linha).strip())
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Falha ao registrar historico de alerta")