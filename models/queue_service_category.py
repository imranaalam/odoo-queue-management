from odoo import models, fields


class QueueServiceCategory(models.Model):
    _name        = 'queue.service.category'
    _description = 'Service Category'
    _order       = 'sequence, name'

    name       = fields.Char('Category Name', required=True, translate=True)
    sequence   = fields.Integer('Sequence', default=10)
    image_1920 = fields.Image('Image', max_width=1920, max_height=1920)
    active     = fields.Boolean(default=True)
    color      = fields.Integer('Colour', default=0)

    service_ids = fields.One2many('queue.service', 'category_id', 'Services')
    service_count = fields.Integer('# Services', compute='_compute_service_count')

    def _compute_service_count(self):
        for rec in self:
            rec.service_count = len(rec.service_ids)
