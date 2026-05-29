# -*- coding: utf-8 -*-

import time
from odoo import models, fields, api
from num2words import num2words

dict_total = 0.0


class AdvancePartnerLedger(models.AbstractModel):
    _name = 'report.tkn_adv_partner_ledger.report_customer_card'

    def _get_company(self, form):
        company = form['company_id']

        company_name = company[1]

        return company_name

    def _get_start_date(self, form):
        date_start = form['date_start']
        return date_start

    def _get_end_date(self, form):
        date_end = form['date_end']
        return date_end

    def _get_balance(self, partner, date, journals, sales_person, moves_status, currency, company, partner_type=None):
        if not date:
            return 0.0
        company_currency = company.currency_id
        # domain = [('partner_id', '=', partner.id),
        #           ('date', '<', date),
        #           '|',
        #           ('account_id', '=', partner.property_account_receivable_id.id),
        #           ('account_id', '=', partner.property_account_payable_id.id)]

        domain = [('partner_id', '=', partner.id),
          ('date', '<', date)]

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

    def _get_currant_balance(self, partner, date_from, date_to, journals, sales_person, moves_status, currency, company, partner_type=None):
        company_currency = company.currency_id
        today = fields.Date.today()
        # domain = [('partner_id', '=', partner.id),
        #           ('date', '>=', date_from),
        #           ('date', '<=', date_to),
        #           '|',
        #           ('account_id', '=', partner.property_account_receivable_id.id),
        #           ('account_id', '=', partner.property_account_payable_id.id)]

        domain = [('partner_id', '=', partner.id),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to)]

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
            move_currency = mov.currency_id or company_currency

            if move_currency == currency:
                # if amount is in the same currency
                if mov.amount_currency and mov.currency_id:
                    total_balance += mov.amount_currency
                else:
                    total_balance += mov.balance
            else:
                # If the currency is different, we need to make a conversion.
                amount_to_convert = mov.amount_currency if mov.currency_id else mov.balance
                source_currency = mov.currency_id if mov.currency_id else company_currency

                converted = source_currency._convert(amount_to_convert, currency, company, today)
                total_balance += converted

        return round(total_balance, 2)

    def _get_move(self, date_start, date_end, partner_id, journal_ids, sales_person_ids, moves_status, currency_id, company_id, partner_type=None):
        list_move = []
        res = {}
        obj_inv = self.env["account.move"]
        obj_pay = self.env["account.payment"]
        obj_entry = self.env["account.move.line"]

        # Invoice Domain
        inv_domain = [
            ('move_type', '!=', 'entry'),
            ("partner_id", "=", partner_id.id)
        ]

        # Payment Domain
        pay_domain = [
            ("partner_id", "=", partner_id.id)
        ]

        # Journal Entry Domain
        entery_domain = [
            ('partner_id', '=', partner_id.id),
            ("payment_id", "=", False),
        ]

        # Check For Journals
        if journal_ids:
            inv_domain = [("journal_id", "in", journal_ids.ids), ] + inv_domain
            pay_domain = [("journal_id", "in", journal_ids.ids), ] + pay_domain
            entery_domain = [("journal_id", "in", journal_ids.ids), ] + entery_domain

        # Check For Sales Person
        if sales_person_ids:
            inv_domain = [("invoice_user_id", "in", sales_person_ids.ids), ] + inv_domain
            entery_domain = [("move_id.invoice_user_id", "in", sales_person_ids.ids), ] + entery_domain

        # check Status
        if moves_status == "posted":
            inv_domain = [('state', 'not in', ['draft', 'cancel']), ] + inv_domain
            pay_domain = [('state', 'not in', ['draft', 'cancelled']), ] + pay_domain
            entery_domain = [('parent_state', 'in', ['posted', 'post']), ] + entery_domain

        # Check For Date Start
        if date_start:
            inv_domain = [("invoice_date", ">=", date_start), ] + inv_domain
            pay_domain = [("date", ">=", date_start), ] + pay_domain
            entery_domain = [("date", ">=", date_start), ] + entery_domain

        # Check For Date End
        if date_end:
            inv_domain = [("invoice_date", "<=", date_end), ] + inv_domain
            pay_domain = [("date", "<=", date_end), ] + pay_domain
            entery_domain = [("date", "<=", date_end), ] + entery_domain

        inv_ids = obj_inv.sudo().search(inv_domain, order="invoice_date")
        entery_domain = [("move_id", "not in", inv_ids.ids), ] + entery_domain
        
        if partner_type == 'receivable':
            entery_domain += [('account_id', '=', partner_id.property_account_receivable_id.id)]
            inv_ids = inv_ids.filtered(lambda m: m.move_type in [
                'out_invoice', 'out_refund', 'out_receipt'
            ])
        elif partner_type == 'payable':
            entery_domain += [('account_id', '=', partner_id.property_account_payable_id.id)]
            inv_ids = inv_ids.filtered(lambda m: m.move_type in [
                'in_invoice', 'in_refund', 'in_receipt'
            ])
        else:
            entery_domain += ['|',
                            ('account_id', '=', partner_id.property_account_receivable_id.id),
                            ('account_id', '=', partner_id.property_account_payable_id.id)]


        p_balance = self._get_balance(partner_id, date_start, journal_ids, sales_person_ids, moves_status, currency_id, company_id)
        entries = obj_entry.search(entery_domain, order="date")
        for ent in entries:
            if ent.credit > 0:
                res = {
                    "date": ent.date,
                    "num": ent.move_id.name,
                    "type": "Journal Entry",
                    "inv_type": ent.move_id.journal_id.display_name,
                    "lines": False,
                    "credit": ent.credit if ent.currency_id.id == currency_id.id else ent.currency_id._convert(ent.credit, currency_id, company_id, ent.date),
                    "origin": ent.ref,
                    "debit": 0,
                    "flag": 'entry',
                    "currency": ent.currency_id.name,
                    "balance": p_balance - ent.credit,
                }

            if ent.debit > 0:
                res = {
                    "date": ent.date,
                    "num": ent.move_id.name,
                    "type": "Journal Entry",
                    "inv_type": ent.move_id.journal_id.display_name,
                    "lines": False,
                    "credit": 0,
                    "origin": ent.ref,
                    "debit": ent.debit if ent.currency_id.id == currency_id.id else ent.currency_id._convert(ent.debit, currency_id, company_id, ent.date),
                    "flag": 'entry',
                    "currency": ent.currency_id.name,
                    "balance": p_balance + ent.debit,
                }

            list_move.append(res)
        payment_ids = obj_pay.search(pay_domain, order="date")
        if partner_type == 'receivable':
            payment_ids = payment_ids.filtered(lambda p: p.partner_type == 'customer')
        elif partner_type == 'payable':
            payment_ids = payment_ids.filtered(lambda p: p.partner_type == 'supplier')

        for pay in payment_ids:

            # IF Salesperson Not Show Payments
            # if sales_person_ids:
            #     continue

            if pay.payment_type == 'inbound':
                pay_res = {
                    "date": pay.date,
                    "num": pay.name if pay.name else '/',
                    "type": 'Payment',
                    "inv_type": 'Payment Receipt',
                    "lines": False,
                    "credit": abs(pay.amount) if pay.currency_id.id == currency_id.id else pay.currency_id._convert(pay.amount, currency_id, company_id, pay.date),
                    "origin": pay.memo,
                    "debit": 0,
                    "flag": 'payment',
                    "currency": pay.currency_id.name,
                    "balance": p_balance - abs(pay.amount),
                }

            elif pay.payment_type == 'outbound':
                pay_res = {
                    "date": pay.date,
                    "num": pay.name if pay.name else '/',
                    "type": 'Payment',
                    "inv_type": 'Payment Disbursement',
                    "lines": False,
                    "credit": 0,
                    "origin": pay.memo,
                    "debit": pay.amount if pay.currency_id.id == currency_id.id else pay.currency_id._convert(pay.amount, currency_id, company_id, pay.date),
                    "flag": 'payment',
                    "currency": pay.currency_id.name,
                    "balance": p_balance + pay.amount,
                }
            else:
                if pay.partner_type == 'customer':
                    pay_res = {
                        "date": pay.date,
                        "num": pay.name if pay.name else '/',
                        "type": 'Payment',
                        "inv_type": 'Payment Receipt',
                        "lines": False,
                        "credit": abs(pay.amount) if pay.currency_id.id == currency_id.id else pay.currency_id._convert(pay.amount, currency_id, company_id, pay.date),
                        "origin": pay.memo,
                        "debit": 0,
                        "flag": 'payment',
                        "currency": pay.currency_id.name,
                        "balance": p_balance - abs(pay.amount),
                    }

                else:
                    pay_res = {
                        "date": pay.date,
                        "num": pay.name if pay.name else '/',
                        "type": 'Payment',
                        "inv_type": 'Payment Disbursement',
                        "lines": False,
                        "credit": 0,
                        "origin": pay.memo,
                        "debit": pay.amount if pay.currency_id.id == currency_id.id else pay.currency_id._convert(pay.amount, currency_id, company_id, pay.date),
                        "flag": 'payment',
                        "currency": pay.currency_id.name,
                        "balance": p_balance + pay.amount,
                    }

            list_move.append(pay_res)
        for inv in inv_ids:
            total_pay = inv.amount_total - inv.amount_residual

            if inv.move_type == 'out_refund':
                inv_res = {
                    "date": inv.invoice_date,
                    "num": inv.name if inv.state == 'posted' else '/',
                    "type": 'Credit Notes',
                    "inv_type": 'out_ref',
                    "lines": inv.invoice_line_ids,
                    "credit": inv.amount_total if inv.currency_id.id == currency_id.id else inv.currency_id._convert(inv.amount_total, currency_id, company_id, inv.invoice_date),
                    "total_amount": inv.amount_total,
                    "residual": inv.amount_residual,
                    "total_pay": total_pay,
                    "debit": 0,
                    "flag": 'invoice',
                    "origin": inv.invoice_origin,
                    "currency": inv.currency_id.name,
                    "balance": p_balance - inv.amount_total,

                }

            if inv.move_type == 'in_refund':
                inv_res = {
                    "date": inv.invoice_date,
                    "num": inv.name if inv.state == 'posted' else '/',
                    "type": 'Vendor Refund',
                    "inv_type": 'in_ref',
                    "lines": inv.invoice_line_ids,
                    "credit": False,
                    "total_amount": inv.amount_total,
                    "residual": inv.amount_residual,
                    "total_pay": total_pay,
                    "debit": inv.amount_total if inv.currency_id.id == currency_id.id else inv.currency_id._convert(inv.amount_total, currency_id, company_id, inv.invoice_date),
                    "flag": 'invoice',
                    "origin": inv.invoice_origin,
                    "currency": inv.currency_id.name,
                    "balance": p_balance + inv.amount_total,
                }

            if inv.move_type == 'out_invoice':
                inv_res = {
                    "date": inv.invoice_date,
                    "num": inv.name if inv.state == 'posted' else '/',
                    "type": 'Customer Invoice',
                    "inv_type": 'out_inv',
                    "lines": inv.invoice_line_ids,
                    "credit": False,
                    "debit": inv.amount_total if inv.currency_id.id == currency_id.id else inv.currency_id._convert(inv.amount_total, currency_id, company_id, inv.invoice_date),
                    "total_amount": inv.amount_total,
                    "residual": inv.amount_residual,
                    "total_pay": total_pay,
                    "flag": 'invoice',
                    "origin": inv.invoice_origin,
                    "currency": inv.currency_id.name,
                    "balance": p_balance + inv.amount_total,

                }
            if inv.move_type == 'in_invoice':
                inv_res = {
                    "date": inv.invoice_date,
                    "num": inv.name if inv.state == 'posted' else '/',
                    "type": 'Vendor Bill',
                    "inv_type": 'in_inv',
                    "lines": inv.invoice_line_ids,
                    "credit": inv.amount_total if inv.currency_id.id == currency_id.id else inv.currency_id._convert(inv.amount_total, currency_id, company_id, inv.invoice_date),
                    "debit": False,
                    "total_amount": inv.amount_total,
                    "residual": inv.amount_residual,
                    "total_pay": total_pay,
                    "flag": 'invoice',
                    "origin": inv.invoice_origin,
                    "currency": inv.currency_id.name,
                    "balance": p_balance - inv.amount_total,
                }
            #  Receipt
            if inv.move_type == 'out_receipt':
                inv_res = {
                    "date": inv.invoice_date,
                    "num": inv.name  if inv.state == 'posted' else '/',
                    "type": 'Sale Receipt',
                    "inv_type": 'out_rec',
                    "lines": inv.invoice_line_ids,
                    "credit": False,
                    "debit": inv.amount_total if inv.currency_id.id == currency_id.id else inv.currency_id._convert(inv.amount_total, currency_id, company_id, inv.invoice_date),
                    "total_amount": inv.amount_total,
                    "residual": inv.amount_residual,
                    "total_pay": total_pay,
                    "flag": 'invoice',
                    "origin": inv.invoice_origin,
                    "currency": inv.currency_id.name,
                    "balance": p_balance + inv.amount_total,

                }
            if inv.move_type == 'in_receipt':
                inv_res = {
                    "date": inv.invoice_date,
                    "num": inv.name if inv.state == 'posted' else '/',
                    "type": 'Purchase Receipt',
                    "inv_type": 'in_inv',
                    "lines": inv.invoice_line_ids,
                    "credit": inv.amount_total if inv.currency_id.id == currency_id.id else inv.currency_id._convert(inv.amount_total, currency_id, company_id, inv.invoice_date),
                    "debit": False,
                    "total_amount": inv.amount_total,
                    "residual": inv.amount_residual,
                    "total_pay": total_pay,
                    "flag": 'invoice',
                    "origin": inv.invoice_origin,
                    "currency": inv.currency_id.name,
                    "balance": p_balance - inv.amount_total,
                }

            list_move.append(inv_res)
        if list_move:
            list_move.sort(key=lambda item: item['date'], reverse=False)
            newlist = list_move
            for rec in newlist:
                if rec.get('debit'):
                    rec.update({'balance': rec.get('debit') + p_balance})
                    p_balance += rec.get('debit')
                else:
                    rec.update({'balance': p_balance - rec.get('credit')})
                    p_balance -= rec.get('credit')

            return newlist

    def _get_total(self, lst):
        total = {'t_qty': 0.0, 't_price': 0.0, 't_total': 0.0, 't_in': 0.0, 't_out': 0.0, 't_bal': 0.0}
        for rec in lst:
            total['t_qty'] += rec['move_qty']
            total['t_price'] += rec['price_unit']
            total['t_total'] += rec['value']
            if rec['flag'] == 'in':
                total['t_in'] += rec['in']
            if rec['flag'] == 'out':
                total['t_out'] += rec['out']
            total['t_bal'] = lst[-1]['balance']
        return total

    def _get_balance_in_words(self, balance, currency):
        """ Convert numeric balance to words using num2words. """
        currency = currency
        total_amount = balance
        amount = int(total_amount)
        subunit_amount = round((total_amount - amount) * 1000)

        amount_in_words = num2words(amount).capitalize()
        amount_word_arabic = f"Only {amount_in_words} {currency.full_name} and {subunit_amount} {currency.currency_subunit_label}"
        return amount_word_arabic

    @api.model
    def _get_report_values(self, docids, data=None):
        if data:
            user = data['form']['create_uid'][1]

            model = self.env.context.get('active_model')
            docs = self.env[model].browse(self.env.context.get('active_id'))
            # multiple partner
            partner_ids = data['form'].get('partner_ids', [])
            partners = self.env['res.partner'].browse([pid for pid in partner_ids])

            stock_report = self.env['ir.actions.report']._get_report_from_name(
                'customer_card_report.report_customer_card')

            # Balance In Word
            # balance = self._get_currant_balance(docs.partner_id, docs.currency_id, docs.company_id)
            # balance_in_words = self._get_balance_in_words(balance, docs.currency_id)

            return {
                'doc_ids': docids,
                'doc_model': stock_report.model,
                'docs': docs,
                'partners': partners,
                "today": str(fields.Date.today()),
                "user": user,
                "get_company": self._get_company(data['form']),
                "start_date": self._get_start_date(data['form']),
                "end_date": self._get_end_date(data['form']),
                "get_move": self._get_move,
                "get_total": self._get_total,
                "balance": self._get_balance,
                "all_balance": self._get_currant_balance,
                # "balance_in_words": balance_in_words,
            }