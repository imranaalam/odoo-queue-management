import requests
import logging
from datetime import datetime
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class QueueQueue(models.Model):
    _name        = 'queue.queue'
    _description = 'Queue'
    _order       = 'sequence, id'
    _inherit     = ['mail.thread', 'mail.activity.mixin']

    # ── Identity ──────────────────────────────────────────────────────────────
    name       = fields.Char('Queue Name', required=True, tracking=True)
    sequence   = fields.Integer('Sequence', default=10)
    prefix     = fields.Char(
        'Ticket Prefix', default='Q',
        help='Prefix before the number.  e.g. "Q" → Q001, "A" → A001'
    )
    color      = fields.Integer('Colour Index', default=1)
    active     = fields.Boolean(default=True)
    description = fields.Text('Description')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
    )

    # ── State ─────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('open',   'Open'),
        ('paused', 'Paused'),
        ('closed', 'Closed'),
    ], default='open', string='State', tracking=True)

    # ── Behaviour ─────────────────────────────────────────────────────────────
    require_name  = fields.Boolean('Require Customer Name',  default=False)
    require_phone = fields.Boolean('Require Phone Number',   default=False)
    auto_next     = fields.Boolean(
        'Auto-call Next on Done', default=False,
        help='Automatically call the next waiting token when the current one is marked Done.'
    )
    avg_service_minutes = fields.Integer('Avg. Service Time (min)', default=5)

    # ── Webhooks ──────────────────────────────────────────────────────────────
    display_webhook_url = fields.Char(
        'Display Webhook URL',
        help='POST here on every token state change — for TV/screen display.\n'
             'Payload: action, queue_id, queue_name, token_id, display_number, '
             'customer_name, customer_phone, state, waiting_count, timestamp'
    )
    sms_webhook_url = fields.Char(
        'SMS Webhook URL',
        help='POST here when a token is called (to notify the customer by SMS).'
    )
    whatsapp_webhook_url = fields.Char(
        'WhatsApp Webhook URL',
        help='POST here when a token is called (to notify the customer via WhatsApp).'
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    token_ids = fields.One2many('queue.token', 'queue_id', 'Tokens')

    # ── Computed statistics ───────────────────────────────────────────────────
    token_count   = fields.Integer('Total Tokens',  compute='_compute_counts', store=False)
    waiting_count = fields.Integer('Waiting',       compute='_compute_counts', store=False)
    called_count  = fields.Integer('Called/Serving',compute='_compute_counts', store=False)
    done_count    = fields.Integer('Done',          compute='_compute_counts', store=False)

    current_token_id = fields.Many2one(
        'queue.token', 'Now Serving',
        compute='_compute_current', store=False
    )

    @api.depends('token_ids.state')
    def _compute_counts(self):
        for rec in self:
            tokens = rec.token_ids
            rec.token_count   = len(tokens)
            rec.waiting_count = len(tokens.filtered(lambda t: t.state == 'waiting'))
            rec.called_count  = len(tokens.filtered(lambda t: t.state in ('called', 'serving')))
            rec.done_count    = len(tokens.filtered(lambda t: t.state == 'done'))

    @api.depends('token_ids.state')
    def _compute_current(self):
        for rec in self:
            called = rec.token_ids.filtered(
                lambda t: t.state in ('called', 'serving')
            ).sorted('number')
            rec.current_token_id = called[0] if called else False

    # ── State actions ─────────────────────────────────────────────────────────
    def action_open(self):
        self.write({'state': 'open'})

    def action_pause(self):
        self.write({'state': 'paused'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_call_next(self):
        """Button action — calls the next waiting token for this queue."""
        self.ensure_one()
        self.call_next(self.id)

    def action_view_tokens(self):
        """Smart button: open tokens for this queue."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Queue Tokens',
            'res_model': 'queue.token',
            'view_mode': 'list,form,kanban',
            'domain': [('queue_id', '=', self.id)],
            'context': {'default_queue_id': self.id},
        }


    # ── Public API (called from views, controllers, or other modules) ─────────

    @api.model
    def create_token(self, queue_id, customer_name=None, customer_phone=None,
                     partner_id=None, source='manual', notes=None):
        """
        Create a new token for the given queue.

        Args:
            queue_id       (int): id of the queue.queue record
            customer_name  (str): optional walk-in customer name
            customer_phone (str): optional phone / WhatsApp
            partner_id     (int): optional existing res.partner id
            source         (str): 'manual' | 'pos' | 'web' | 'api' | 'kiosk'
            notes          (str): optional free text

        Returns:
            dict with token data, or {'error': '...'} on failure.
        """
        queue = self.browse(queue_id)
        if not queue.exists():
            return {'error': 'Queue not found'}

        # ── find / create partner ───────────────────────────────────────────
        partner = self.env['res.partner']
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
        if not partner.exists() and (customer_name or customer_phone):
            if customer_phone:
                partner = self.env['res.partner'].search(
                    [('phone', '=', customer_phone), ('active', '=', True)], limit=1
                )
            if not partner and customer_name:
                partner = self.env['res.partner'].search(
                    [('name', '=', customer_name), ('active', '=', True)], limit=1
                )
            if not partner:
                partner = self.env['res.partner'].create({
                    'name':          customer_name or customer_phone,
                    'phone':         customer_phone or False,
                    'customer_rank': 1,
                })

        number = self.env['queue.token']._next_number(queue_id)
        token  = self.env['queue.token'].create({
            'queue_id':      queue_id,
            'number':        number,
            'customer_name': customer_name or False,
            'customer_phone':customer_phone or False,
            'partner_id':    partner.id if partner else False,
            'source':        source,
            'notes':         notes or False,
        })

        queue._fire_webhook(queue.display_webhook_url, 'new_token', token)

        return {
            'id':             token.id,
            'number':         token.number,
            'display_number': token.display_number,
            'customer_name':  token.customer_name  or '',
            'customer_phone': token.customer_phone or '',
            'state':          token.state,
            'queue_name':     queue.name,
            'prefix':         queue.prefix or 'Q',
        }

    @api.model
    def call_next(self, queue_id):
        """Call the next waiting token in queue order."""
        domain = [('queue_id', '=', queue_id), ('state', '=', 'waiting')]
        next_t = self.env['queue.token'].search(domain, order='number asc', limit=1)
        if not next_t:
            return False
        next_t.action_call()
        return {
            'id':             next_t.id,
            'display_number': next_t.display_number,
            'customer_name':  next_t.customer_name or '',
        }

    @api.model
    def get_status(self, queue_id):
        """
        Return full queue status dict — used by external display screens
        and the REST API.
        """
        queue = self.browse(queue_id)
        if not queue.exists():
            return {'error': 'Not found'}

        current = queue.current_token_id
        waiting = queue.token_ids.filtered(
            lambda t: t.state == 'waiting'
        ).sorted('number')

        return {
            'id':            queue.id,
            'name':          queue.name,
            'prefix':        queue.prefix or 'Q',
            'state':         queue.state,
            'waiting_count': len(waiting),
            'called_count':  queue.called_count,
            'done_count':    queue.done_count,
            'current': {
                'id':             current.id,
                'display_number': current.display_number,
                'customer_name':  current.customer_name or '',
            } if current else None,
            'next_waiting':  waiting[0].display_number if waiting else None,
        }

    # ── Internal webhook helper ───────────────────────────────────────────────
    def _fire_webhook(self, url, action, token=None):
        """POST a JSON payload to *url*.  Silently logs failures."""
        if not url:
            return
        payload = {
            'action':        action,
            'queue_id':      self.id,
            'queue_name':    self.name,
            'waiting_count': self.waiting_count,
            'timestamp':     str(datetime.now()),
        }
        if token:
            payload.update({
                'token_id':       token.id,
                'display_number': token.display_number,
                'customer_name':  token.customer_name  or '',
                'customer_phone': token.customer_phone or '',
                'state':          token.state,
            })
        try:
            r = requests.post(
                url, json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=8,
            )
            _logger.info('Queue webhook [%s] → %s  HTTP %s', action, url, r.status_code)
        except Exception as exc:
            _logger.warning('Queue webhook FAILED [%s] → %s : %s', action, url, exc)
