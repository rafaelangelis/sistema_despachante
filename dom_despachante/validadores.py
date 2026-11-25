# -*- coding: utf-8 -*-
"""Validacoes de documentos brasileiros e consultas publicas (BrasilAPI)."""

import re

import frappe

BRASILAPI_CEP = "https://brasilapi.com.br/api/cep/v2/{cep}"
BRASILAPI_CNPJ = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
TIMEOUT = 8


def so_digitos(valor) -> str:
	return re.sub(r"\D", "", valor or "")


def valida_cpf(cpf) -> bool:
	c = so_digitos(cpf)
	if len(c) != 11 or len(set(c)) == 1:
		return False
	for pos in (9, 10):
		soma = sum(int(c[i]) * ((pos + 1) - i) for i in range(pos))
		resto = (soma * 10) % 11
		digito = 0 if resto == 10 else resto
		if digito != int(c[pos]):
			return False
	return True


def valida_cnpj(cnpj) -> bool:
	c = so_digitos(cnpj)
	if len(c) != 14 or len(set(c)) == 1:
		return False
	pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
	pesos2 = [6] + pesos1
	for pesos, pos in ((pesos1, 12), (pesos2, 13)):
		soma = sum(int(c[i]) * pesos[i] for i in range(pos))
		dv = 11 - (soma % 11)
		if dv >= 10:
			dv = 0
		if dv != int(c[pos]):
			return False
	return True


def valida_placa(placa) -> bool:
	"""Aceita padrao antigo (ABC1234) e Mercosul (ABC1D23)."""
	return bool(re.match(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$", (placa or "").upper()))


def valida_chassi(chassi) -> bool:
	return bool(re.match(r"^[A-HJ-NPR-Z0-9]{17}$", (chassi or "").upper()))


def valida_renavam(renavam) -> bool:
	c = so_digitos(renavam)
	return len(c) == 11


def normaliza_telefone(numero) -> str:
	"""Devolve DDI+DDD+numero (ex.: 5511999998888) para uso na Evolution API."""
	c = so_digitos(numero)
	if not c:
		return ""
	if c.startswith("55") and len(c) in (12, 13):
		return c
	if len(c) in (10, 11):
		return "55" + c
	return c


def formata_cep(cep) -> str:
	c = so_digitos(cep)
	return f"{c[:5]}-{c[5:]}" if len(c) == 8 else (cep or "")


def consulta_cep(cep):
	"""Retorna dict da BrasilAPI (street, neighborhood, city, state) ou None."""
	c = so_digitos(cep)
	if len(c) != 8:
		return None
	try:
		import requests

		resp = requests.get(BRASILAPI_CEP.format(cep=c), timeout=TIMEOUT)
		if resp.status_code == 200:
			return resp.json()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "BrasilAPI CEP indisponivel")
	return None


def consulta_cnpj(cnpj):
	"""Retorna dict da BrasilAPI (razao_social, nome_fantasia, cep, municipio, uf...) ou None."""
	c = so_digitos(cnpj)
	if len(c) != 14:
		return None
	try:
		import requests

		resp = requests.get(BRASILAPI_CNPJ.format(cnpj=c), timeout=TIMEOUT)
		if resp.status_code == 200:
			return resp.json()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "BrasilAPI CNPJ indisponivel")
	return None