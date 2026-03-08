from odoo import models, fields, api


class QueueQuickWizard(models.TransientModel):
    """
    Two-mode token-issue wizard (fallback for when kiosk is not convenient).

    Quick mode  — just pick a queue → token created instantly, no customer info.
    Detailed mode — pick queue + service types + optional customer details.
    """
    _name        = 'queue.quick.wizard'
    _description = 'Issue Token Wizard'

    # ── Mode ──────────────────────────────────────────────────────────────────
    wizard_type = fields.Selection([
        ('quick',    'Quick Token'),
        ('detailed', 'Detailed Token'),
    ], string='Mode', default='quick', required=True)

    # ── Queue & Services ──────────────────────────────────────────────────────
    queue_id = fields.Many2one(
        'queue.queue', 'Queue', required=True,
        domain=[('state', '=', 'open')],
    )
    service_ids = fields.Many2many(
        'queue.service', 'queue_wizard_service_rel', 'wizard_id', 'service_id',
        string='Services',
        domain="[('queue_id', 'in', [queue_id, False])]",
    )

    # ── Customer (shown in detailed mode only) ────────────────────────────────
    partner_id     = fields.Many2one('res.partner', 'Customer Record')
    customer_name  = fields.Char('Customer Name')
    customer_phone = fields.Char('Phone / WhatsApp')
    notes          = fields.Text('Notes')

    # ── Computed helpers ──────────────────────────────────────────────────────
    has_services = fields.Boolean(compute='_compute_has_services', store=False)
    queue_info   = fields.Char(compute='_compute_queue_info', store=False,
                               string='Queue Info')

    @api.depends('queue_id', 'queue_id.service_ids')
    def _compute_has_services(self):
        for rec in self:
            services = self.env['queue.service'].search([
                ('queue_id', 'in', [rec.queue_id.id, False] if rec.queue_id else [False]),
                ('active', '=', True),
            ]) if rec.queue_id else self.env['queue.service']
            rec.has_services = bool(services)

    @api.depends('queue_id')
    def _compute_queue_info(self):
        for rec in self:
            if rec.queue_id:
                q = rec.queue_id
                rec.queue_info = (
                    f'{q.name}  ·  {q.waiting_count} waiting'
                    f'  ·  now serving: {q.current_token_id.display_number or "—"}'
                )
            else:
                rec.queue_info = ''

    # ── Onchange ──────────────────────────────────────────────────────────────
    @api.onchange('queue_id')
    def _onchange_queue_id(self):
        self.service_ids = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            if not self.customer_name:
                self.customer_name = self.partner_id.name
            if not self.customer_phone:
                self.customer_phone = (
                    self.partner_id.phone or self.partner_id.mobile or ''
                )

    # ── Action ────────────────────────────────────────────────────────────────
    def action_issue_token(self):
        """Create the token and open its form (Print Slip is available there)."""
        self.ensure_one()
        vals = {
            'queue_id': self.queue_id.id,
            'source':   'manual',
        }
        if self.service_ids:
            vals['service_ids'] = [(6, 0, self.service_ids.ids)]
        if self.wizard_type == 'detailed':
            vals.update({
                'customer_name':  self.customer_name  or False,
                'customer_phone': self.customer_phone or False,
                'partner_id':     self.partner_id.id if self.partner_id else False,
                'notes':          self.notes          or False,
            })
        token = self.env['queue.token'].create(vals)
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'queue.token',
            'res_id':    token.id,
            'view_mode': 'form',
            'target':    'current',
        }
