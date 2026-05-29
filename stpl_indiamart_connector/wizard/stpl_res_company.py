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
from datetime import datetime, tzinfo
from odoo.exceptions import UserError
import pytz
from pytz import timezone


class ResCompany(models.TransientModel):
    '''
        created Wizard Res Company
    '''
    _name = 'res.company.wizard'
    _description = 'crm.indiamart.history'

    start_datetime = fields.Datetime(string='Start Datetime')
    end_datetime = fields.Datetime(string='End Datetime')

    def get_manual_response(self):
        '''
        Function for fetching manual response of given time duration
        '''

        if self.start_datetime and self.end_datetime:
            # Convert user-entered datetime to IST for API Call
            ist = pytz.timezone('Asia/Kolkata')
            start_datetime_ist = self.start_datetime.astimezone(ist).replace(tzinfo=None)
            end_datetime_ist = self.end_datetime.astimezone(ist).replace(tzinfo=None)

            current_utc_datetime = datetime.now(pytz.utc)
            current_ist_datetime = current_utc_datetime.astimezone(ist).replace(tzinfo=None)

            self.start_datetime = start_datetime_ist
            self.end_datetime = end_datetime_ist

            # Validate the Datetime range
            if end_datetime_ist <= start_datetime_ist:
                raise UserError(_("End datetime should be greater than Start datetime."))
            elif end_datetime_ist > current_ist_datetime:
                raise UserError(_("End datetime should be less than or equal to Today."))

            company_ids = self.env['res.company'].sudo().search([
                ('id', '=', self.env.context.get('active_id')),
                ('is_indiamart', '=', True),
                ('indiamart_mobile', '!=', False),
                ('indiamart_api_key', '!=', False),
            ])
            if not company_ids:
                raise UserError(_("Please enable the indiamart configuration."))

            company_ids.get_response_and_create_rec(self.start_datetime, self.end_datetime, current_ist_datetime)
