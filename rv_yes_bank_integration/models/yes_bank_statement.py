# -*- coding: utf-8 -*-
import base64
import json
import logging
import os
import time
from datetime import datetime

# pyrefly: ignore [missing-import]
from odoo import models, fields, api, _
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JWE Helpers (pure `cryptography` library – ships with Odoo 18 / Debian)
# ---------------------------------------------------------------------------
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _CRYPTO_OK = True
except ImportError:
    _CRYPTO_OK = False
    _logger.warning("YES Bank Statement: `cryptography` package not found – JWE disabled.")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def _b64url_decode(s: str) -> bytes:
    padding_needed = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + '=' * padding_needed)


def _jwe_encrypt(payload_dict: dict, cert_path: str) -> str:
    """Encrypt payload_dict as a compact JWE token using YES Bank's DataPower cert."""
    if not _CRYPTO_OK:
        raise UserError(_("The 'cryptography' Python package is not installed. Cannot encrypt JWE payload."))

    with open(cert_path, "rb") as f:
        cert_data = f.read()

    # Try PEM certificate first, fallback to raw public key
    try:
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        pub_key = cert.public_key()
    except Exception:
        pub_key = serialization.load_pem_public_key(cert_data, backend=default_backend())

    header = {"alg": "RSA-OAEP-256", "enc": "A256GCM"}
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    b64_header = _b64url_encode(header_json)

    aes_key = os.urandom(32)
    enc_key = pub_key.encrypt(
        aes_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    b64_enc_key = _b64url_encode(enc_key)

    iv = os.urandom(12)
    b64_iv = _b64url_encode(iv)

    plaintext = json.dumps(payload_dict).encode('utf-8')
    aad = b64_header.encode('ascii')
    aesgcm = AESGCM(aes_key)
    ciphertext_and_tag = aesgcm.encrypt(iv, plaintext, aad)

    ciphertext = ciphertext_and_tag[:-16]
    tag = ciphertext_and_tag[-16:]

    return f"{b64_header}.{b64_enc_key}.{b64_iv}.{_b64url_encode(ciphertext)}.{_b64url_encode(tag)}"


def _jwe_decrypt(compact_jwe: str, key_path: str) -> dict:
    """Decrypt a compact JWE token using client private key."""
    if not _CRYPTO_OK:
        raise UserError(_("The 'cryptography' Python package is not installed. Cannot decrypt JWE response."))

    parts = compact_jwe.strip().split('.')
    if len(parts) != 5:
        # Response may be plain JSON (non-encrypted error)
        try:
            return json.loads(compact_jwe)
        except Exception:
            return {"raw_text": compact_jwe}

    b64_header, b64_enc_key, b64_iv, b64_ciphertext, b64_tag = parts

    with open(key_path, "rb") as f:
        priv_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())

    enc_key = _b64url_decode(b64_enc_key)
    aes_key = priv_key.decrypt(
        enc_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    iv = _b64url_decode(b64_iv)
    ciphertext = _b64url_decode(b64_ciphertext)
    tag = _b64url_decode(b64_tag)
    aad = b64_header.encode('ascii')

    aesgcm = AESGCM(aes_key)
    plaintext = aesgcm.decrypt(iv, ciphertext + tag, aad)
    return json.loads(plaintext.decode('utf-8'))


# ---------------------------------------------------------------------------
# Wizard Model
# ---------------------------------------------------------------------------

class YesBankStatementWizard(models.TransientModel):
    _name = 'yes.bank.statement.wizard'
    _description = 'YES Bank Adhoc Statement Fetch Wizard'

    journal_id = fields.Many2one(
        'account.journal', string='Journal', required=True,
        domain=[('type', '=', 'bank')],
        default=lambda self: self._default_journal()
    )
    date_from = fields.Date(
        string='From Date', required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='To Date', required=True,
        default=fields.Date.today
    )
    page_size = fields.Integer(string='Records per Page', default=50)
    fetch_all_pages = fields.Boolean(
        string='Fetch All Pages', default=True,
        help="Automatically paginate through all available records."
    )
    result_summary = fields.Text(string='Result', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft')

    def _default_journal(self):
        journals = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        return journals.id if journals else False

    def _get_config(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        # Settings account number takes priority; fall back to journal's linked bank account
        configured_account = (get_param('rv_yes_bank_integration.yes_bank_account_number') or '').strip()
        journal_account = (self.journal_id.bank_account_id.acc_number or '').strip()
        return {
            'client_id': get_param('rv_yes_bank_integration.yes_bank_client_id'),
            'client_secret': get_param('rv_yes_bank_integration.yes_bank_client_secret'),
            'channel_id': get_param('rv_yes_bank_integration.yes_bank_channel_id', 'RVEnterprise'),
            'basic_auth_user': get_param('rv_yes_bank_integration.yes_bank_basic_auth_user', 'testuser'),
            'basic_auth_pass': get_param('rv_yes_bank_integration.yes_bank_basic_auth_password'),
            'cert_path': (get_param('rv_yes_bank_integration.yes_bank_cert_path') or '').strip(),
            'key_path': (get_param('rv_yes_bank_integration.yes_bank_key_path') or '').strip(),
            'dp_cert_path': (get_param('rv_yes_bank_integration.yes_bank_dp_cert_path') or '').strip(),
            'account_number': configured_account or journal_account,
            'cust_id': (get_param('rv_yes_bank_integration.yes_bank_cust_id') or '').strip(),
            'app_id': get_param('rv_yes_bank_integration.yes_bank_app_id', 'NIL1121'),
            'env_mode': get_param('rv_yes_bank_integration.yes_bank_environment', 'uat'),
        }


    def _validate_config(self, cfg):
        missing = [k for k in ('client_id', 'client_secret', 'basic_auth_pass',
                               'cert_path', 'key_path', 'dp_cert_path',
                               'account_number', 'cust_id') if not cfg.get(k)]
        if missing:
            raise UserError(
                _("Please complete YES Bank Integration settings. Missing: %s") % ', '.join(missing)
            )
        for label, path in [('SSL Cert', cfg['cert_path']),
                            ('SSL Key', cfg['key_path']),
                            ('DataPower Cert', cfg['dp_cert_path'])]:
            if not os.path.exists(path):
                raise ValidationError(_("%s file not found at: %s") % (label, path))

    def action_fetch_statement(self):
        self.ensure_one()
        cfg = self._get_config()
        self._validate_config(cfg)

        import requests as req_lib

        base_url = ("https://skyway.yes.bank.in/app/live" if cfg['env_mode'] == 'production'
                    else "https://skyway.yesuat.bank.in/app/uat")
        url = f"{base_url}/AdhocStatement/V3/enc/Inquiry"

        start_date = self.date_from.strftime('%Y%m%d')
        end_date = self.date_to.strftime('%Y%m%d')
        # startTime/endTime format: YYYYMMDDHHmmS (13 digits as per YES Bank spec)
        start_time = self.date_from.strftime('%Y%m%d') + '000000'
        end_time = self.date_to.strftime('%Y%m%d') + '235959'

        all_transactions = []
        page_no = 1
        total_pages = 0
        is_next = 'Y'

        while is_next == 'Y':
            req_ref = f"RVSTMT{int(time.time())}{page_no}"
            payload = {
                "AcctStatementInquiryReq": {
                    "ReqHdr": {
                        "ConsumerContext": {"RequesterID": "APP"},
                        "ServiceContext": {
                            "ServiceName": "AcctStatementInquiry",
                            "ReqRefNum": req_ref,
                            "ReqRefTimeStamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            "ServiceVersionNo": "1.3"
                        }
                    },
                    "ReqBody": {
                        "customerId": cfg['cust_id'],
                        "accountNo": cfg['account_number'],
                        "pageSize": str(self.page_size),
                        "pageNo": str(page_no),
                        "startTime": start_time,
                        "endTime": end_time,
                        "startDate": start_date,
                        "endDate": end_date
                    }
                }
            }

            try:
                jwe_token = _jwe_encrypt(payload, cfg['dp_cert_path'])
            except Exception as e:
                raise UserError(_("JWE Encryption failed: %s") % str(e))

            headers = {
                "ChannelId": cfg['channel_id'],
                "X-IBM-Client-Id": cfg['client_id'],
                "X-IBM-Client-Secret": cfg['client_secret'],
                "Content-Type": "text/plain"
            }

            log = self.env['yes.bank.log'].sudo().create({
                'name': f'Statement – Pg {page_no} – {start_date} to {end_date}',
                'amount': 0.0,
                'raw_data': f"URL: {url}\nRef: {req_ref}\nAcct: {cfg['account_number']}\nPage: {page_no}",
                'status': 'received'
            })

            try:
                response = req_lib.post(
                    url,
                    headers=headers,
                    auth=(cfg['basic_auth_user'], cfg['basic_auth_pass']),
                    cert=(cfg['cert_path'], cfg['key_path']),
                    data=jwe_token,
                    timeout=60
                )
            except Exception as e:
                log.write({'status': 'error', 'raw_data': log.raw_data + f"\n\nError: {e}"})
                raise UserError(_("Failed to connect to YES Bank: %s") % str(e))

            log.write({'raw_data': log.raw_data + f"\n\nHTTP {response.status_code}"})

            if response.status_code != 200:
                log.write({'status': 'error'})
                raise UserError(_("YES Bank API HTTP %s: %s") % (response.status_code, response.text[:500]))

            try:
                res_data = _jwe_decrypt(response.text, cfg['key_path'])
            except Exception as e:
                log.write({'status': 'error', 'raw_data': log.raw_data + f"\n\nDecrypt Error: {e}"})
                raise UserError(_("JWE Decryption failed: %s") % str(e))

            log.write({'raw_data': log.raw_data + f"\n\nDecrypted:\n{json.dumps(res_data, indent=2)}"})

            # Parse response
            inner = res_data.get('AcctStatementInquiryRes', {})
            res_hdr = inner.get('ResHdr', {})
            svc_resp = res_hdr.get('ServiceResponse', {})
            esb_status = svc_resp.get('EsbResStatus', 1)
            err_details = res_hdr.get('ErrorDetails', {})

            if esb_status != 0:
                log.write({'status': 'error'})
                err_code = err_details.get('ErrCode', '?')
                err_desc = err_details.get('ErrDesc', 'Unknown error')
                raise UserError(
                    _("YES Bank CBS error (Code %s): %s\n\n"
                      "The account must be entitled to Channel ID '%s' in YES Bank's Finacle system.\n"
                      "Please contact APIONBOARDING.RETAIL to map your account to this channel.")
                    % (err_code, err_desc, cfg['channel_id'])
                )

            res_body = inner.get('ResBody', {})
            transactions = res_body.get('xfaceTransactionDetailsDTO', [])
            all_transactions.extend(transactions)
            total_pages += 1
            is_next = res_body.get('isNextPage', 'N')

            log.write({
                'status': 'completed',
                'amount': float(res_body.get('currentBalance', 0) or 0),
                'processed_date': fields.Datetime.now()
            })

            if not self.fetch_all_pages or is_next != 'Y':
                break
            page_no += 1

        # Create bank statement lines
        created, skipped = self._create_statement_lines(all_transactions)

        summary = (
            f"Fetched {len(all_transactions)} transactions across {total_pages} page(s).\n"
            f"Created: {created} new statement line(s).\n"
            f"Skipped (duplicates): {skipped}."
        )
        self.write({'result_summary': summary, 'state': 'done'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'yes.bank.statement.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _create_statement_lines(self, transactions):
        """Parse YES Bank transactions and create account.bank.statement.line records."""
        created = 0
        skipped = 0
        journal = self.journal_id

        for txn in transactions:
            ref_no = (txn.get('referenceTransactionNo') or '').strip()
            user_ref = (txn.get('userReferenceNumber') or '').strip()
            narrative = (txn.get('narrative') or '').strip()
            dr_cr = txn.get('drcrFlag', 'D')
            txn_amount_raw = txn.get('transactionAmount') or '0'
            txn_date_raw = txn.get('transactionDate') or txn.get('fcrPostingDate') or ''
            txn_literal = txn.get('txnLiteral', '')
            cheque_no = txn.get('chequeNo') or ''

            # Parse amount
            try:
                amount = float(str(txn_amount_raw).replace(',', ''))
            except (ValueError, TypeError):
                amount = 0.0

            # Debits are outflows (negative)
            if dr_cr == 'D':
                amount = -abs(amount)
            else:
                amount = abs(amount)

            # Parse date
            txn_date = None
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y%m%d'):
                try:
                    txn_date = datetime.strptime(txn_date_raw[:19], fmt).date()
                    break
                except (ValueError, TypeError):
                    continue
            if not txn_date:
                txn_date = self.date_from

            # Unique reference for deduplication
            unique_ref = ref_no or user_ref or f"{txn_date}_{amount}_{narrative[:30]}"

            # Dedup check
            existing = self.env['account.bank.statement.line'].sudo().search([
                ('journal_id', '=', journal.id),
                ('payment_ref', '=', unique_ref),
            ], limit=1)
            if existing:
                skipped += 1
                continue

            # Build narration label
            parts = [narrative]
            if txn_literal:
                parts.append(f"[{txn_literal}]")
            if cheque_no:
                parts.append(f"Chq:{cheque_no}")
            label = ' | '.join(filter(None, parts)) or unique_ref

            try:
                self.env['account.bank.statement.line'].sudo().create({
                    'journal_id': journal.id,
                    'date': txn_date,
                    'payment_ref': unique_ref,
                    'ref': user_ref or ref_no,
                    'narration': label,
                    'amount': amount,
                    'partner_name': narrative[:100] if narrative else False,
                })
                created += 1
            except Exception as e:
                _logger.error("YES Bank: Failed to create line for ref %s: %s", unique_ref, e)
                skipped += 1

        return created, skipped

    def action_open_bank_statement(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bank Statement Lines'),
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,form',
            'domain': [('journal_id', '=', self.journal_id.id)],
            'context': {'default_journal_id': self.journal_id.id},
        }

    @api.model
    def cron_auto_fetch_statement(self):
        """Scheduled action: fetch yesterday's statement for all YES Bank journals."""
        from datetime import date, timedelta
        yesterday = date.today() - timedelta(days=1)

        get_param = self.env['ir.config_parameter'].sudo().get_param
        account_number = get_param('rv_yes_bank_integration.yes_bank_account_number')

        journals = self.env['account.journal'].search([('type', '=', 'bank')])
        for journal in journals:
            is_yes_bank = (
                (account_number and journal.bank_account_id.acc_number == account_number)
                or journal.code == 'YES'
                or 'yes' in (journal.name or '').lower()
            )
            if not is_yes_bank:
                continue
            try:
                wizard = self.create({
                    'journal_id': journal.id,
                    'date_from': yesterday,
                    'date_to': yesterday,
                    'fetch_all_pages': True,
                    'page_size': 100,
                })
                wizard.action_fetch_statement()
                _logger.info("YES Bank cron: statement fetched for journal %s (%s)", journal.name, yesterday)
            except Exception as e:
                _logger.error("YES Bank cron: statement fetch failed for journal %s: %s", journal.name, str(e))

