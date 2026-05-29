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
import logging
import requests
import json
import pytz

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    '''
        Interited Res Company
    '''
    _inherit = 'res.company'

    indiamart_mobile = fields.Char('IndiaMart Mobile')
    indiamart_api_key = fields.Char('IndiaMart API Key')
    last_fetch_update_time = fields.Datetime('Last Fetch Updated Time')
    indiamart_leads_count = fields.Integer('IndiaMart Leads', compute='compute_indiamart_leads_count')
    is_indiamart = fields.Boolean('IndiaMart')

    _sql_constraints = [
        ('indiamart_mobile_unique', 'unique (indiamart_mobile)', "IndiaMart Mobile already registered.!"),
    ]

    def crm_indiamart_history_action(self):
        '''
        Action for open CRM Lead Views
        '''
        action = self.env.ref('crm.crm_lead_all_leads').read()[0]
        action['domain'] = [('company_id', '=', self.id), ('is_indiamart', '!=', False)]
        return action

    def compute_indiamart_leads_count(self):
        '''
        Compute function for count leads
        '''
        self.indiamart_leads_count = len(self.env['crm.lead'].search([
            ('company_id', '=', self.id),
            ('is_indiamart', '!=', False)
        ]))

    def convert_to_ist(self, datetime_obj):
        """
        Converts a given naive or timezone-aware datetime object to IST (Indian Standard Time).

        Args:
            datetime_obj (datetime): The input datetime, can be naive or timezone-aware.

        Returns:
            datetime: Timezone-aware datetime in IST.
        """
        # Define the IST timezone
        ist = pytz.timezone('Asia/Kolkata')

        # If the datetime is naive (doesn't have timezone info), localize it to IST
        if datetime_obj.tzinfo is None:
            datetime_obj = ist.localize(datetime_obj)  # Localize to IST if naive
        else:
            # If it's already timezone-aware, convert it to IST
            datetime_obj = datetime_obj.astimezone(ist)

        return datetime_obj

    def get_response_and_create_rec(self, start_datetime, end_datetime, current_datetime):
        '''
        Function for getting response through request and creating CRM lead records and history.
        '''
        cron_ref = self.env.ref('stpl_indiamart_connector.stpl_indiamart_connector_cron', raise_if_not_found=False)
        uid = cron_ref.user_id if cron_ref else self.env.ref('base.user_admin')
        user_timezone = pytz.timezone(uid.tz or 'UTC')

        # Calculate the time difference
        local_time = datetime.now(user_timezone)
        time_diff = local_time - datetime.now(pytz.utc)

        for company_id in self:
            lead_ids, duplicated_leads, error, stage = [], [], '', 'error'
            start_datetime, end_datetime = self.prepare_datetime(start_datetime, end_datetime, current_datetime)

            response = self.fetch_api_response(company_id.indiamart_api_key, start_datetime, end_datetime)
            if response:
                # Pass time_diff and uid to process_api_response
                stage, error, lead_ids, duplicated_leads = self.process_api_response(response, company_id, time_diff,
                                                                                     uid)


            self.create_history_record(company_id, lead_ids, duplicated_leads, start_datetime, end_datetime, error,
                                       stage, response)
            if stage == 'done':
                end_datetime_ist = self.convert_to_ist(end_datetime)
                company_id.last_fetch_update_time = end_datetime_ist.astimezone(pytz.utc).replace(tzinfo=None)

        return True

    def prepare_datetime(self, start_datetime, end_datetime, current_datetime):
        """
        Prepares the datetime range to be used.

        If both `start_datetime` and `end_datetime` are provided, they are returned as the range.
        If either of them is missing, the `current_datetime` is returned as both the start and end.

        Args:
            start_datetime (datetime): The start datetime.
            end_datetime (datetime): The end datetime.
            current_datetime (datetime): The current datetime to use if the start or end datetime is missing.

        Returns:
            tuple: A tuple containing the start and end datetime.
        """
        if start_datetime and end_datetime:
            return start_datetime, end_datetime
        return current_datetime, current_datetime

    def fetch_api_response(self, api_key, start_datetime, end_datetime):
        """
        Fetches the API response from the IndiaMart API.

        Constructs a URL with the provided `api_key`, `start_datetime`, and `end_datetime`,
        then sends a GET request to fetch the data. If the request is successful (HTTP status 200),
        it returns the JSON response. Otherwise, it logs an error and returns None.

        Args:
            api_key (str): The API key to authenticate the request.
            start_datetime (str): The start datetime in the query.
            end_datetime (str): The end datetime in the query.

        Returns:
            dict or None: The JSON response if successful, or None if there was an error.
        """
        url = f"https://mapi.indiamart.com/wservce/crm/crmListing/v2/?glusr_crm_key={api_key}&start_time={start_datetime}&end_time={end_datetime}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"HTTP error: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            _logger.error(f"Request error: {str(e)}")
            return None

    def process_api_response(self, json_response, company_id, time_diff, uid):
        """
        Processes the API response and extracts lead data.

        Args:
            json_response (dict): The JSON response from the API.
            company_id (Record): The company record associated with the leads.
            time_diff (timedelta): The time difference to adjust the query time.
            uid (Record): The user record who is processing the leads.

        Returns:
            tuple: A tuple containing the stage, error message, lead IDs, and duplicated lead IDs.
        """
        # Initialize default values
        lead_ids, duplicated_leads, error, stage = [], [], '', 'error'

        # Check if the response is valid
        if not isinstance(json_response, dict):
            return stage, error, lead_ids, duplicated_leads

        # Handle the SUCCESS response
        if json_response.get('CODE') == 204 and json_response.get('STATUS') == 'SUCCESS':
            return 'done', error, lead_ids, duplicated_leads

        # If there are response leads, process each one
        if 'RESPONSE' in json_response:
            for lead_data in json_response['RESPONSE']:
                if isinstance(lead_data, dict):
                    lead, error, stage = self.create_or_update_lead(lead_data, company_id, time_diff, uid)
                    if lead:
                        lead_ids.append(lead.id)
                    else:
                        duplicated_leads.append(lead_data.get('UNIQUE_QUERY_ID', ''))

        return stage, error, lead_ids, duplicated_leads

    def create_or_update_lead(self, val, company_id, time_diff, uid):
        """
        Creates or updates a lead in the system.

        If a lead with the provided `UNIQUE_QUERY_ID` already exists, it is updated.
        Otherwise, a new lead is created using the provided data.

        Args:
            val (dict): The lead data from the API response.
            company_id (Record): The company record associated with the lead.
            time_diff (timedelta): The time difference to adjust the query time.
            uid (Record): The user record associated with the lead.

        Returns:
            tuple: A tuple containing the lead (or None if not created), error message (or None), and stage.
        """
        if not val.get('SENDER_NAME') or not val.get('QUERY_TYPE'):
            return None, "Invalid entry", 'error'

        unique_query_id = val.get('UNIQUE_QUERY_ID')
        if not unique_query_id:
            return None, "Missing UNIQUE_QUERY_ID", 'error'

        lead_found = self.env['crm.lead'].sudo().search([
            ('indiamart_query_id', '=', unique_query_id),
            ('company_id', '=', company_id.id),
        ])

        if not lead_found:
            lead_vals = self.prepare_lead_values(val, company_id, uid, time_diff)
            lead = self.env['crm.lead'].sudo().create(lead_vals)
            lead.message_post(body=str(val))
            return lead, None, 'done'
        return lead_found, None, 'done'

    def prepare_lead_values(self, val, company_id, uid, time_diff):
        """
        Prepares the values for creating or updating a lead.

        Extracts the relevant fields from the API response and returns a dictionary
        with the required lead data.

        Args:
            val (dict): The lead data from the API response.
            company_id (Record): The company record associated with the lead.
            uid (Record): The user record associated with the lead.
            time_diff (timedelta): The time difference to adjust the query time.

        Returns:
            dict: A dictionary containing the lead values.
        """
        country_id = self.env['res.country'].search([('code', '=', val.get('SENDER_COUNTRY_ISO', ''))], limit=1)
        state_id = self.env['res.country.state'].search([('name', '=', val.get('SENDER_STATE', ''))], limit=1)

        lead_vals = {
            'partner_name': val.get('SENDER_COMPANY', ''),
            'name': val.get('SUBJECT', ''),
            'indiamart_query_id': val.get('UNIQUE_QUERY_ID', ''),
            'contact_name': val.get('SENDER_NAME', ''),
            'mobile': val.get('SENDER_MOBILE', ''),
            'email_from': val.get('SENDER_EMAIL', ''),
            'is_indiamart': True,
            'source_id': self.env.ref('stpl_indiamart_connector.india_mart_id').id,
            'company_id': company_id.id,
            'description': val.get('QUERY_MESSAGE', ''),
            'phone': val.get('SENDER_PHONE', ''),
            'street': val.get('SENDER_ADDRESS', ''),
            'city': val.get('SENDER_CITY', ''),
            'state_id': state_id.id if state_id else False,
            'zip': val.get('SENDER_PINCODE', ''),
            'country_id': country_id.id if country_id else False,
            'user_id': uid.id,
        }

        if val.get('QUERY_TIME'):
            query_time = datetime.strptime(val.get('QUERY_TIME'), "%Y-%m-%d %H:%M:%S")
            lead_vals.update({'date_open': query_time - time_diff})

        return lead_vals

    def create_history_record(self, company_id, lead_ids, duplicated_leads, start_datetime, end_datetime, error, stage,
                              response):
        """
        Creates a history record for the processed leads.

        This method creates a record in the `crm.indiamart.history` model to store the result
        of the API processing, including the associated leads, duplicated leads, error description,
        and processing stage.

        Args:
            company_id (Record): The company record associated with the leads.
            lead_ids (list): A list of created or updated lead IDs.
            duplicated_leads (list): A list of duplicated lead IDs.
            start_datetime (datetime): The start datetime for the API call.
            end_datetime (datetime): The end datetime for the API call.
            error (str): The error message, if any.
            stage (str): The stage of processing (e.g., 'done', 'error').
            response (json) : Response of Api call
        """

        # Convert start and end datetimes to IST (timezone-aware)
        start_datetime_ist = self.convert_to_ist(start_datetime)
        end_datetime_ist = self.convert_to_ist(end_datetime)

        start_datetime_utc = start_datetime_ist.astimezone(pytz.utc).replace(tzinfo=None)
        end_datetime_utc = end_datetime_ist.astimezone(pytz.utc).replace(tzinfo=None)

        history_rec = {
            'company_id': company_id.id,
            'response': response,
            'start_datetime': start_datetime_utc,  # Naive datetime in UTC
            'end_datetime': end_datetime_utc,  # Naive datetime in UTC
            'error_description': error if error else False,
            'state': stage,
        }

        if lead_ids:
            history_rec.update({'lead_ids': [(6, 0, lead_ids)], 'state': 'done'})
        if duplicated_leads:
            history_rec.update({'duplicate_lead_ids': [(6, 0, duplicated_leads)], 'state': 'done'})

        self.env['crm.indiamart.history'].sudo().create(history_rec)

