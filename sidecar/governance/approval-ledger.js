'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');

/**
 * AU Approval Ledger
 *
 * Durable store for Agent University registration and approval states.
 * Enforces that only ACTIVE agents with verified definition hashes can operate.
 */

const LEDGER_PATH = path.join(process.cwd(), 'sidecar/governance/approval_ledger.json');

class ApprovalLedger {
    constructor() {
        this.ledger = null;
    }

    async initialize() {
        try {
            const data = await fs.readFile(LEDGER_PATH, 'utf8');
            this.ledger = JSON.parse(data);
            console.log('[AU-Ledger] Approval ledger loaded.');
        } catch (error) {
            console.warn('[AU-Ledger] Ledger not found or malformed; initializing empty ledger (FAIL-CLOSED).');
            this.ledger = {};
            await this.save();
        }
    }

    async save() {
        await fs.writeFile(LEDGER_PATH, JSON.stringify(this.ledger, null, 2));
    }

    async getApproval(agentId) {
        if (!this.ledger) await this.initialize();
        return this.ledger[agentId] || null;
    }

    async setApproval(agentId, { definitionHash, status, approver, timestamp }) {
        if (!this.ledger) await this.initialize();

        this.ledger[agentId] = {
            definitionHash,
            status, // 'PENDING_REVIEW' | 'ACTIVE' | 'REVOKED'
            approver,
            timestamp,
            revocationHistory: []
        };
        await this.save();
    }

    async revoke(agentId, reason, revoker) {
        if (!this.ledger) await this.initialize();
        const entry = this.ledger[agentId];
        if (!entry) throw new Error('AGENT_NOT_FOUND');

        entry.status = 'REVOKED';
        entry.revocationHistory.push({
            timestamp: new Date().toISOString(),
            reason,
            revoker
        });
        await this.save();
    }

    async isApproved(agentId, currentHash) {
        const entry = await this.getApproval(agentId);
        if (!entry) return false;
        if (entry.status !== 'ACTIVE') return false;
        if (entry.definitionHash !== currentHash) return false; // Version bound
        return true;
    }
}

module.exports = new ApprovalLedger();
