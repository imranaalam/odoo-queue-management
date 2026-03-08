import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class QueueService(models.Model):
    _name        = 'queue.service'
    _description = 'Queue Service Type'
    _order       = 'sequence, name'

    name        = fields.Char('Service Name', required=True, translate=True)
    # queue_id is optional — a service with no queue appears in all queues
    queue_id    = fields.Many2one(
        'queue.queue', 'Queue',
        ondelete='cascade', index=True,
        help='Leave empty to show this service in every queue on the kiosk.'
    )
    category_id = fields.Many2one(
        'queue.service.category', 'Category',
        ondelete='set null', index=True,
    )
    image_1920  = fields.Image('Image', max_width=1920, max_height=1920)
    description = fields.Text('Description')
    active      = fields.Boolean(default=True)
    sequence    = fields.Integer('Sequence', default=10)
    color       = fields.Integer('Colour Index', default=0)

    # Today's stats
    token_count   = fields.Integer('Tokens Today',  compute='_compute_stats', store=False)
    waiting_count = fields.Integer('Waiting',        compute='_compute_stats', store=False)

    @api.depends('queue_id')
    def _compute_stats(self):
        today = fields.Date.today()
        Token = self.env['queue.token']
        for rec in self:
            tokens = Token.search([
                ('service_ids', 'in', [rec.id]),
                ('created_at', '>=', str(today)),
            ])
            rec.token_count   = len(tokens)
            rec.waiting_count = len(tokens.filtered(lambda t: t.state == 'waiting'))

    # ── Import from POS ────────────────────────────────────────────────────────
    def action_import_from_pos(self):
        """
        Import POS categories → queue.service.category
        and POS products (available_in_pos=True) → queue.service
        """
        if 'pos.category' not in self.env.registry.models:
            return {
                'type': 'ir.actions.client',
                'tag':  'display_notification',
                'params': {
                    'message': 'Point of Sale module is not installed.',
                    'type':    'warning',
                    'sticky':  False,
                },
            }

        ServiceCategory = self.env['queue.service.category']
        cat_created = 0
        cat_map = {}  # pos.category id → queue.service.category id

        # Import POS categories
        for pos_cat in self.env['pos.category'].search([]):
            existing = ServiceCategory.search(
                [('name', '=', pos_cat.name)], limit=1
            )
            if not existing:
                sc = ServiceCategory.create({
                    'name':       pos_cat.name,
                    'image_1920': pos_cat.image_1920,
                    'sequence':   getattr(pos_cat, 'sequence', 10),
                })
                cat_created += 1
            else:
                sc = existing
            cat_map[pos_cat.id] = sc.id

        # Import POS products
        products = self.env['product.template'].search([
            ('available_in_pos', '=', True),
            ('sale_ok', '=', True),
        ])
        svc_created = 0
        for prod in products:
            if self.search([('name', '=', prod.name)], limit=1):
                continue  # skip duplicates
            vals = {
                'name':       prod.name,
                'image_1920': prod.image_1920,
                'description': prod.description_sale or False,
            }
            pos_cat_id = getattr(prod, 'pos_category_id', False)
            if pos_cat_id:
                sc_id = cat_map.get(pos_cat_id.id)
                if sc_id:
                    vals['category_id'] = sc_id
            self.create(vals)
            svc_created += 1

        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'message': (
                    f'Imported {cat_created} categories and '
                    f'{svc_created} services from Point of Sale.'
                ),
                'type':   'success',
                'sticky': False,
            },
        }
