from odoo import models, fields, api


class QueueService(models.Model):
    _name        = 'queue.service'
    _description = 'Queue Service Type'
    _order       = 'sequence, name'

    name        = fields.Char('Service Name', required=True, translate=True)
    queue_id    = fields.Many2one(
        'queue.queue', 'Queue', required=True,
        ondelete='cascade', index=True,
    )
    description = fields.Text('Description')
    active      = fields.Boolean(default=True)
    sequence    = fields.Integer('Sequence', default=10)
    color       = fields.Integer('Colour', default=0)

    # How many tokens for this service were issued today
    token_count = fields.Integer(
        'Tokens Today', compute='_compute_token_count', store=False
    )
    # How many are currently waiting
    waiting_count = fields.Integer(
        'Waiting', compute='_compute_token_count', store=False
    )

    @api.depends('queue_id')
    def _compute_token_count(self):
        today = fields.Date.today()
        Token = self.env['queue.token']
        for rec in self:
            tokens = Token.search([
                ('service_id', '=', rec.id),
                ('created_at', '>=', str(today)),
            ])
            rec.token_count   = len(tokens)
            rec.waiting_count = len(tokens.filtered(lambda t: t.state == 'waiting'))
