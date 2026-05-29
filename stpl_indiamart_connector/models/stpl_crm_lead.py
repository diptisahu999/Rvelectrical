##############################################################################
# 
# Odoo Proprietary License v1.0
# 
# This software and associated files (the "Software") may only be used (executed)
#  if you have purchased a valid license from the authors, typically via Odoo 
#  Apps, or if you have received a written agreement from the authors of the 
#  Software (see the COPYRIGHT file). 
# 
# You may develop Odoo modules that use the Software as a library (typically 
#  by depending on it, importing it and using its resources), but without 
# copying any source code or material from the Software. 
# You may distribute those modules under the license of your choice, provided 
# that this license is compatible with the terms of the Odoo Proprietary License 
# (For example: LGPL, MIT, or proprietary licenses similar to this one). 
# 
# It is forbidden to modify, upgrade, publish, distribute, sublicense, or sell 
# copies of the Software or modified copies of the Software. 
# 
# The above copyright notice and this permission notice must be included in all 
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
# 
##############################################################################
'''
    Import Libraries
'''
from odoo import api, fields, models, _
from datetime import datetime
import logging
import pytz

_logger = logging.getLogger(__name__)


class CrmLeadInherit(models.Model):
    '''
        Interited CRM Lead
    '''
    _inherit = 'crm.lead'

    lead_history_id = fields.Many2one('crm.indiamart.history', string="Lead History Id")
    is_indiamart = fields.Boolean("Indiamart")
    indiamart_query_id = fields.Char('IndiaMart Query Id')

    @api.depends('user_id')
    def _compute_date_open(self):
        for lead in self:
            if not lead.is_indiamart:
                lead.date_open = fields.Datetime.now() if lead.user_id else False

    def call_stpl_indiamart_connector(self):
        '''
        Function from stpl indiamart cron
        '''

        ist = pytz.timezone('Asia/Kolkata')
        current_utc_datetime = datetime.now(pytz.utc)
        current_ist_datetime = current_utc_datetime.astimezone(ist).replace(tzinfo=None)

        company_ids = self.env['res.company'].sudo().search([
            ('is_indiamart', '=', True),
            ('indiamart_mobile', '!=', False),
            ('indiamart_api_key', '!=', False),
        ])
        for company_id in company_ids:
            if company_id.last_fetch_update_time:
                utc_time = pytz.utc.localize(company_id.last_fetch_update_time)
                start_datetime = utc_time.astimezone(ist).replace(tzinfo=None)
                end_datetime = current_ist_datetime
            else:
                start_datetime = False
                end_datetime = False
            company_id.get_response_and_create_rec(start_datetime, end_datetime, current_ist_datetime)
