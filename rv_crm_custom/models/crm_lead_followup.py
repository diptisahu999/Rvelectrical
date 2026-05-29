# models/crm_lead_followup.py
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta

class CrmLeadFollowup(models.Model):
    _name = 'crm.lead.followup'
    _description = 'CRM Lead Follow Up'
    _rec_name = 'lead_id'

    lead_id = fields.Many2one(
        'crm.lead',
        required=True,
        ondelete='cascade'
    )
    partner_id = fields.Many2one(related='lead_id.partner_id', string='Customer', store=True)
    user_id = fields.Many2one(related='lead_id.user_id', string='Salesperson', store=True, readonly=True)
    lead_type = fields.Selection(related='lead_id.type', string="Type", store=True)
    outcome = fields.Selection([
        ('continue', 'Continue Follow-up'),
        ('won', 'Deal Done'),
        ('lost', 'Deal Cancelled')
    ], string="Outcome", default='continue')
    note = fields.Char(string="Follow up note")
    create_date = fields.Datetime(readonly=True)
    is_locked = fields.Boolean(
        string='Locked',
        default=False,
        readonly=True
    )
    scheduled_date = fields.Date(string="Scheduled Date", default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Pending'),
        ('done', 'Done')
    ], string='Status', default='draft', required=True)

    # ---------- 1: ALLOW SCHEDULED CREATION ----------
    @api.model
    def create(self, vals):
        # Check type
        is_lead = False
        if vals.get('lead_id'):
            lead = self.env['crm.lead'].browse(vals['lead_id'])
            if lead.type == 'lead':
                is_lead = True
                vals['state'] = 'done'

        # ---------- 1: ALLOW SCHEDULED CREATION (Opportunities) ----------
        if not is_lead and vals.get('state') == 'draft':
            return super().create(vals)
            
        # For done records, require note
        note = (vals.get("note") or "").strip()
        if not note and not is_lead:
             return self.env["crm.lead.followup"]

        # ----------  2: ONE DONE NOTE PER DAY ----------
        today = fields.Date.context_today(self)
        domain = [
            ("lead_id", "=", vals.get("lead_id")),
            ("create_date", ">=", fields.Datetime.to_string(today)),
        ]
        if not is_lead:
            domain.append(("state", "=", "done"))

        exists = self.search(domain, limit=1)

        if exists:
            return self.env["crm.lead.followup"]
        
        vals["is_locked"] = True
            
        return super().create(vals)

    # ---------- 3. ALLOW EDIT FOR PENDING ----------
    def write(self, vals):
        for rec in self:
            if rec.lead_type == 'lead':
                return super(CrmLeadFollowup, rec).write(vals)

        if 'scheduled_date' in vals:
             for rec in self:
                 if vals['scheduled_date'] != rec.scheduled_date:
                     raise UserError("You cannot change the scheduled date of a follow-up.")

        if 'note' in vals:
            vals['note'] = vals['note'].strip()

        is_marking_done = vals.get('state') == 'done'
        
        if is_marking_done:
            today = fields.Date.context_today(self)
            for record in self:
                # 1. Date Restriction
                sc_date = record.scheduled_date
                if sc_date and sc_date > today:
                    raise UserError(f"You cannot complete this follow-up yet. It is scheduled for {sc_date}.")

                # 2. Strict Note Requirement
                note = vals.get('note') if 'note' in vals else record.note
                if not note:
                    raise UserError("A Follow-up note is required to mark as Done.")
                
                vals['is_locked'] = True
                
                # 3. Add Log to Chatter
                record.lead_id.message_post(body=f"Follow-up Done: {note}")

                # 4. Handle Outcome (Only for Opportunities)
                if record.lead_type == 'opportunity':
                     outcome = vals.get('outcome', record.outcome)
                     
                     if outcome == 'won':
                         has_confirmed_order = any(o.state in ['sale', 'done'] for o in record.lead_id.order_ids)
                         if not has_confirmed_order:
                             raise UserError("You cannot mark this deal as Done because there is no Confirmed Order linked to this Opportunity.")

                         record.lead_id.action_set_won()
                         
                         future = self.env['crm.lead.followup'].search([
                             ('lead_id', '=', record.lead_id.id),
                             ('state', '=', 'draft'),
                             ('id', '!=', record.id)
                         ])
                         future.sudo().unlink()
                         
                     elif outcome == 'lost':
                         record.lead_id.action_archive()
                         
                         future = self.env['crm.lead.followup'].search([
                             ('lead_id', '=', record.lead_id.id),
                             ('state', '=', 'draft'),
                             ('id', '!=', record.id)
                         ])
                         future.sudo().unlink()

        return super().write(vals)

    def action_mark_done(self):
        """Button action to mark as done (saves form first)"""
        for rec in self:
            rec.write({'state': 'done'})
    

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    followup_ids = fields.One2many(
        'crm.lead.followup',
        'lead_id',
        string='Follow Ups'
    )

    @api.model
    def create(self, vals):
        res = super(CrmLead, self).create(vals)
        if res.type == 'opportunity':
            res._create_scheduled_followups()
        return res

    def write(self, vals):
        res = super(CrmLead, self).write(vals)
        if 'type' in vals and vals['type'] == 'opportunity':
            for record in self:
                record._create_scheduled_followups()
        return res

    def _create_scheduled_followups(self):
        """Create 4 scheduled followups: Today, Today+3, Today+6, Today+9"""
        self.ensure_one()
        if self.followup_ids:
            return

        base_date = fields.Date.context_today(self)
        offsets = [0, 3, 6, 9]
        
        for days in offsets:
            scheduled_date = base_date + timedelta(days=days)
            self.env['crm.lead.followup'].sudo().create({
                'lead_id': self.id,
                'scheduled_date': scheduled_date,
                'state': 'draft',
                'note': False
            })