# Queue Management — Odoo 17

[![Odoo 17](https://img.shields.io/badge/Odoo-17.0-875A7B)](https://www.odoo.com)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL%203-brightgreen.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Category: Services](https://img.shields.io/badge/Category-Services-informational)]()

**Universal queue management system for Odoo 17.**
Works for any use case — clinics, banks, government counters, retail desks — with no dependency on Point of Sale.

---

## Features

| Feature | Description |
|---|---|
| 📋 **Multiple Queues** | Create named queues, each with its own prefix, colour, and webhook URLs |
| 🎫 **Token Lifecycle** | Waiting → Called → Serving → Done / Skipped / No-Show |
| 📺 **Live Board** | Kanban view grouped by state — Call and Done from the card |
| 📢 **Call Next / Auto-Next** | One-click or automatic progression through the queue |
| 📱 **SMS & WhatsApp** | Per-queue webhooks fire when a token is called |
| 📺 **External Display** | Display webhook for TV screens and digital signage |
| 🔗 **REST API** | Issue tokens, call next, mark done via JSON HTTP |
| 👤 **Partner Integration** | Auto-creates/matches `res.partner` from name/phone |
| 🔒 **Access Groups** | User (issue & call) and Manager (configure & delete) roles |

---

## Installation

### From source (Docker / Odoo)
```bash
# 1. Copy module to your addons path
cp -r queue_management /mnt/extra-addons/

# 2. Restart Odoo
docker restart odoo

# 3. Install from Apps menu  (search "Queue Management")
# OR install via CLI:
docker exec -it odoo odoo -d <database> -i queue_management --stop-after-init
```

### Verification
After install you should see **Queue Management** in the main Odoo menu with a green icon.
A default *Main Queue* (prefix `Q`) is created automatically.

---

## Quick Start

1. Go to **Queue Management → Queues** — your *Main Queue* is ready
2. Open the queue form → **Tokens** tab → add a row (or use the REST API)
3. Click **📢 Call Next** in the header to call the first waiting token
4. Switch to **Live Board** to manage all active tokens visually

---

## REST API

Base URL: `/queue-management/api/v1/`

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/queue/{id}` | Queue status |
| `POST` | `/queue/{id}/token` | Issue new token |
| `POST` | `/queue/{id}/call_next` | Call next waiting |
| `POST` | `/token/{id}/call` | Call specific token |
| `POST` | `/token/{id}/done` | Mark done |
| `POST` | `/token/{id}/skip` | Mark skipped |
| `POST` | `/token/{id}/reset` | Reset to waiting |

**Create token example:**
```bash
curl -X POST http://localhost:8069/queue-management/api/v1/queue/1/token \
  -H "Content-Type: application/json" \
  -d '{"name": "Ali Ahmed", "phone": "+971501234567", "source": "kiosk"}'
```

**Response:**
```json
{
  "id": 42,
  "number": 7,
  "display_number": "Q007",
  "customer_name": "Ali Ahmed",
  "customer_phone": "+971501234567",
  "state": "waiting",
  "queue_name": "Main Queue"
}
```

---

## Webhook Payload

Fires on: `new_token`, `token_called`, `token_serving`, `token_done`

```json
{
  "action": "token_called",
  "queue_id": 1,
  "queue_name": "Main Queue",
  "token_id": 42,
  "display_number": "Q007",
  "customer_name": "Ali Ahmed",
  "customer_phone": "+971501234567",
  "state": "called",
  "waiting_count": 3,
  "timestamp": "2026-03-07 14:30:00"
}
```

---

## Module Structure

```
queue_management/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── queue_queue.py     # queue.queue — Queue configuration model
│   └── queue_token.py     # queue.token — Individual tokens/tickets
├── controllers/
│   └── main.py            # REST API controller
├── views/
│   ├── queue_queue_views.xml   # Kanban, list, form, search
│   ├── queue_token_views.xml   # List, kanban (Live Board), form, search
│   └── queue_menus.xml         # Menu structure
├── security/
│   ├── queue_management_security.xml  # Groups: User, Manager
│   └── ir.model.access.csv
├── data/
│   └── queue_demo_data.xml    # Default "Main Queue"
└── static/description/
    ├── icon.png               # 128×128 app icon
    └── index.html             # Odoo Apps catalog description
```

---

## Relationship with `pos_queue_management`

| Module | Dependency | Use Case |
|---|---|---|
| **`queue_management`** | `base`, `mail` | Standalone — any queue use case |
| **`pos_queue_management`** | `point_of_sale` | POS connector — button, slip printing, receipt |

Both modules can be installed independently and coexist.

---

## Requirements

- Odoo **17.0**
- Dependencies: `base`, `mail` (both standard Odoo modules)
- No external Python packages (`requests` is pre-installed in Odoo)

---

## License

[LGPL-3](https://www.gnu.org/licenses/lgpl-3.0)

---

## Author

**Imran Alam** · [GitHub](https://github.com/imranaalam)
Companion module: [pos_queue_management](https://github.com/imranaalam/odoo-pos-queue-management)
