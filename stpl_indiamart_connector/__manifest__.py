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
{
    'name': 'Odoo IndiaMart Connector',
    'version': '18.0.1.0.0',
    'author': 'Surekha Technologies Pvt Ltd',
    'description': """With the Odoo IndiaMart Connector Module, One can easily create the leads
                     from the API Responses. Through this Odoo IndiaMart integrator Module  the person is able
                     to check each and every api call's history. Another feature of this module is 
                     that one can configure IndiaMart for more than one company i.e. multiple companies 
                     is featured in this. Also, with scheduler one can fetch response with specific time duration. """,
    'summary': """Configure IndiaMart for multiple company, and able to create leads from api calls.""",
    'category': 'Tools',
    'license': 'Other proprietary',
    'maintainer': 'Surekha Technologies Pvt Ltd',
    'website': 'https://www.surekhatech.com',
    'company': 'Surekha Technologies Pvt Ltd',
    'depends': ['base','crm'],
    'data': [
        'security/stpl_crm_indiamart_history_security.xml',
        'security/ir.model.access.csv',
        'data/utm_source.xml',
        'wizard/stpl_res_company_wizard_view.xml',
        'views/stpl_res_company_inherited.xml',
        'views/stpl_indiamart_connector_cron.xml',
        'views/stpl_crm_indiamart_history.xml',
        'views/stpl_crm_lead_view_inherited.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True, 
    'auto_install': False,
    'application': True,
    'price': 24.99,
    'currency': 'EUR',
    'sequence': 1,
    'live_test_url': 'https://indiamartconv18.surekhatech.com/web?db=odoo_18_indiamart_connector'
}
