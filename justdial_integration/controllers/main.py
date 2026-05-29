import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class JustDialIntegrationController(http.Controller):

    @http.route('/lead', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def justdial_lead(self, **kwargs):
        _logger.info("Justdial Lead data received: %s", kwargs)
        
        # Check if basic info is present
        if not kwargs:
            return Response("ERROR: No data received", status=400)

        # Extract parameters based on JD format
        leadid = kwargs.get('leadid', '')
        leadtype = kwargs.get('leadtype', '')
        prefix = kwargs.get('prefix', '')
        name = kwargs.get('name', '')
        mobile = kwargs.get('mobile', '')
        phone = kwargs.get('phone', '')
        email = kwargs.get('email', '')
        date_str = kwargs.get('date', '')
        category = kwargs.get('category', '')
        city = kwargs.get('city', '')
        area = kwargs.get('Area', kwargs.get('area', ''))
        brancharea = kwargs.get('brancharea', '')
        dncmobile = kwargs.get('dncmobile', '')
        dncphone = kwargs.get('dncphone', '')
        company = kwargs.get('company', '')
        pincode = kwargs.get('pincode', '')
        time_str = kwargs.get('time', '')
        branchpin = kwargs.get('branchpin', '')
        parentid = kwargs.get('parentid', '')

        # Construct Lead Contact Name
        contact_full_name = " ".join(filter(None, [prefix, name])) if name else ""

        # Filter out own company name (JustDial listing name) to get real client company
        OWN_COMPANY_NAMES = ['r v enterprise', 'rv enterprise']
        client_company = company if company and company.strip().lower() not in OWN_COMPANY_NAMES else ''

        # Lead title logic:
        #   - If real client company exists → "Company Name - Category"
        #   - If no company → "Contact Name - Category"
        primary_name = client_company if client_company else contact_full_name
        lead_name_parts = list(filter(None, [primary_name, category]))
        lead_name = " - ".join(lead_name_parts)
        if not lead_name:
            lead_name = "Unknown Caller"

        # Build description with extra data that doesn't fit standard fields
        # Note: Added empty lines or explicit formatting to ensure they appear line-by-line
        description_lines = []
        if leadid: description_lines.append(f"JD Lead ID: {leadid}")
        if leadtype: description_lines.append(f"Lead Type: {leadtype}")
        if date_str or time_str: description_lines.append(f"JD Lead Date/Time: {date_str} {time_str}")
        if category: description_lines.append(f"Category: {category}")
        if area: description_lines.append(f"Area: {area}")
        if brancharea: description_lines.append(f"Branch Area: {brancharea}")
        if branchpin: description_lines.append(f"Branch Pincode: {branchpin}")
        if parentid: description_lines.append(f"Parent ID: {parentid}")
        if dncmobile: description_lines.append(f"DNC Mobile: {'Yes' if dncmobile=='1' else 'No'}")
        if dncphone: description_lines.append(f"DNC Phone: {'Yes' if dncphone=='1' else 'No'}")

        # Adding explicit HTML <br/> tags because the Internal Notes field may render as HTML
        description = "<br/><br/>".join(description_lines)

        # Find Justdial Source
        source = request.env['utm.source'].sudo().search([('name', '=', 'Justdial')], limit=1)
        
        lead_vals = {
            'name': lead_name,
            'contact_name': contact_full_name,
            'partner_name': client_company,  # Only caller's real company, NOT your own JD listing name
            'mobile': mobile,
            'phone': phone,
            'email_from': email,
            'city': city,
            'zip': pincode,
            'description': description,
            'type': 'lead',  # explicitly set to lead
            'source_id': source.id if source else False,
            'is_justdial': True,
        }

        # 👇 Get Cron User (Salesperson)
        # ✅ Get company
        company = request.env.company

        # ✅ Priority 1: Settings salesperson
        user = company.justdial_salesperson_id

        # ✅ Fallback: Cron user
        if not user:
            cron_ref = request.env.ref('justdial_integration.stpl_justdial_connector_cron', raise_if_not_found=False)
            user = cron_ref.user_id if cron_ref else request.env.ref('base.user_admin')

        lead_vals.update({
            'user_id': user.id,
            'is_justdial': True
        })

        try:
            # Prevent Duplicate Leads based on Justdial 'leadid'
            if leadid:
                # Search for an existing lead with the same JD Lead ID in its description
                existing_lead = request.env['crm.lead'].sudo().search([
                    ('description', 'ilike', f"JD Lead ID: {leadid}")
                ], limit=1)
                
                if existing_lead:
                    _logger.info("Justdial Lead '%s' already exists in Odoo database. Skipping duplicate creation.", leadid)
                    return request.make_response("RECEIVED", headers=[('Content-Type', 'text/plain')])

            # Create the lead using sudo since auth='public'
            request.env['crm.lead'].sudo().create(lead_vals)
            _logger.info("Successfully created JustDial Lead: %s", lead_name)
            
        except Exception as e:
            _logger.error("Failed to create JustDial Lead: %s", str(e))
            # Even if it fails internally, if JD requires 'RECEIVED', we should probably still return it or handle error appropriately.

        # Justdial requires the response to be exactly "RECEIVED"
        return request.make_response("RECEIVED", headers=[('Content-Type', 'text/plain')])
