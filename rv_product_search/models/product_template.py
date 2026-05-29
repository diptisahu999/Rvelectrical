from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """Override to also search by product attribute values.

        When a user types an attribute value (e.g., "590") in the search bar,
        this will also find products that have matching attribute values,
        not just matching product names or internal references.
        """
        res = super()._name_search(
            name=name, domain=domain, operator=operator,
            limit=limit, order=order
        )

        if name and operator in ('ilike', 'like', '=ilike', '=like', '=', '!='):
            # Search for products that have matching attribute values
            # This searches through:
            #   product.template -> attribute_line_ids -> value_ids -> name
            attr_domain = [
                ('attribute_line_ids.value_ids.name', operator, name)
            ]
            if domain:
                attr_domain += list(domain)

            attr_product_ids = self._search(attr_domain, limit=limit, order=order)

            # Combine results, avoiding duplicates
            if attr_product_ids:
                existing_ids = set(res)
                for pid in attr_product_ids:
                    if pid not in existing_ids:
                        res.append(pid)

        return res

