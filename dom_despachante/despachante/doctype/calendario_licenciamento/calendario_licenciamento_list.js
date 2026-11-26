frappe.listview_settings["Calendario Licenciamento"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Copiar calendario"), () => {
			const ano = new Date().getFullYear();
			frappe.prompt(
				[
					{ fieldname: "uf", label: "UF", fieldtype: "Data", default: "SP", reqd: 1 },
					{ fieldname: "ano_origem", label: "Copiar do ano", fieldtype: "Int", default: ano, reqd: 1 },
					{ fieldname: "ano_destino", label: "Para o ano", fieldtype: "Int", default: ano + 1, reqd: 1 },
				],
				(v) => {
					frappe.call({
						method: "dom_despachante.despachante.doctype.calendario_licenciamento.calendario_licenciamento.copiar_calendario",
						args: { uf: (v.uf || "").toUpperCase(), ano_origem: v.ano_origem, ano_destino: v.ano_destino },
						freeze: true,
						callback(r) {
							frappe.msgprint(
								__("{0} regras criadas. CONFIRA as datas no site do DETRAN antes de confiar nelas.", [r.message || 0])
							);
							listview.refresh();
						},
					});
				},
				__("Copiar calendario de licenciamento"),
				__("Copiar")
			);
		});
	},
};
