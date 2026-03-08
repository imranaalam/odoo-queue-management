{
    'name': 'Queue Management',
    'version': '17.0.1.0.0',
    'category': 'Services',
    'summary': 'Universal queue management — numbered tokens, live board, SMS/WhatsApp webhooks, REST API',
    'description': """
Queue Management
================

A fully standalone queue management system that works for ANY use case:
clinics, banks, government offices, retail counters, service desks.

No dependency on Point of Sale — install and use independently.

Key Features
------------
* **Multiple named queues** — each with its own prefix, colour, and webhook URLs
* **Token lifecycle** — Waiting → Called → Serving → Done / Skipped / No-Show
* **Live Board** — Kanban view grouped by state, drag-and-drop style
* **Call Next** and **Call Specific** from the queue form
* **Auto-next** — automatically calls the next waiting token when current is Done
* **Partner creation** — auto-creates or finds a matching res.partner per token
* **REST API** — external kiosk / display screen integration
* **SMS & WhatsApp webhooks** — notify customers when their number is called
* **Display webhook** — push events to a TV/screen queue display
* **Backend dashboard** — manage all queues and tokens from one place
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
        'views/queue_service_views.xml',
        'views/queue_queue_views.xml',
        'views/queue_token_views.xml',
        'views/queue_quick_wizard_views.xml',
        'views/queue_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
