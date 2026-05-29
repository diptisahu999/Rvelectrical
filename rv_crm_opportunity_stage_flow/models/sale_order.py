from odoo import models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    # 🔁 Sync Opportunity stage based on product existence
    def _sync_opportunity_stage_by_products(self):
        # 1. Fetch Stages
        quotation_stage = self.env["crm.stage"].with_context(lang=None).search(
            [("name", "=", "Quotation")], limit=1
        )
        new_stage = self.env["crm.stage"].with_context(lang=None).search(
            [("name", "=", "New")], limit=1
        )
        won_stage = self.env["crm.stage"].search(
            [("is_won", "=", True)], limit=1
        )

        # 2. Key: Iterate over distinct opportunities to check holistic status
        opportunities = self.mapped('opportunity_id')
        
        for opportunity in opportunities:
            # Get ALL relevant orders for this opportunity (not just self)
            all_orders = self.env['sale.order'].search([
                ('opportunity_id', '=', opportunity.id),
                ('state', 'in', ['draft', 'sent', 'sale'])
            ])

            # A. If any order is CONFIRMED, ensure it's WON (or keep it there)
            # This protects Won opportunities from being downgraded by a draft edit.
            if any(o.state == 'sale' for o in all_orders):
                 if won_stage and opportunity.stage_id.id != won_stage.id:
                     opportunity.stage_id = won_stage.id
                 continue

            # B. Check for products across ANY draft/sent order
            has_product = any(
                line.product_id 
                for o in all_orders 
                for line in o.order_line
            )

            # C. Apply Logic
            if has_product and quotation_stage:
                # Promote → Quotation (or stay)
                if opportunity.stage_id.id != quotation_stage.id:
                    opportunity.stage_id = quotation_stage.id

            elif not has_product and new_stage:
                # Downgrade → New
                if opportunity.stage_id.id != new_stage.id:
                    opportunity.stage_id = new_stage.id


    # 1️⃣ Create quotation
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._sync_opportunity_stage_by_products()
        return orders
    

    # 2️⃣ Edit quotation (add/remove products + save / send)
    def write(self, vals):
        res = super().write(vals)

        if "order_line" in vals or "state" in vals:
            self._sync_opportunity_stage_by_products()

        return res
    

    # 3️⃣ Confirm Sales Order → Opportunity → Won
    def action_confirm(self):
        res = super().action_confirm()

        won_stage = self.env["crm.stage"].search(
            [("is_won", "=", True)],
            limit=1
        )

        for order in self:
            if order.opportunity_id and won_stage:
                order.opportunity_id.write({
                    "stage_id": won_stage.id,
                    "probability": 100,
                })

        return res
    

    # 4️⃣ Cancel Sales Order → Opportunity → Quotation
    def action_cancel(self):
        res = super().action_cancel()

        quotation_stage = self.env["crm.stage"].with_context(lang=None).search(
            [("name", "=", "Quotation")],
            limit=1
        )

        for order in self:
            if order.opportunity_id and quotation_stage:
                order.opportunity_id.write({
                    "stage_id": quotation_stage.id,
                    "probability": 0,
                })

        return res
    

    # 5️⃣ Delete quotation → Opportunity → New
    def unlink(self):
        opportunities = self.mapped("opportunity_id")

        res = super().unlink()

        if opportunities:
            new_stage = self.env["crm.stage"].with_context(lang=None).search(
                [("name", "=", "New")],
                limit=1
            )
            if new_stage:
                opportunities.write({
                    "stage_id": new_stage.id,
                    "probability": 0,
                })

        return res
