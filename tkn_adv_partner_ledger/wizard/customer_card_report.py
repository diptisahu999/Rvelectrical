# -*- coding: utf-8 -*-

import io
import base64
import xlsxwriter
from odoo import models, fields, api
from odoo.tools.translate import _
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError


class report_stock_card(models.TransientModel):
    _name = 'report.customer.card'

    @api.model
    def default_get(self, field_list):
        res = super(report_stock_card, self).default_get(field_list)
        today = datetime.now()
        current_month_last_day = ((today.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)).day
        res.update({
            'date_start': today.replace(day=1),
            'date_end': today.replace(day=current_month_last_day),
        })
        return res

    date_start = fields.Date(string="From Date")
    date_end = fields.Date(string="To Date")
    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 default=lambda self: self.env.user.company_id.id, )
    # partner_id = fields.Many2one(comodel_name="res.partner", string="Partner",
    #                              default=lambda self: self.env.user.partner_id.id, required=True, )
    partner_ids = fields.Many2many(comodel_name="res.partner", string="Partners", required=True)

    show_details = fields.Boolean(string="Invoice Details", default=False)

    sales_person_ids = fields.Many2many('res.users', string="Sales Person")
    journal_ids = fields.Many2many('account.journal', string="Journals")

    moves_status = fields.Selection([
        ('posted', 'Only Posted Entries'),
        ('all', 'All Entries'), ],
        required=True, string='Moves Status', default='posted')
    
    partner_type = fields.Selection([
        ('receivable', 'Receivable Accounts'),
        ('payable', 'Payable Accounts'),
        ('both', 'Receivable and Payable Accounts'),
    ], string="Partner's")


    show_initial_balance = fields.Boolean(string="Show Initial Balance", default=True)
    show_closing_balance = fields.Boolean(string="Show Ending Balance", default=True)

    printed_by = fields.Boolean(string="Show Printed By", default=False)
    print_date = fields.Boolean(string="Show Print Date", default=False)

    currency_id = fields.Many2one('res.currency', string='Report Currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id)

    ledger_line_ids = fields.One2many('partner.ledger.line', 'wizard_id', string='Ledger Lines')

    @api.constrains(
        "date_start", "date_end")
    def _check_date(self):
        strWarning = _(
            "Date start must be greater than date end")
        if self.date_start and self.date_end:
            if self.date_start > self.date_end:
                raise UserError(strWarning)

    def print_report(self):
        self.ensure_one()

        [data] = self.read()
        data['form'] = self.read(['date_start', 'date_end', 'company_id', 'partner_ids', 'journal_ids', 'sales_person_ids', 'moves_status'])[0]

        datas = {
            'model': 'product.product',
            'form': data
        }
        return self.env.ref('tkn_adv_partner_ledger.qweb_report_customer_card_id').report_action(self, data=datas)

    # Excel Report
    def export_xlsx_report(self):
        self.ensure_one()

        # Get data
        [data] = self.read()
        data['form'] = self.read(['date_start', 'date_end', 'company_id', 'partner_ids'])[0]

        report_obj = self.env['report.tkn_adv_partner_ledger.report_customer_card']
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Customer Card')

        # currency
        currency = self.currency_id or self.company_id.currency_id
        currency_format_string = f'#,##0.00 "{currency.symbol}"'

        # Formats
        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#D3D3D3', 'border': 1, 'font_name': 'Arial', 'font_size': 10
        })
        date_format = workbook.add_format(
            {'num_format': 'yyyy-mm-dd', 'align': 'center', 'font_name': 'Arial', 'font_size': 10})
        date_format_header = workbook.add_format(
            {'num_format': 'yyyy-mm-dd', 'align': 'left', 'font_name': 'Arial', 'font_size': 10})
        currency_format = workbook.add_format(
            {'num_format': currency_format_string, 'align': 'right', 'font_name': 'Arial', 'font_size': 10})
        currency_format_header = workbook.add_format(
            {'num_format': currency_format_string, 'align': 'left', 'font_name': 'Arial', 'font_size': 10})
        currency_format_total = workbook.add_format(
            {'bold': True, 'bg_color': '#D3D3D3', 'num_format': currency_format_string, 'align': 'right',
             'font_name': 'Arial', 'font_size': 10})
        text_format = workbook.add_format({'font_name': 'Arial', 'font_size': 10})
        initial_balance_format = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'align': 'center'})
        title_format = workbook.add_format(
            {'bold': True, 'border': 1, 'font_size': 16, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Arial'})
        header_label_format = workbook.add_format({'bold': True, 'font_size': 11, 'font_name': 'Arial'})
        header_value_format = workbook.add_format({'font_size': 11, 'font_name': 'Arial'})

        current_row = 0

        for partner in self.partner_ids:
            list_move = []
            obj_inv = self.env["account.move"]
            obj_pay = self.env["account.payment"]
            obj_entry = self.env["account.move.line"]

            inv_domain = [('move_type', '!=', 'entry'), ("partner_id", "=", partner.id)]
            pay_domain = [("partner_id", "=", partner.id)]
            entery_domain = [('partner_id', '=', partner.id), ("payment_id", "=", False)]

            if self.date_start:
                inv_domain.insert(0, ("invoice_date", ">=", self.date_start))
                pay_domain.insert(0, ("date", ">=", self.date_start))
                entery_domain.insert(0, ("date", ">=", self.date_start))

            if self.date_end:
                inv_domain.insert(0, ("invoice_date", "<=", self.date_end))
                pay_domain.insert(0, ("date", "<=", self.date_end))
                entery_domain.insert(0, ("date", "<=", self.date_end))

            # Check For Journals
            if self.journal_ids:
                inv_domain = [("journal_id", "in", self.journal_ids.ids), ] + inv_domain
                pay_domain = [("journal_id", "in", self.journal_ids.ids), ] + pay_domain
                entery_domain = [("journal_id", "in", self.journal_ids.ids), ] + entery_domain

            # Check For Sales Person
            if self.sales_person_ids:
                inv_domain = [("invoice_user_id", "in", self.sales_person_ids.ids), ] + inv_domain
                entery_domain = [("move_id.invoice_user_id", "in", self.sales_person_ids.ids), ] + entery_domain

            # check Status
            if self.moves_status == "posted":
                inv_domain = [('state', 'not in', ['draft', 'cancel']), ] + inv_domain
                pay_domain = [('state', 'not in', ['draft', 'cancelled']), ] + pay_domain
                entery_domain = [('parent_state', 'in', ['posted', 'post']), ] + entery_domain

            invoices = obj_inv.sudo().search(inv_domain, order="invoice_date")
            if self.partner_type == 'receivable':
                invoices = invoices.filtered(lambda m: m.move_type in [
                    'out_invoice', 'out_refund', 'out_receipt'
                ])
            elif self.partner_type == 'payable':
                invoices = invoices.filtered(lambda m: m.move_type in [
                    'in_invoice', 'in_refund', 'in_receipt'
                ])

            entery_domain.insert(0, ("move_id", "not in", invoices.ids))
            
            if self.partner_type == 'receivable':
                entery_domain += [('account_id', '=', partner.property_account_receivable_id.id)]
            elif self.partner_type == 'payable':
                entery_domain += [('account_id', '=', partner.property_account_payable_id.id)]
            else:
                entery_domain += ['|',
                    ('account_id', '=', partner.property_account_receivable_id.id),
                    ('account_id', '=', partner.property_account_payable_id.id)]


            entries = obj_entry.search(entery_domain, order="date")
            payments = obj_pay.search(pay_domain, order="date")
            if self.partner_type == 'receivable':
                payments = payments.filtered(lambda p: p.partner_type == 'customer')
            elif self.partner_type == 'payable':
                payments = payments.filtered(lambda p: p.partner_type == 'supplier')


            p_balance = report_obj._get_balance(partner, self.date_start, self.journal_ids, self.sales_person_ids, self.moves_status, self.currency_id, self.company_id, self.partner_type)

            for ent in entries:
                if ent.credit > 0 or ent.debit > 0:
                    debit = ent.debit
                    credit = ent.credit
                    if ent.currency_id and ent.currency_id != self.currency_id:
                        debit = ent.currency_id._convert(
                            ent.debit, self.currency_id, ent.company_id, ent.date
                        )
                        credit = ent.currency_id._convert(
                            ent.credit, self.currency_id, ent.company_id, ent.date
                        )
                    list_move.append({
                        'date': ent.date,
                        'name': ent.move_id.display_name,
                        'ref': ent.move_id.ref or '',
                        'debit': debit,
                        'credit': credit,
                        'balance': p_balance + ent.debit - ent.credit
                    })
                    p_balance += (ent.debit - ent.credit)

            for pay in payments:
                # If Sales Person Filtered
                # if self.sales_person_ids:
                #     continue
                amount = pay.amount
                if pay.currency_id != self.currency_id:
                    amount = pay.currency_id._convert(
                        pay.amount,
                        self.currency_id,
                        pay.company_id,
                        pay.date or fields.Date.today()
                    )
                credit = amount if pay.payment_type == 'inbound' else 0.0
                debit = amount if pay.payment_type == 'outbound' else 0.0
                list_move.append({
                    'date': pay.date,
                    'name': f'Payment: {pay.name}',
                    'ref': pay.memo or '',
                    'debit': debit,
                    'credit': credit,
                    'balance': p_balance + (debit - credit)
                })
                p_balance += (debit - credit)

            for inv in invoices:
                amount = inv.amount_total
                if inv.currency_id != currency:
                    amount = inv.currency_id._convert(
                        amount, currency, inv.company_id, inv.invoice_date or fields.Date.today()
                    )
                debit = 0.0
                credit = 0.0
                if inv.move_type == 'out_invoice':
                    # Sale Invoice = Debit
                    debit = amount
                elif inv.move_type == 'out_refund':
                    # Sale Refund = Credit
                    credit = amount
                elif inv.move_type == 'in_invoice':
                    # Vendor Bill = Credit
                    credit = amount
                elif inv.move_type == 'in_refund':
                    # Vendor Refund = Debit
                    debit = amount
                elif inv.move_type == 'out_receipt':
                    # Sale Receipt = Debit
                    debit = amount
                elif inv.move_type == 'in_receipt':
                    # Purchase Receipt = Credit
                    credit = amount

                list_move.append({
                    'date': inv.invoice_date,
                    'name': f'Invoice: {inv.name}' if inv.name else '/',
                    'ref': inv.ref or '',
                    'debit': debit,
                    'credit': credit,
                    'balance': p_balance + (debit - credit)
                })
                p_balance += (debit - credit)

            list_move.sort(key=lambda x: x['date'])

            running_balance = report_obj._get_balance(partner, self.date_start, self.journal_ids, self.sales_person_ids, self.moves_status, self.currency_id, self.company_id, self.partner_type)
            for move in list_move:
                move['balance'] = running_balance + move['debit'] - move['credit']
                running_balance = move['balance']
            docs = list_move

            # Header
            sheet.merge_range(current_row, 0, current_row, 5, _('Customer Account Statement'), title_format)
            current_row += 1
            sheet.write(current_row, 0, _('Customer:'), header_label_format)
            sheet.merge_range(current_row, 1, current_row, 2, partner.name, header_value_format)

            current_row += 1
            sheet.write(current_row, 0, _('Current Balance:'), header_label_format)
            sheet.write(current_row, 1, report_obj._get_currant_balance(partner, self.date_start, self.date_end, self.journal_ids, self.sales_person_ids, self.moves_status, self.currency_id, self.company_id, self.partner_type),
                        currency_format_header)

            current_row += 1
            sheet.write(current_row, 0, _('Period:'), header_label_format)
            period = f"{self.date_start.strftime('%Y-%m-%d')} - {self.date_end.strftime('%Y-%m-%d')}"
            sheet.write(current_row, 1, period, header_value_format)

            if self.sales_person_ids:
                current_row += 1
                sheet.write(current_row, 0, _('Sales Person:'), header_label_format)
                sheet.write(current_row, 1, ', '.join(self.sales_person_ids.mapped('name')), header_value_format)

            if self.journal_ids:
                current_row += 1
                sheet.write(current_row, 0, _('Journal:'), header_label_format)
                sheet.write(current_row, 1, ', '.join(self.journal_ids.mapped('name')), header_value_format)

            if self.printed_by:
                current_row += 1
                sheet.write(current_row, 0, _('Print Date:'), header_label_format)
                sheet.write(current_row, 1, fields.Datetime.now(), date_format_header)
            if self.print_date:
                current_row += 1
                sheet.write(current_row, 0, _('Printed By:'), header_label_format)
                sheet.write(current_row, 1, self.env.user.name, header_value_format)

            current_row += 2
            sheet.set_column('A:A', 15)
            sheet.set_column('B:B', 50)
            sheet.set_column('C:C', 20)
            sheet.set_column('D:D', 15)
            sheet.set_column('E:E', 15)
            sheet.set_column('F:F', 15)

            headers = [_('Date'), _('Description'), _('Reference'), _('Debit'), _('Credit'), _('Balance')]
            for col, header in enumerate(headers):
                sheet.write(current_row, col, header, header_format)
            current_row += 1

            # Initial Balance row
            initial_balance = report_obj._get_balance(partner, self.date_start, self.journal_ids, self.sales_person_ids, self.moves_status, self.currency_id, self.company_id, self.partner_type)
            sheet.merge_range(current_row, 0, current_row, 1, _('Initial Balance'), initial_balance_format)
            sheet.write(current_row, 5, initial_balance, currency_format)
            current_row += 1

            for line in docs:
                if line.get('date'):
                    sheet.write_datetime(current_row, 0, line['date'], date_format)
                sheet.write(current_row, 1, line.get('name', ''), text_format)
                sheet.write(current_row, 2, line.get('ref', ''), text_format)
                sheet.write(current_row, 3, line.get('debit', 0.0), currency_format)
                sheet.write(current_row, 4, line.get('credit', 0.0), currency_format)
                sheet.write(current_row, 5, line.get('balance', 0.0), currency_format)
                current_row += 1

            total_debit = sum(line.get('debit', 0) for line in docs if line)
            total_credit = sum(line.get('credit', 0) for line in docs if line)
            last_balance = docs[-1].get('balance', 0.0) if docs else 0.0

            sheet.write(current_row, 2, 'Total:', header_format)
            sheet.write(current_row, 3, total_debit, currency_format_total)
            sheet.write(current_row, 4, total_credit, currency_format_total)
            sheet.write(current_row, 5, last_balance, currency_format_total)
            sheet.set_row(current_row, None, None, {'level': 1, 'collapsed': True})

            current_row += 3  # Space between partners

        workbook.close()
        output.seek(0)
        excel_file = base64.b64encode(output.read())
        output.close()
        attachment = self._create_attachment(excel_file)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _create_attachment(self, excel_file):
        # Create and return an attachment with the Excel file
        filename = f'customer_card_{fields.Date.today()}.xlsx'
        return self.env['ir.attachment'].create({
            'name': filename,
            'datas': excel_file,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

    # View Ledger
    def action_view_ledger(self):
        self.ensure_one()
        # Clear existing ledger lines
        self.ledger_line_ids.sudo().unlink()

        # Get the partner ledger data
        self._generate_ledger_lines()

        # Return the action to view the ledger lines
        return {
            'name': _('Partner Ledger'),
            'type': 'ir.actions.act_window',
            'res_model': 'partner.ledger.line',
            'view_mode': 'list,pivot,graph',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'search_default_group_by_date': 1},
            'target': 'current',
        }


    def _generate_ledger_lines(self):
        self.ensure_one()
        PartnerLedgerLine = self.env['partner.ledger.line']
        report_currency = self.currency_id
        company = self.company_id

        # Add initial balance if needed
        for partner in self.partner_ids:
            if self.show_initial_balance:
                initial_balance = self._get_balance(partner, self.date_start, self.journal_ids, self.sales_person_ids, self.moves_status, self.currency_id, self.company_id, self.partner_type)
                PartnerLedgerLine.create({
                    'wizard_id': self.id,
                    'date': self.date_start,
                    'name': _('Initial Balance'),
                    'ref': '',
                    'debit': 0.0,
                    'credit': 0.0,
                    'balance': initial_balance,
                    'currency_id': report_currency.id,
                    'partner_id': partner.id,
                    'is_initial_balance': True,
                    'entry_type': 'Initial Balance',
                })

            # Get all ledger entries
            ledger_entries = self._get_move_data(partner)
            if ledger_entries:
                # Create ledger lines
                for entry in ledger_entries:
                    # Convert entry currency to report currency
                    entry_currency = self.env['res.currency'].search([('name', '=', entry.get('currency'))], limit=1)
                    debit = entry.get('debit') or 0.0
                    credit = entry.get('credit') or 0.0
                    balance = entry.get('balance') or 0.0
                    entry_date = entry.get('date')
                    PartnerLedgerLine.create({
                        'wizard_id': self.id,
                        'date': entry.get('date'),
                        'name': entry.get('num'),
                        'ref': entry.get('origin') or '',
                        'debit': debit,
                        'credit': credit,
                        'balance': balance,
                        'currency_id': report_currency.id,
                        'partner_id': partner.id,
                        'entry_type': entry.get('type'),
                        'invoice_id': entry.get('invoice_id', False),
                        'payment_id': entry.get('payment_id', False),
                        'move_id': entry.get('move_id', False),
                        'has_invoice_details': entry.get('flag') == 'invoice' and self.show_details,
                    })

    def _get_balance(self, partner, date, journals, sales_person, moves_status, currency, company, partner_type=None):
        if not date:
            return 0.0
        # domain = [('partner_id', '=', partner.id), ('date', '<', date), '|',
        #           ('account_id', '=', partner.property_account_receivable_id.id),
        #           ('account_id', '=', partner.property_account_payable_id.id)]

        domain = [('partner_id', '=', partner.id), ('date', '<', date)]

        if partner_type == 'receivable':
            domain += [('account_id', '=', partner.property_account_receivable_id.id)]
        elif partner_type == 'payable':
            domain += [('account_id', '=', partner.property_account_payable_id.id)]
        else:
            domain += ['|',
                    ('account_id', '=', partner.property_account_receivable_id.id),
                    ('account_id', '=', partner.property_account_payable_id.id)]

        if moves_status == "posted":
            domain += [('parent_state', 'not in', ['draft', 'cancel'])]

        if journals:
            domain += [('journal_id', 'in', journals.ids)]

        if sales_person:
            domain += [('move_id.invoice_user_id', 'in', sales_person.ids)]

        moves = self.env['account.move.line'].search(domain)

        total_balance = 0.0
        for mov in moves:
            if mov.currency_id.id == currency.id:
                total_balance += mov.balance
            else:
                total_balance += mov.currency_id._convert(mov.balance, currency, company, date)
        return round(total_balance, 2)

    def _get_move_data(self, partner):
        # Reuse the existing _get_move method from the report model
        report_model = self.env['report.tkn_adv_partner_ledger.report_customer_card']
        # Currency Report
        moves = report_model._get_move(
            self.date_start,
            self.date_end,
            partner,
            self.journal_ids,
            self.sales_person_ids,
            self.moves_status,
            self.currency_id,
            self.company_id,
            self.partner_type,
        )

        if moves:
            # Enhance the data with additional information for the view
            for move in moves:
                # Add document references
                if move.get('flag') == 'invoice':
                    invoice = self.env['account.move'].search([('name', '=', move.get('num'))], limit=1)
                    if invoice:
                        move['invoice_id'] = invoice.id
                        move['move_id'] = invoice.id
                elif move.get('flag') == 'payment':
                    payment = self.env['account.payment'].search([('name', '=', move.get('num'))], limit=1)
                    if payment:
                        move['payment_id'] = payment.id
                elif move.get('flag') == 'entry':
                    entry = self.env['account.move'].search([('name', '=', move.get('num'))], limit=1)
                    if entry:
                        move['move_id'] = entry.id

        return moves
