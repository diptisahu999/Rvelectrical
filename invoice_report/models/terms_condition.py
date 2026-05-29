from odoo import fields, models


class TermsAndConditions(models.Model):
    _name = "terms.and.conditions"
    _description = "Temrs And Conditions"

    name = fields.Char("Name")
    terms_condition = fields.Html("Terms and Conditions")
