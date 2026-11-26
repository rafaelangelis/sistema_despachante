frappe.ui.form.on("Ordem de Servico", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.status !== "Cancelada" && flt(frm.doc.saldo) > 0) {
			frm.add_custom_button(__("Registrar recebimento"), () => {
				frappe.new_doc("Recebimento", {
					ordem_de_servico: frm.doc.name,
					valor: frm.doc.saldo,
				});
			}, __("Financeiro"));
		}
		frm.add_custom_button(__("Ver recebimentos"), () => {
			frappe.set_route("List", "Recebimento", { ordem_de_servico: frm.doc.name });
		}, __("Financeiro"));

		const cores = { Pago: "green", Parcial: "orange", Pendente: "red" };
		if (cores[frm.doc.status_pagamento]) {
			frm.dashboard.add_indicator(
				__("{0}: saldo {1}", [__(frm.doc.status_pagamento), format_currency(frm.doc.saldo)]),
				cores[frm.doc.status_pagamento]
			);
		}
	},
});
