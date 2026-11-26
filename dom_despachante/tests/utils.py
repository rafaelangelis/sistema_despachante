import frappe
from frappe.tests.utils import FrappeTestCase


class DomTestCase(FrappeTestCase):
	"""Desfaz o banco ao fim de CADA teste (o FrappeTestCase do v15 so desfaz por classe)."""

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")
		super().tearDown()
