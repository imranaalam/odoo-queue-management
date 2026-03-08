import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class QueueToken(models.Model):
    _name        = 'queue.token'
    _description = 'Queue Token'
    _rec_name    = 'display_number'
    _order       = 'number asc'

    # ── Core ──────────────────────────────────────────────────────────────────
    queue_id = fields.Many2one(
        'queue.queue', 'Queue', required=True, ondelete='cascade', index=True
    )
    number         = fields.Integer('Token Number', required=True)
    display_number = fields.Char(
        'Token #', compute='_compute_display', store=True
    )

    # ── Service ───────────────────────────────────────────────────────────────
    service_id = fields.Many2one(
        'queue.service', 'Service Type',
        domain="[('queue_id', '=', queue_id)]",
        ondelete='set null',
    )

    # ── Customer ──────────────────────────────────────────────────────────────
    partner_id     = fields.Many2one('res.partner', 'Customer', ondelete='set null')
    customer_name  = fields.Char('Customer Name')
    customer_phone = fields.Char('Phone / WhatsApp')

    # ── State ─────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('called',  'Called'),
        ('serving', 'Serving'),
        ('done',    'Done'),
        ('skipped', 'Skipped'),
        ('noshow',  'No-Show'),
    ], default='waiting', string='State', index=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    source = fields.Selection([
        ('manual', 'Manual'),
        ('pos',    'Point of Sale'),
        ('web',    'Website'),
        ('api',    'API'),
        ('kiosk',  'Kiosk'),
    ], default='manual', string='Source')
    notes = fields.Text('Notes')

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = fields.Datetime('Created',   default=fields.Datetime.now, index=True)
    called_at  = fields.Datetime('Called At')
    served_at  = fields.Datetime('Served At')

    # ── Computed ──────────────────────────────────────────────────────────────
    wait_minutes = fields.Integer('Wait (min)', compute='_compute_wait')

    company_id = fields.Many2one(
        'res.company', related='queue_id.company_id', store=True
    )

    @api.depends('number', 'queue_id.prefix')
    def _compute_display(self):
        for rec in self:
            prefix = rec.queue_id.prefix or 'Q'
            rec.display_number = f'{prefix}{rec.number:03d}'

    @api.depends('created_at', 'called_at', 'state')
    def _compute_wait(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.state in ('done', 'skipped', 'noshow') and rec.called_at and rec.created_at:
                diff = rec.called_at - rec.created_at
            elif rec.created_at:
                diff = now - rec.created_at
            else:
                diff = False
            rec.wait_minutes = int(diff.total_seconds() / 60) if diff else 0

    # ── ORM overrides ────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-assign the next sequential number when not supplied."""
        for vals in vals_list:
            if not vals.get('number') and vals.get('queue_id'):
                vals['number'] = self._next_number(vals['queue_id'])
        return super().create(vals_list)

    # ── Onchange ──────────────────────────────────────────────────────────────
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Fill customer name and phone from the selected partner."""
        if self.partner_id:
            if not self.customer_name:
                self.customer_name = self.partner_id.name
            if not self.customer_phone:
                self.customer_phone = (
                    self.partner_id.phone or self.partner_id.mobile or ''
                )

    # ── Print action ──────────────────────────────────────────────────────────
    def action_print_slip(self):
        """Return the token slip report action."""
        self.ensure_one()
        return self.env.ref(
            'queue_management.action_report_queue_token_slip'
        ).report_action(self)

    # ── State actions (called from buttons / server actions) ──────────────────
    def action_call(self):
        """Mark as Called and fire all notification webhooks."""
        for rec in self:
            if rec.state in ('waiting', 'skipped'):
                rec.write({'state': 'called', 'called_at': fields.Datetime.now()})
                q = rec.queue_id
                q._fire_webhook(q.display_webhook_url,   'token_called',     rec)
                q._fire_webhook(q.sms_webhook_url,       'sms_notify',       rec)
                q._fire_webhook(q.whatsapp_webhook_url,  'whatsapp_notify',  rec)

    def action_serve(self):
        """Move from Called → Serving (optional intermediate step)."""
        for rec in self:
            if rec.state == 'called':
                rec.write({'state': 'serving'})
                rec.queue_id._fire_webhook(
                    rec.queue_id.display_webhook_url, 'token_serving', rec
                )

    def action_done(self):
        """Mark as Done and optionally trigger auto-next."""
        for rec in self:
            rec.write({'state': 'done', 'served_at': fields.Datetime.now()})
            q = rec.queue_id
            q._fire_webhook(q.display_webhook_url, 'token_done', rec)
            if q.auto_next:
                q.call_next(q.id)

    def action_skip(self):
        self.write({'state': 'skipped'})

    def action_noshow(self):
        self.write({'state': 'noshow'})

    def action_reset(self):
        """Reset a skipped / no-show token back to waiting."""
        self.write({'state': 'waiting', 'called_at': False, 'served_at': False})

    # ── Helper ────────────────────────────────────────────────────────────────
    @api.model
    def _next_number(self, queue_id):
        """Return the next sequential number for the given queue."""
        last = self.search(
            [('queue_id', '=', queue_id)],
            order='number desc', limit=1
        )
        return (last.number + 1) if last else 1
