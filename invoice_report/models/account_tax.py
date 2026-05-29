from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override name_search to filter taxes based on location context"""
        # Check if we're in the context of a sale order (multiple ways to detect)
        filter_taxes = (self._context.get('filter_taxes_by_location') or 
                       self._context.get('default_filter_taxes_by_location') or
                       'sale.order' in str(self._context.get('active_model', '')))
        
        if filter_taxes:
            partner_id = (self._context.get('partner_id') or 
                         self._context.get('default_partner_id') or
                         self._context.get('parent', {}).get('partner_id'))
            company_id = (self._context.get('company_id') or 
                         self._context.get('default_company_id') or
                         self._context.get('parent', {}).get('company_id'))
            
            # Always filter out inactive taxes
            args = args or []
            if ('active', '=', True) not in args:
                args.append(('active', '=', True))
            
            if partner_id and company_id:
                partner = self.env['res.partner'].browse(partner_id)
                company = self.env['res.company'].browse(company_id)
                
                # Get tax domain based on location
                location_domain = self._get_tax_domain_for_location(partner, company)
                if location_domain:
                    args = args + location_domain
                    
        return super().name_search(name=name, args=args, operator=operator, limit=limit)
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """Override search to filter taxes in search dialog"""
        # Add debugging
        import logging
        _logger = logging.getLogger(__name__)
        
        # Log all context for debugging
        _logger.info(f"Tax search called with context: {self._context}")
        _logger.info(f"Tax search args: {args}")
        
        # Check if we're in the context of a sale order (multiple ways to detect)
        filter_taxes = (self._context.get('filter_taxes_by_location') or 
                       self._context.get('default_filter_taxes_by_location') or
                       'sale.order' in str(self._context.get('active_model', '')))
        
        if filter_taxes:
            partner_id = (self._context.get('partner_id') or 
                         self._context.get('default_partner_id') or
                         self._context.get('parent', {}).get('partner_id'))
            company_id = (self._context.get('company_id') or 
                         self._context.get('default_company_id') or
                         self._context.get('parent', {}).get('company_id'))
            
            _logger.info(f"Filtering taxes - partner_id: {partner_id}, company_id: {company_id}")
            
            # Always filter out inactive taxes
            args = args or []
            if ('active', '=', True) not in args:
                args.append(('active', '=', True))
            
            if partner_id and company_id:
                partner = self.env['res.partner'].browse(partner_id)
                company = self.env['res.company'].browse(company_id)
                
                _logger.info(f"Partner: {partner.name}, State: {partner.state_id.name if partner.state_id else 'None'}")
                
                # Get tax domain based on location
                location_domain = self._get_tax_domain_for_location(partner, company)
                if location_domain:
                    _logger.info(f"Applying location domain: {location_domain}")
                    args = args + location_domain
                    
        if count:
            return super().search_count(args)
        return super().search(args, offset=offset, limit=limit, order=order)
    
    @api.model
    def _get_tax_domain_for_location(self, partner, company):
        """Get tax domain based on partner and company location"""
        if not partner or not company:
            return []
            
        # Get customer state
        customer_state = partner.state_id
        # Get company state
        company_state = company.state_id
        
        if not customer_state:
            return []
            
        # If company state is not set, assume Gujarat
        if not company_state:
            gujarat_state = self.env['res.country.state'].search([
                ('name', 'ilike', 'Gujarat GJ'),
                ('country_id.code', '=', 'IN')
            ], limit=1)
            if gujarat_state:
                company_state = gujarat_state
            else:
                return []
            
        is_same_state = customer_state.id == company_state.id

        # Filter taxes based on location
        if is_same_state:
            # Customer in same state as company - show only GST (exclude IGST)
            return [
                ('type_tax_use', '=', 'sale'),
                ('company_id', '=', company.id),
                ('active', '=', True),
                ('name', 'not ilike', 'IGST'),  # Must not contain IGST
                '|', '|', '|',  # OR conditions for multiple GST types
                ('name', 'ilike', 'GST'),  # Contains GST
                ('name', 'ilike', 'CGST'),  # Contains CGST
                ('name', 'ilike', 'SGST'),  # Contains SGST
                ('name', 'ilike', 'UTGST'),  # Contains UTGST
            ]
        else:
            # Customer in different state - show only IGST
            return [
                ('type_tax_use', '=', 'sale'),
                ('company_id', '=', company.id),
                ('active', '=', True),
                ('name', 'ilike', 'IGST')
            ]
