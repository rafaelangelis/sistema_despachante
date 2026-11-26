import unittest

from dom_despachante.validadores import (
	formata_cep,
	normaliza_telefone,
	so_digitos,
	valida_chassi,
	valida_cnpj,
	valida_cpf,
	valida_placa,
	valida_renavam,
)


class TestValidadores(unittest.TestCase):
	def test_cpf(self):
		self.assertTrue(valida_cpf("529.982.247-25"))
		self.assertTrue(valida_cpf("52998224725"))
		self.assertFalse(valida_cpf("529.982.247-26"))
		self.assertFalse(valida_cpf("111.111.111-11"))
		self.assertFalse(valida_cpf("123"))
		self.assertFalse(valida_cpf(None))

	def test_cnpj(self):
		self.assertTrue(valida_cnpj("11.222.333/0001-81"))
		self.assertFalse(valida_cnpj("11.222.333/0001-80"))
		self.assertFalse(valida_cnpj("00.000.000/0000-00"))
		self.assertFalse(valida_cnpj(""))

	def test_placa(self):
		self.assertTrue(valida_placa("ABC1234"))
		self.assertTrue(valida_placa("ABC1D23"))
		self.assertTrue(valida_placa("abc1d23"))
		self.assertFalse(valida_placa("ABC-1234"))
		self.assertFalse(valida_placa("AB12345"))

	def test_chassi_sem_i_o_q(self):
		self.assertTrue(valida_chassi("9BWZZZ377VT004251"))
		self.assertFalse(valida_chassi("9BWZZZ377VT00425I"))
		self.assertFalse(valida_chassi("CURTO"))

	def test_renavam(self):
		self.assertTrue(valida_renavam("00123456789"))
		self.assertFalse(valida_renavam("1234"))

	def test_telefone(self):
		self.assertEqual(normaliza_telefone("(11) 99999-8888"), "5511999998888")
		self.assertEqual(normaliza_telefone("11 3333-4444"), "551133334444")
		self.assertEqual(normaliza_telefone("+55 11 99999-8888"), "5511999998888")
		self.assertEqual(normaliza_telefone(""), "")

	def test_utilitarios(self):
		self.assertEqual(so_digitos("a1b2-3"), "123")
		self.assertEqual(formata_cep("01310100"), "01310-100")
		self.assertEqual(formata_cep("123"), "123")
