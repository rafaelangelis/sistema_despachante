frappe.ui.form.on("Cliente", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.anonimizado || !frappe.user.has_role("System Manager")) return;
		frm.add_custom_button(
			__("Anonimizar dados (LGPD)"),
			() => {
				frappe.prompt(
					[
						{
							fieldtype: "HTML",
							options:
								"<p>Apaga <b>definitivamente</b> nome, CPF, RG, contatos, CNH, endereco, observacoes e o historico de alteracoes deste cliente. As O.S. e recebimentos continuam existindo, ligados a \"CLIENTE ANONIMIZADO\".</p><p><b>Nao pode ser desfeito.</b> Use apenas a pedido do titular e se nao houver obrigacao legal de guardar os dados.</p>",
						},
						{ fieldname: "confirmacao", fieldtype: "Data", label: __("Digite ANONIMIZAR para confirmar"), reqd: 1 },
					],
					(v) => {
						frappe.call({
							method: "dom_despachante.lgpd.anonimizar_cliente",
							args: { cliente: frm.doc.name, confirmacao: v.confirmacao },
							freeze: true,
							callback: () => frm.reload_doc(),
						});
					},
					__("Anonimizar cliente"),
					__("Anonimizar")
				);
			},
			__("Acoes")
		);
	},
});
