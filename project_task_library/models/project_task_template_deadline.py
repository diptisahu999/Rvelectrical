from odoo import models, fields, api
from datetime import timedelta
import re
from odoo.exceptions import ValidationError


# -------------------------
# 🧩 STEP 1: SHARED DEADLINE CALCULATOR
# -------------------------

class DeadlineCalculationMixin(models.AbstractModel):
    _name = 'deadline.calculation.mixin'
    _description = 'Shared deadline calculation logic'

    def _calculate_deadline_from_days(self, days_deadline):
        if not days_deadline:
            return False

        match = re.search(r'\d+', days_deadline)
        if not match:
            return False

        days = int(match.group())
        current = fields.Date.context_today(self)
        added = 0

        while added < days:
            current += timedelta(days=1)
            if current.weekday() != 6:  # NOT Sunday
                added += 1

        return current



# -------------------------
# 🧩 STEP 2: PROJECT TASK TEMPLATE (PARENT)
# -------------------------

class ProjectTaskTemplate(models.Model, DeadlineCalculationMixin):
    _inherit = 'project.task.template'

    @api.onchange('days_deadline')
    def _onchange_days_deadline(self):
        for project in self:
            # 🔹 ALWAYS reset first (important)
            project.date_deadline = False

            if not project.days_deadline:
                continue

            # 🔹 Recalculate parent date (even if same days re-entered)
            project.date_deadline = project._calculate_deadline_from_days(
                project.days_deadline
            )

            # 🔹 Sync children immediately (UI-time)
            for sub in project.subtask_template_ids:

                # Rule 3: child empty → inherit parent
                if not sub.days_deadline:
                    sub.days_deadline = project.days_deadline
                    sub.date_deadline = project.date_deadline
                    continue

                # Rule 4: child previously same as parent → update
                if (
                    sub.days_deadline == project._origin.days_deadline
                    and sub.date_deadline == project._origin.date_deadline
                ):
                    sub.days_deadline = project.days_deadline
                    sub.date_deadline = project.date_deadline


    @api.model
    def create(self, vals):
        if vals.get('days_deadline'):
            vals['date_deadline'] = self._calculate_deadline_from_days(
                vals.get('days_deadline')
            )
        return super().create(vals)

    # def write(self, vals):
    #     # 🔥 If days_deadline is changing, force recompute date_deadline
    #     if 'days_deadline' in vals:
    #         for record in self:
    #             new_date = record._calculate_deadline_from_days(
    #                 vals.get('days_deadline')
    #             )
    #             vals['date_deadline'] = new_date

    #     res = super().write(vals)

    #     # 🔥 Now sync children AFTER parent is saved
    #     if 'days_deadline' in vals:
    #         for project in self:
    #             project._sync_subtasks_deadline()

    #     return res

    def write(self, vals):
        # 🔒 prevent infinite loop
        if self.env.context.get('skip_deadline_recalc'):
            return super().write(vals)

        # recompute date BEFORE write
        if 'days_deadline' in vals:
            vals['date_deadline'] = self._calculate_deadline_from_days(
                vals.get('days_deadline')
            )

        res = super(
            ProjectTaskTemplate,
            self.with_context(skip_deadline_recalc=True)
        ).write(vals)

        # sync subtasks AFTER save
        for project in self:
            project._sync_subtasks_deadline()

        return res

    def _sync_subtasks_deadline(self):
        self.ensure_one()

        for sub in self.subtask_template_ids:

            # CASE 1: child days EMPTY → FORCE update
            if not sub.days_deadline:
                sub.write({
                    'days_deadline': self.days_deadline,
                    'date_deadline': self.date_deadline,
                })
                continue

            # CASE 2: child SAME as parent → update
            if (
                sub.days_deadline == self.days_deadline
                and sub.date_deadline == self.date_deadline
            ):
                sub.write({
                    'days_deadline': self.days_deadline,
                    'date_deadline': self.date_deadline,
                })


# -------------------------
# 🧩 STEP 3: SUB-TASK TEMPLATE (CHILD)
# -------------------------

class ProjectSubtaskTemplate(models.Model, DeadlineCalculationMixin):
    _inherit = 'project.subtask.template'

    def _apply_project_deadline(self, days, date):
        self.write({
            'days_deadline': days,
            'date_deadline': date,
        })

    
    # ONCHANGE
    @api.onchange('days_deadline')
    def _onchange_days_deadline(self):
        for sub in self:
            # Always reset first
            sub.date_deadline = False

            if sub.days_deadline:
                sub.date_deadline = sub._calculate_deadline_from_days(
                    sub.days_deadline
                )

    
    # -------------------------
    # OVERRIDE CREATE
    # -------------------------
    @api.model
    def create(self, vals):
        # 🔹 Case 1: User entered days manually
        if vals.get('days_deadline'):
            vals['date_deadline'] = self._calculate_deadline_from_days(
                vals.get('days_deadline')
            )

        sub = super().create(vals)

        # 🔹 Case 2: Inherit from parent ONLY if child days empty
        if (
            not vals.get('days_deadline')
            and sub.task_template_id
            and sub.task_template_id.days_deadline
        ):
            sub.write({
                'days_deadline': sub.task_template_id.days_deadline,
                'date_deadline': sub.task_template_id.date_deadline,
            })

        return sub


    # -------------------------
    # OVERRIDE WRITE
    # -------------------------
    def write(self, vals):
        # 🔥 If days change, ALWAYS recalc date
        if 'days_deadline' in vals:
            vals['date_deadline'] = (
                self._calculate_deadline_from_days(vals.get('days_deadline'))
                if vals.get('days_deadline')
                else False
            )

        return super().write(vals)
    
    # -------------------------
    # VALIDATIONS
    # -------------------------
    @api.constrains('days_deadline', 'task_template_id')
    def _check_child_days_vs_parent(self):
        for sub in self:

            # If child has no days → nothing to validate
            if not sub.days_deadline:
                continue

            parent = sub.task_template_id
            if not parent:
                continue

            # 🔴 Rule 2: Parent days empty, child has days
            if not parent.days_deadline:
                raise ValidationError(
                    "You cannot set Sub-task Deadline Days "
                    "because the Parent Task has no Deadline Days."
                )

            # Extract numbers safely
            parent_days = int(re.search(r'\d+', parent.days_deadline).group())
            child_days = int(re.search(r'\d+', sub.days_deadline).group())

            # 🔴 Rule 1: Child days > Parent days
            if child_days > parent_days:
                raise ValidationError(
                    "Sub-task Deadline Days cannot be greater than "
                    "Parent Task Deadline Days.\n\n"
                    f"Parent Days: {parent_days}\n"
                    f"Sub-task Days: {child_days}"
                )
