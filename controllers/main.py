"""
queue_management REST API
=========================

Base URL:  /queue-management/api/v1/

Endpoints
---------
GET  /queue-management/api/v1/queue/<id>
    Returns current status of a queue (state, waiting count, current token).
    Auth: public (read-only).

POST /queue-management/api/v1/queue/<id>/token
    Creates a new token for the queue.
    Body (JSON): { name?, phone?, source? }
    Auth: public.

POST /queue-management/api/v1/queue/<id>/call_next
    Calls the next waiting token.
    Auth: requires api_key header matching queue display_webhook_url or open.

POST /queue-management/api/v1/token/<id>/call
    Calls (or re-calls) a specific token.
    Auth: public.

POST /queue-management/api/v1/token/<id>/done
    Marks a specific token as Done.
    Auth: public.

POST /queue-management/api/v1/token/<id>/skip
    Marks a specific token as Skipped.
    Auth: public.
"""

import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

_JSON_HEADERS = [('Content-Type', 'application/json')]


def _ok(data):
    return Response(json.dumps(data), status=200, headers=_JSON_HEADERS)


def _err(msg, status=400):
    return Response(json.dumps({'error': msg}), status=status, headers=_JSON_HEADERS)


class QueueManagementController(http.Controller):

    # ── Queue status ──────────────────────────────────────────────────────────
    @http.route(
        '/queue-management/api/v1/queue/<int:queue_id>',
        auth='public', methods=['GET'], type='http', csrf=False
    )
    def queue_status(self, queue_id, **kw):
        """GET current status of a queue."""
        try:
            status = request.env['queue.queue'].sudo().get_status(queue_id)
            if 'error' in status:
                return _err(status['error'], status=404)
            return _ok(status)
        except Exception as e:
            _logger.exception('queue_status error')
            return _err(str(e), status=500)

    # ── Create token ─────────────────────────────────────────────────────────
    @http.route(
        '/queue-management/api/v1/queue/<int:queue_id>/token',
        auth='public', methods=['POST'], type='http', csrf=False
    )
    def create_token(self, queue_id, **kw):
        """POST – create a new token for the queue."""
        try:
            body = {}
            if request.httprequest.data:
                body = json.loads(request.httprequest.data.decode('utf-8'))

            result = request.env['queue.queue'].sudo().create_token(
                queue_id,
                customer_name=body.get('name'),
                customer_phone=body.get('phone'),
                source=body.get('source', 'api'),
                notes=body.get('notes'),
            )
            if 'error' in result:
                return _err(result['error'], status=404)
            return _ok(result)
        except Exception as e:
            _logger.exception('create_token error')
            return _err(str(e), status=500)

    # ── Call next ─────────────────────────────────────────────────────────────
    @http.route(
        '/queue-management/api/v1/queue/<int:queue_id>/call_next',
        auth='public', methods=['POST'], type='http', csrf=False
    )
    def call_next(self, queue_id, **kw):
        """POST – call the next waiting token."""
        try:
            result = request.env['queue.queue'].sudo().call_next(queue_id)
            if not result:
                return _err('No waiting tokens', status=404)
            return _ok(result)
        except Exception as e:
            _logger.exception('call_next error')
            return _err(str(e), status=500)

    # ── Token actions ─────────────────────────────────────────────────────────
    @http.route(
        '/queue-management/api/v1/token/<int:token_id>/call',
        auth='public', methods=['POST'], type='http', csrf=False
    )
    def token_call(self, token_id, **kw):
        """POST – call (or re-call) a specific token."""
        return self._token_action(token_id, 'action_call')

    @http.route(
        '/queue-management/api/v1/token/<int:token_id>/done',
        auth='public', methods=['POST'], type='http', csrf=False
    )
    def token_done(self, token_id, **kw):
        """POST – mark a token as Done."""
        return self._token_action(token_id, 'action_done')

    @http.route(
        '/queue-management/api/v1/token/<int:token_id>/skip',
        auth='public', methods=['POST'], type='http', csrf=False
    )
    def token_skip(self, token_id, **kw):
        """POST – mark a token as Skipped."""
        return self._token_action(token_id, 'action_skip')

    @http.route(
        '/queue-management/api/v1/token/<int:token_id>/reset',
        auth='public', methods=['POST'], type='http', csrf=False
    )
    def token_reset(self, token_id, **kw):
        """POST – reset a skipped/no-show token back to Waiting."""
        return self._token_action(token_id, 'action_reset')

    # ── Helper ────────────────────────────────────────────────────────────────
    def _token_action(self, token_id, method_name):
        try:
            token = request.env['queue.token'].sudo().browse(token_id)
            if not token.exists():
                return _err('Token not found', status=404)
            getattr(token, method_name)()
            return _ok({
                'id':             token.id,
                'display_number': token.display_number,
                'state':          token.state,
                'queue_id':       token.queue_id.id,
                'queue_name':     token.queue_id.name,
            })
        except Exception as e:
            _logger.exception('%s error', method_name)
            return _err(str(e), status=500)
