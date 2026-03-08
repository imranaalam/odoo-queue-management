from odoo import models, fields, api


class QueueQuickWizard(models.TransientModel):
    """
    Two-mode token-issue wizard.

    Quick mode  — just pick a queue → token created instantly, no customer info.
    Detailed mode — pick queue + service type + optional customer details.
    """
    _name        = 'queue.quick.wizard'
    _description = 'Issue Token Wizard'

    # ── Mode ──────────────────────────────────────────────────────────────────
    wizard_type = fields.Selection([
        ('quick',    'Quick Token'),
        ('detailed', 'Detailed Token'),
    ], string='Mode', default='quick', required=True)

    # ── Queue & Service ───────────────────────────────────────────────────────
    queue_id = fields.Many2one(
        'queue.queue', 'Queue', required=True,
        domain=[('state', '=', 'open')],
    )
    service_id = fields.Many2one(
        'queue.service', 'Service Type',
        domain="[('queue_id', '=', queue_id)]",
    )

    # ── Customer (shown in detailed mode only) ────────────────────────────────
    partner_id     = fields.Many2one('res.partner', 'Customer Record')
    customer_name  = fields.Char('Customer Name')
    customer_phone = fields.Char('Phone / WhatsApp')
    notes          = fields.Text('Notes')

    # ── Computed helpers ──────────────────────────────────────────────────────
    has_services = fields.Boolean(compute='_compute_has_services', store=False)
    queue_info   = fields.Char(compute='_compute_queue_info',   store=False,
                               string='Queue Info')

    @api.depends('queue_id', 'queue_id.service_ids')
    def _compute_has_services(self):
        for rec in self:
            rec.has_services = bool(
                rec.queue_id and rec.queue_id.service_ids
            )

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
        """Clear service when queue changes."""
        self.service_id = False

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
        if self.service_id:
            vals['service_id'] = self.service_id.id
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
