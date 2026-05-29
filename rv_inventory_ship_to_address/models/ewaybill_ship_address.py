from odoo import models, fields, api
from odoo.tools import html_escape


class EWaybill(models.Model):
    _inherit = "l10n.in.ewaybill"

    ship_to_address_html = fields.Html(
        string="Ship To Address",
        compute="_compute_ship_to_address",
        store=False,
    )

    picking_partner_id = fields.Many2one(
        'res.partner',
        related='picking_id.partner_id',
        string='Picking Partner'
    )

    # =========================
    # COMPUTE (initial load)
    # =========================
    @api.depends("partner_ship_to_id", "picking_id")
    def _compute_ship_to_address(self):
        for rec in self:
            # For initial load, allow fallback
            partner = rec.partner_ship_to_id or rec.picking_id.partner_id
            rec.ship_to_address_html = rec._format_partner_address(partner)

    # =========================
    # ONCHANGE (live UI)
    # =========================
    @api.onchange("partner_ship_to_id")
    def _onchange_partner_ship_to_id(self):
        for rec in self:
            # 🔥 If user clears partner → clear address
            if not rec.partner_ship_to_id:
                rec.ship_to_address_html = ""
            else:
                rec.ship_to_address_html = rec._format_partner_address(
                    rec.partner_ship_to_id
                )

    # =========================
    # ADDRESS FORMATTER
    # =========================
    def _format_partner_address(self, partner):
        if not partner:
            return ""

        lines = []

        if partner.street:
            lines.append(html_escape(partner.street))
        if partner.street2:
            lines.append(html_escape(partner.street2))

        city_zip = " ".join(filter(None, [partner.city, partner.zip]))
        if city_zip:
            lines.append(html_escape(city_zip))

        state_country = ", ".join(filter(None, [
            partner.state_id.name if partner.state_id else "",
            partner.country_id.name if partner.country_id else "",
        ]))
        if state_country:
            lines.append(html_escape(state_country))

        if partner.vat:
            lines.append(f"GST: {html_escape(partner.vat)}")

        return "<br/>".join(lines)