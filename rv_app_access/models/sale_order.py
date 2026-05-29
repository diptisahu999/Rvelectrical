from odoo import models, api, _
from odoo.exceptions import UserError, AccessError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_invoices(self, grouped=False, final=False, date=None):
        if self.env.user.has_group('rv_app_access.group_restricted_sales_access'):
            raise UserError(_("You are not allowed to create invoices."))
        return super(SaleOrder, self)._create_invoices(grouped=grouped, final=final, date=date)

    def action_view_sale_advance_payment_inv(self):
        if self.env.user.has_group('rv_app_access.group_restricted_sales_access'):
            raise UserError(_("You are not allowed to create invoices."))
        return super(SaleOrder, self).action_view_sale_advance_payment_inv()

    def action_view_invoice(self):
        if self.env.user.has_group('rv_app_access.group_restricted_sales_access'):
            raise AccessError(_("You do not have access to view invoices."))
        return super(SaleOrder, self).action_view_invoice()

    def unlink(self):
        if not (self.env.user.has_group('rv_app_access.group_sales_crm_delete') or self.env.user.has_group('sales_team.group_sale_manager')):
            raise AccessError(_("You are not allowed to delete Sales entries."))
        return super(SaleOrder, self).unlink()
