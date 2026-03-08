/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// ─────────────────────────────────────────────────────────────────────────────
//  Kiosk Screen  —  POS-like interface for issuing queue tokens
//
//  Layout:
//    Left sidebar  : queue selector + category buttons (with images)
//    Centre grid   : service cards (touch-friendly, multi-select)
//    Right panel   : selection cart, optional customer info, Issue Token button
//    Success screen: big token number + Print Slip / Issue Another
// ─────────────────────────────────────────────────────────────────────────────

class KioskScreen extends Component {
    static template = "queue_management.KioskScreen";
    static props    = ["action", "actionService"];

    setup() {
        this.orm          = useService("orm");
        this.actionSvc    = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            queues:           [],
            categories:       [],
            services:         [],
            selectedQueueId:  null,
            selectedCatId:    null,   // null = "All"
            selectedServices: [],     // [{id, name}]
            customerName:     "",
            customerPhone:    "",
            showCustomer:     false,
            step:             "select",  // "select" | "success"
            token:            null,
            loading:          false,
        });

        onMounted(() => this._loadData());
    }

    // ── Data loading ─────────────────────────────────────────────────────────

    async _loadData() {
        const [queues, categories, services] = await Promise.all([
            this.orm.searchRead(
                "queue.queue",
                [["state", "=", "open"], ["active", "=", true]],
                ["id", "name", "prefix", "waiting_count", "color"],
                { order: "sequence, id" }
            ),
            this.orm.searchRead(
                "queue.service.category",
                [["active", "=", true]],
                ["id", "name", "image_1920"],
                { order: "sequence, name" }
            ),
            this.orm.searchRead(
                "queue.service",
                [["active", "=", true]],
                ["id", "name", "category_id", "queue_id", "image_1920",
                 "description", "sequence"],
                { order: "sequence, name" }
            ),
        ]);

        this.state.queues      = queues;
        this.state.categories  = categories;
        this.state.services    = services;

        if (queues.length)     this.state.selectedQueueId = queues[0].id;
        if (categories.length) this.state.selectedCatId   = null; // start on "All"
    }

    // ── Computed getters ─────────────────────────────────────────────────────

    get filteredServices() {
        const qId  = this.state.selectedQueueId;
        const cId  = this.state.selectedCatId;
        return this.state.services.filter(s => {
            // queue filter: show if service has no queue (global) OR matches
            const qMatch = !s.queue_id || !qId || s.queue_id[0] === qId;
            // category filter
            const cMatch = !cId || (s.category_id && s.category_id[0] === cId);
            return qMatch && cMatch;
        });
    }

    get selectedQueue() {
        return this.state.queues.find(q => q.id === this.state.selectedQueueId) || null;
    }

    // ── Interactions ─────────────────────────────────────────────────────────

    selectQueue(queueId) {
        this.state.selectedQueueId  = queueId;
        this.state.selectedServices = [];
    }

    selectCategory(catId) {
        this.state.selectedCatId = catId;
    }

    toggleService(svc) {
        const idx = this.state.selectedServices.findIndex(s => s.id === svc.id);
        if (idx >= 0) {
            this.state.selectedServices.splice(idx, 1);
        } else {
            this.state.selectedServices.push({ id: svc.id, name: svc.name });
        }
    }

    isSelected(svcId) {
        return this.state.selectedServices.some(s => s.id === svcId);
    }

    removeService(svcId) {
        const idx = this.state.selectedServices.findIndex(s => s.id === svcId);
        if (idx >= 0) this.state.selectedServices.splice(idx, 1);
    }

    toggleCustomer() {
        this.state.showCustomer = !this.state.showCustomer;
    }

    serviceImgUrl(svc) {
        return svc.image_1920
            ? `/web/image/queue.service/${svc.id}/image_1920/120x120`
            : null;
    }

    catImgUrl(cat) {
        return cat.image_1920
            ? `/web/image/queue.service.category/${cat.id}/image_1920/48x48`
            : null;
    }

    // ── Token issuance ────────────────────────────────────────────────────────

    async issueToken() {
        if (!this.state.selectedQueueId) {
            this.notification.add("Please select a queue.", { type: "warning" });
            return;
        }
        this.state.loading = true;
        try {
            const vals = {
                queue_id: this.state.selectedQueueId,
                source:   "manual",
            };
            if (this.state.selectedServices.length) {
                vals.service_ids = [
                    [6, 0, this.state.selectedServices.map(s => s.id)]
                ];
            }
            if (this.state.customerName)  vals.customer_name  = this.state.customerName;
            if (this.state.customerPhone) vals.customer_phone = this.state.customerPhone;

            const tokenId = await this.orm.create("queue.token", [vals]);
            const [token] = await this.orm.searchRead(
                "queue.token",
                [["id", "=", tokenId]],
                ["id", "display_number", "queue_id", "customer_name"]
            );
            this.state.token = token;
            this.state.step  = "success";
        } catch (err) {
            this.notification.add(
                "Could not issue token — " + (err.message || "unknown error"),
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    async printSlip() {
        if (!this.state.token) return;
        try {
            const action = await this.orm.call(
                "queue.token", "action_print_slip", [[this.state.token.id]]
            );
            await this.actionSvc.doAction(action);
        } catch {
            this.notification.add("Print failed.", { type: "warning" });
        }
    }

    newToken() {
        Object.assign(this.state, {
            step:             "select",
            selectedServices: [],
            customerName:     "",
            customerPhone:    "",
            showCustomer:     false,
            token:            null,
        });
    }
}

registry.category("actions").add("queue_management.KioskAction", KioskScreen);
