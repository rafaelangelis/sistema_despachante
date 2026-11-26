frappe.query_reports["Caixa Recebimentos"] = {
	filters: [
		{ fieldname: "de", label: __("De"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "ate", label: __("Ate"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{
			fieldname: "forma_pagamento",
			label: __("Forma"),
			fieldtype: "Select",
			options: "\nPIX\nDinheiro\nCartao de debito\nCartao de credito\nBoleto\nTransferencia",
		},
		{ fieldname: "recebido_por", label: __("Recebido por"), fieldtype: "Link", options: "User" },
	],
};
