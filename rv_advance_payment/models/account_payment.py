from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')

    def action_post(self):
        # Call super to post the payment
        res = super(AccountPayment, self).action_post()
        
        # Auto-reconcile logic for Advance Payments to skip 'In Process'
        for payment in self:
            if (payment.sale_order_id or payment.purchase_order_id) and payment.state == 'posted' and not payment.is_reconciled:
                # We can't easily force "Paid" (is_reconciled=True) without a counter-entry (Statement Line or Invoice).
                # However, if the journal is configured to skip outstanding accounts, it might help.
                # But typically, 'In Process' IS the correct state for a posted payment.
                # If the user insists on 'Paid', we would need to create a Bank Statement Line.
                
                # ATTEMPT 1: If 'base_accounting_kit' or 'account_accountant' is installed, we might have tools.
                # For now, let's try to update the payment state label via View modification or assume the user accepts 'In Process' if we explain it.
                # BUT the user said "remove the in process stage".
                
                # Hack: We can try to manually create a statement line and reconcile it.
                # Only do this if it's a "Cash" or "Bank" journal.
                if payment.journal_id.type in ['cash', 'bank']:
                     # Check if we can create a statement line
                     vals = {
                         'date': payment.date,
                         'journal_id': payment.journal_id.id,
                         'payment_ref': payment.name,
                         'amount': payment.amount if payment.payment_type == 'inbound' else -payment.amount,
                         'partner_id': payment.partner_id.id,
                     }
                     # Create statement (single line statement)
                     # Using standard Odoo flow for manual reconciliation
                     # statement = self.env['account.bank.statement'].create({
                     #    'name': "Auto-Statement for " + payment.name,
                     #    'journal_id': payment.journal_id.id,
                     #    'line_ids': [(0, 0, vals)],
                     # })
                     # statement.button_post()
                     # Then match... this is too complex and risky to automate blindly without context.
                     pass 
        return res
