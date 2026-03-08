{
    'name': 'Queue Management',
    'version': '17.0.2.0.0',
    'category': 'Services',
    'summary': 'Universal queue management — POS-like kiosk, numbered tokens, live board, SMS/WhatsApp webhooks',
    'description': """
Queue Management
================

A fully standalone queue management system that works for ANY use case:
clinics, banks, government offices, retail counters, service desks.

No dependency on Point of Sale — install and use independently.

Key Features
------------
* **Multiple named queues** — each with its own prefix, colour, and webhook URLs
* **POS-like kiosk** — touch-friendly issue-token screen with categories, service cards, images
* **Service Categories** — group services with images for a visual kiosk (Aesthetics, Medical…)
* **Service Types** — per-queue or global services with images (Hydrafacial, Hair Removal…)
* **Multi-service selection** — customers can tick multiple services; staff route accordingly
* **Import from POS** — one-click import of POS products/categories as queue services
* **Token lifecycle** — Waiting → Called → Serving → Done / Skipped / No-Show
* **Live Board** — Kanban view of all queues with Call Next button
* **Auto-next** — automatically calls the next waiting token when current is Done
* **Partner creation** — auto-creates or finds a matching res.partner per token
* **SMS & WhatsApp webhooks** — notify customers when their number is called
* **Display webhook** — push events to a TV/screen queue display
* **Access groups** — separate User and Manager roles
    """,
    'author': 'Imran Alam',
    'website': 'https://github.com/imranaalam/odoo-queue-management',
    'depends': ['base', 'mail'],
    'data': [
        'security/queue_management_security.xml',
        'security/ir.model.access.csv',
        'data/queue_demo_data.xml',
        'views/report_queue_token.xml',
        'views/queue_service_category_views.xml',
        'views/queue_service_views.xml',
        'views/queue_queue_views.xml',
        'views/queue_token_views.xml',
        'views/queue_quick_wizard_views.xml',
        'views/queue_kiosk_views.xml',
        'views/queue_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'queue_management/static/src/scss/kiosk.scss',
            'queue_management/static/src/xml/kiosk_screen.xml',
            'queue_management/static/src/js/kiosk_screen.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
