from unittest.mock import patch

import frappe
from dom_despachante.tests.utils import DomTestCase

from dom_despachante import tasks
from dom_despachante.despachante.doctype.veiculo.veiculo import calcular_vencimento

UF = "RJ"  # o site de teste ja vem com SP/2026 semeado; RJ fica isolado para estes testes
GRUPO_LEVES = "Automoveis, Motos, Utilitarios, Onibus e Reboques"
GRUPO_CAM = "Caminhoes e Caminhoes-Tratores"


def regra(ano, final, mes, dia, grupo=GRUPO_LEVES, uf=UF):
	return frappe.get_doc(
		{
			"doctype": "Calendario Licenciamento",
			"uf": uf,
			"ano": ano,
			"grupo": grupo,
			"final_placa": str(final),
			"mes_limite": mes,
			"dia_limite": dia,
		}
	).insert()


def veiculo(placa, ano, uf=UF, **extra):
	return frappe.get_doc(
		dict({"doctype": "Veiculo", "placa": placa, "uf_emplacamento": uf, "exercicio_licenciamento": ano}, **extra)
	).insert()


class TestVeiculo(DomTestCase):
	def test_normaliza_placa_e_final(self):
		v = veiculo("abc-1d27", 2030)
		self.assertEqual(v.placa, "ABC1D27")
		self.assertEqual(v.final_placa, "7")

	def test_placa_invalida(self):
		with self.assertRaises(frappe.ValidationError):
			veiculo("12ABCDE", 2030)

	def test_vencimento_pelo_calendario_do_ano(self):
		regra(2030, 1, 7, 31)
		v = veiculo("AAA1A11", 2030)
		self.assertEqual(str(v.data_vencimento_licenciamento), "2030-07-31")
		self.assertFalse(v.vencimento_estimado)

	def test_caminhao_usa_grupo_proprio(self):
		regra(2030, 2, 7, 31)
		regra(2030, 2, 10, 31, grupo=GRUPO_CAM)
		v = veiculo("AAA1A12", 2030, tipo_veiculo="CAMINHAO")
		self.assertEqual(str(v.data_vencimento_licenciamento), "2030-10-31")

	def test_sem_calendario_do_ano_usa_anterior_e_marca_estimado(self):
		regra(2030, 3, 8, 31)
		v = veiculo("AAA1A13", 2031)
		self.assertEqual(str(v.data_vencimento_licenciamento), "2031-08-31")
		self.assertTrue(v.vencimento_estimado)

	def test_sem_nenhum_calendario_nao_inventa_data(self):
		v = veiculo("AAA1A14", 2031, uf="AC")
		self.assertIsNone(v.data_vencimento_licenciamento)

	def test_29_de_fevereiro_em_ano_nao_bissexto(self):
		regra(2028, 4, 2, 29)
		data, estimado = calcular_vencimento(UF, 2029, GRUPO_LEVES, "4")
		self.assertEqual(data, "2029-02-28")
		self.assertTrue(estimado)

	def test_cadastrar_calendario_oficial_recalcula_estimados(self):
		regra(2030, 5, 8, 31)
		v = veiculo("AAA1A15", 2031)
		self.assertTrue(v.vencimento_estimado)
		regra(2031, 5, 9, 30)
		v.reload()
		self.assertEqual(str(v.data_vencimento_licenciamento), "2031-09-30")
		self.assertFalse(v.vencimento_estimado)

	def test_virada_de_exercicio(self):
		regra(2030, 6, 7, 31)
		v = veiculo("AAA1A16", 2030)
		with patch.object(tasks, "today", return_value="2031-01-02"), patch.object(frappe.db, "commit"):
			tasks.atualizar_exercicio_veiculos()
		v.reload()
		self.assertEqual(v.exercicio_licenciamento, 2031)
		self.assertEqual(str(v.data_vencimento_licenciamento), "2031-07-31")
		self.assertTrue(v.vencimento_estimado)

	def test_copiar_calendario(self):
		from dom_despachante.despachante.doctype.calendario_licenciamento.calendario_licenciamento import (
			copiar_calendario,
		)

		regra(2032, 7, 7, 31)
		regra(2032, 8, 8, 31)
		self.assertEqual(copiar_calendario(UF, 2032, 2033), 2)
		self.assertEqual(copiar_calendario(UF, 2032, 2033), 0, "copiar de novo nao duplica")
		self.assertEqual(frappe.db.count("Calendario Licenciamento", {"uf": UF, "ano": 2033}), 2)

	def test_calendario_rejeita_final_invalido(self):
		with self.assertRaises(frappe.ValidationError):
			regra(2030, "X", 7, 31)
