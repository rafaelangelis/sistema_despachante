frappe.query_reports["Contas a Receber"] = {
	filters: [
		{ fieldname: "cliente", label: __("Cliente"), fieldtype: "Link", options: "Cliente" },
		{ fieldname: "ate_data", label: __("Abertas ate"), fieldtype: "Date" },
		{ fieldname: "min_dias", label: __("Em aberto ha pelo menos (dias)"), fieldtype: "Int" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "dias_em_aberto" && data && data.dias_em_aberto > 30) {
			value = `<span style="color: var(--red-600); font-weight: bold;">${value}</span>`;
		}
		return value;
	},
};
