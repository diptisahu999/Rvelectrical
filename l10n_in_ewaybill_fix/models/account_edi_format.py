# -*- coding: utf-8 -*-
from odoo import models

class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _get_l10n_in_edi_ewaybill_line_details(self, line, line_tax_details, sign):
        # Call super to get the original dictionary (though we're about to modify it, 
        # normally we'd call super but here we want to patch a specific line within the logic that super doesn't expose easily without re-writing the whole method
        # However, to be cleaner, we can just call super and then 'fix' the one specific key.
        
        # Original method returns a dict.
        res = super()._get_l10n_in_edi_ewaybill_line_details(line, line_tax_details, sign)
        
        # Apply the fix: Ensure qtyUnit is max 3 chars
        qty_unit = res.get('qtyUnit', 'OTH')
        if len(qty_unit) > 3:
            # Attempt to extract from UOM if possible, otherwise default to OTH
            uom_code = line.product_uom_id.l10n_in_code
            if uom_code:
                code_part = uom_code.split("-")[0]
                if len(code_part) <= 3:
                    res['qtyUnit'] = code_part
                else:
                    res['qtyUnit'] = 'OTH'
            else:
                res['qtyUnit'] = 'OTH'
        
        return res
