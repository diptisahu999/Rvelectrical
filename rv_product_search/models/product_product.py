from odoo import models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """Override to also search by product attribute values.

        When a user types an attribute value (e.g., "590") in the search bar,
        this will also find product variants that have matching attribute values.
        """
        res = super()._name_search(
            name=name, domain=domain, operator=operator,
            limit=limit, order=order
        )

        if name and operator in ('ilike', 'like', '=ilike', '=like', '=', '!='):
            # Search for product variants that have matching attribute values
            attr_domain = [
                ('product_template_attribute_value_ids.name', operator, name)
            ]
            if domain:
                attr_domain += list(domain)

            attr_product_ids = self._search(attr_domain, limit=limit, order=order)

            if attr_product_ids:
                existing_ids = set(res)
                for pid in attr_product_ids:
                    if pid not in existing_ids:
                        res.append(pid)

        return res
