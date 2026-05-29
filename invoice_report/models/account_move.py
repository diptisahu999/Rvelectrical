import json
from odoo import api, fields, models, tools


class AccountMove(models.Model):
    _inherit = "account.move"

    terms_condition_id = fields.Many2one("terms.and.conditions", "Terms and Condition")

    # Remove custom vehicle_no and eway_bill_no fields - using standard Odoo 18 fields instead:
    # - l10n_in_vehicle_no (from l10n_in_edi_ewaybill)
    # - ewaybillnumber (computed field for e-waybill integration)
    challan_no = fields.Char("Challan Number")
    dispatch_number = fields.Char("Dispatch Number", compute='_compute_dispatch_number', store=True, readonly=False)
    
    @api.depends('invoice_line_ids.sale_line_ids.order_id.picking_ids.name', 'invoice_line_ids.sale_line_ids.order_id.picking_ids.state', 'invoice_line_ids.sale_line_ids.order_id.picking_ids.picking_type_id.code')
    def _compute_dispatch_number(self):
        for move in self:
            dispatch_numbers = set()
            for line in move.invoice_line_ids:
                for sale_line in line.sale_line_ids:
                    for picking in sale_line.order_id.picking_ids:
                        if picking.state != 'cancel' and picking.name and picking.picking_type_id.code == 'outgoing':
                            dispatch_numbers.add(picking.name)
            
            if dispatch_numbers:
                move.dispatch_number = ', '.join(sorted(dispatch_numbers))
            else:
                if not move.dispatch_number:
                    move.dispatch_number = False
    
    # E-waybill number field - integrates with standard Odoo 18 e-waybill systems
    ewaybillnumber = fields.Char("E-way Bill Number", compute="_compute_ewaybillnumber", store=True, readonly=False)
    
    # E-invoice fields for Indian GST compliance
    # These fields store data from e-invoice generation
    l10n_in_irn = fields.Char(
        string="IRN (Invoice Reference Number)", 
        compute='_compute_l10n_in_einvoice_data',
        store=True,
        readonly=False,
        copy=False,
        help="Invoice Reference Number from e-invoice system"
    )
    l10n_in_ack_number = fields.Char(
        string="Acknowledgment Number",
        compute='_compute_l10n_in_einvoice_data',
        store=True,
        readonly=False,
        copy=False,
        help="Acknowledgment number from e-invoice system"
    )
    l10n_in_ack_date = fields.Datetime(
        string="Acknowledgment Date",
        compute='_compute_l10n_in_einvoice_data',
        store=True,
        readonly=False,
        copy=False,
        help="Date and time of acknowledgment"
    )
    l10n_in_qr_code_str = fields.Text(
        string="QR Code String",
        compute='_compute_l10n_in_einvoice_data',
        store=True,
        readonly=False,
        copy=False,
        help="QR code data for e-invoice"
    )
    # global_discount = fields.Float(
    #     string='Discount (%)',
    #     digits='Discount',
    #     default=0.0
    # )
    # discount_amount = fields.Monetary(
    #     string='Discount Amount',
    #     compute='_compute_discount_amount',
    #     store=True
    # )
    # price_after_discount = fields.Monetary(
    #     string='Price After Discount',
    #     compute='_compute_price_after_discount',
    #     store=True
    # )
    # amount_residual_custom = fields.Monetary(
    #     string='Custom Amount Due',
    #     compute='_compute_amount_residual_custom',
    #     store=True,
    # )

    

    def action_preview_invoice_list(self):
        """
        Open a list view of invoices in a modal/dialog to allow the user
        to verify invoice numbers.
        """
        # self.ensure_one() # Not strictly necessary if called from list, but good for form button
        return {
            'name': 'Invoice List Preview',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list',
            'views': [[False, 'list']],
            'domain': [('move_type', '=', self.move_type or 'out_invoice')],
            'target': 'new',
            'context': {'create': False, 'delete': False, 'edit': False},
        }

    def _get_l10n_in_edi_response_json(self):
        """Override to gracefully handle JSON decode errors (e.g. empty attachment)."""
        try:
            return super()._get_l10n_in_edi_response_json()
        except (json.decoder.JSONDecodeError, ValueError, TypeError):
            return {}
        except Exception:
            return {}

    @api.depends('edi_document_ids.state', 'edi_document_ids.attachment_id')
    def _compute_l10n_in_einvoice_data(self):
        """Compute e-invoice fields (IRN, Ack Number, etc.) from EDI response."""
        for move in self:
            irn = ''
            ack_number = ''
            ack_date = False
            qr_code_str = ''
            
            try:
                if hasattr(move, '_get_l10n_in_edi_response_json'):
                    edi_response = move._get_l10n_in_edi_response_json()
                    if edi_response and isinstance(edi_response, dict):
                        irn = (edi_response.get('Irn') or 
                              edi_response.get('irn') or 
                              edi_response.get('IRN') or '')
                        
                        ack_number = (edi_response.get('AckNo') or 
                                     edi_response.get('ackNo') or 
                                     edi_response.get('ack_no') or '')
                        
                        ack_date_str = (edi_response.get('AckDt') or 
                                       edi_response.get('ackDt') or 
                                       edi_response.get('ack_date') or '')
                        if ack_date_str:
                            try:
                                ack_date = fields.Datetime.to_datetime(ack_date_str)
                            except (ValueError, TypeError):
                                pass
                        
                        qr_code_str = (edi_response.get('SignedQRCode') or 
                                      edi_response.get('signedQRCode') or 
                                      edi_response.get('qr_code') or '')
            except Exception:
                pass
            
            # Update fields if data found, otherwise keep existing if manual
            if irn:
                move.l10n_in_irn = irn
            elif not move.l10n_in_irn:
                move.l10n_in_irn = False

            if ack_number:
                move.l10n_in_ack_number = ack_number
            elif not move.l10n_in_ack_number:
                move.l10n_in_ack_number = False

            if ack_date:
                move.l10n_in_ack_date = ack_date
            elif not move.l10n_in_ack_date:
                move.l10n_in_ack_date = False

            if qr_code_str:
                move.l10n_in_qr_code_str = qr_code_str
            elif not move.l10n_in_qr_code_str:
                move.l10n_in_qr_code_str = False

    @api.depends('edi_document_ids.state', 'edi_document_ids.attachment_id')
    def _compute_ewaybillnumber(self):
        """Compute e-waybill number from available sources."""
        for move in self:
            eway_bill_no = ''
            try:
                if hasattr(move, '_get_l10n_in_edi_ewaybill_response_json'):
                    edi_response = move._get_l10n_in_edi_ewaybill_response_json()
                    if edi_response and isinstance(edi_response, dict):
                        data = edi_response.get('data', {})
                        eway_bill_no = (data.get('ewayBillNo') or 
                                       data.get('EwbNo') or 
                                       data.get('ewbNo') or 
                                       edi_response.get('ewayBillNo') or 
                                       edi_response.get('EwbNo') or '')
            except Exception:
                pass
            
            if eway_bill_no:
                move.ewaybillnumber = eway_bill_no
            # Ensure we don't clear it if it was manually set
            elif not move.ewaybillnumber:
                move.ewaybillnumber = False

    def action_populate_einvoice_fields_from_edi(self):
        """Manually trigger compute for e-invoice fields."""
        self._compute_l10n_in_einvoice_data()

    def has_narration_content(self):
        """Check if narration field has meaningful content (not empty/whitespace)."""
        if not self.narration:
            return False
        # Remove HTML tags if any and strip whitespace
        clean_text = tools.html2plaintext(self.narration or '').strip()
        return bool(clean_text)

    @api.onchange("terms_condition_id")
    def _onchange_terms_condition_id(self):
        if tools.is_html_empty(self.narration):
            self.narration = self.terms_condition_id.terms_condition



    class AccountMoveLine(models.Model):
        _inherit = "account.move.line"

        def _get_tax_field_context(self):
            """Get context for tax field (GST/IGST filtering)"""
            partner = self.partner_id or self.move_id.partner_id
            company = self.company_id or self.move_id.company_id
            if partner and company:
                return {
                    'filter_taxes_by_location': True,
                    'default_filter_taxes_by_location': True,
                    'partner_id': partner.id,
                    'default_partner_id': partner.id,
                    'company_id': company.id,
                    'default_company_id': company.id,
                    'active_model': 'account.move',
                    'parent': {
                        'partner_id': partner.id,
                        'company_id': company.id
                    }
                }
            return {}

        def _get_tax_domain(self):
            """Get domain to filter taxes based on customer/company state (GST/IGST)"""
            partner = self.partner_id or self.move_id.partner_id
            company = self.company_id or self.move_id.company_id
            if not partner or not company:
                return [('type_tax_use', '=', 'sale')]
            customer_state = partner.state_id
            company_state = company.state_id
            if not company_state:
                gujarat_state = self.env['res.country.state'].search([
                    ('name', 'ilike', 'Gujarat'),
                    ('country_id.code', '=', 'IN')
                ], limit=1)
                if gujarat_state:
                    company_state = gujarat_state
            if not customer_state or not company_state:
                return [('type_tax_use', '=', 'sale')]
            is_same_state = customer_state.id == company_state.id
            if is_same_state:
                return [
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', company.id),
                    ('active', '=', True),
                    ('name', 'not ilike', 'IGST'),
                    '|', '|', '|',
                    ('name', 'ilike', 'GST'),
                    ('name', 'ilike', 'CGST'),
                    ('name', 'ilike', 'SGST'),
                    ('name', 'ilike', 'UTGST'),
                ]
            else:
                return [
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', company.id),
                    ('active', '=', True),
                    ('name', 'ilike', 'IGST')
                ]

        @api.onchange('product_id')
        def _onchange_product_id_no_auto_tax(self):
            # Call parent method if it exists
            if hasattr(super(), '_onchange_product_id'):
                result = super()._onchange_product_id() or {}
            else:
                result = {}
            # Clear any automatically selected taxes
            if self.product_id:
                self.tax_ids = [(5, 0, 0)]  # Clear all taxes
            # Return domain for filtering
            if self.partner_id or self.move_id.partner_id:
                result['domain'] = {'tax_ids': self._get_tax_domain()}
                result['context'] = self._get_tax_field_context()
            return result

        @api.onchange('partner_id')
        def _onchange_partner_filter_taxes(self):
            if self.partner_id or self.move_id.partner_id:
                return {
                    'domain': {'tax_ids': self._get_tax_domain()},
                    'context': self._get_tax_field_context()
                }
            return {}

        @api.onchange('tax_ids')
        def _onchange_tax_ids_domain(self):
            
            if self.partner_id or self.move_id.partner_id:
                return {
                    'domain': {'tax_ids': self._get_tax_domain()},
                    'context': self._get_tax_field_context()
                }
            return {}
    # @api.depends('amount_total', 'global_discount')
    # def _compute_discount_amount(self):
    #     for move in self:
    #         move.discount_amount = move.amount_total * (move.global_discount / 100.0)
    #
    # @api.depends('amount_total', 'discount_amount')
    # def _compute_price_after_discount(self):
    #     for move in self:
    #         move.price_after_discount = move.amount_total - move.discount_amount
    #
    # @api.depends('price_after_discount', 'amount_total', 'amount_residual', 'global_discount')
    # def _compute_amount_residual_custom(self):
    #     for move in self:
    #         if move.global_discount:
    #             # Calculate residual based on price after discount
    #             paid = move.amount_total - move.amount_residual
    #             move.amount_residual_custom = move.price_after_discount - paid
    #         else:
    #             move.amount_residual_custom = move.amount_residual