import fs from 'fs/promises';
import path from 'path';
import approvalLedger from '../governance/approval-ledger.js';

/**
 * AU Data Bridge
 *
 * Enforces native StarNet authorization and AU Approval Ledger status.
 */

export class AUDataBridge {
    constructor() {
        this.config = null;
        this.authorizedSources = new Set(['clinical_records', 'research_archive', 'hospital_ontology']);
    }

    async initialize() {
        try {
            if (!process.env.STARNET_AUTH_TOKEN) {
                throw new Error('AUTH_TOKEN_MISSING');
            }
            this.config = { managed: true, source: 'agents-university' };
        } catch (error) {
            console.error('[AU-Bridge] Initialization failed:', error);
            throw error;
        }
    }

    /**
     * @param {string} dataSourceId
     * @param {Object} query
     * @param {Object} runtimeContext - Trusted context containing { agentId, definitionHash, sessionToken }
     */
    async fetchGovernedData(dataSourceId, query, runtimeContext = {}) {
        if (!this.config) await this.initialize();

        // 1. Verify Runtime Context exists
        if (!runtimeContext || !runtimeContext.agentId || !runtimeContext.sessionToken) {
            return { data: null, status: 'UNAUTHORIZED', error: 'Missing trusted runtime context' };
        }

        // 2. CHECK APPROVAL LEDGER (The critical gate)
        const isApproved = await approvalLedger.isApproved(runtimeContext.agentId, runtimeContext.definitionHash);
        if (!isApproved) {
            console.warn(`[AU-Bridge] REJECTED: Agent ${runtimeContext.agentId} is not ACTIVE or hash mismatch.`);
            return { data: null, status: 'UNAUTHORIZED', error: 'Agent not approved for execution' };
        }

        // 3. Verify Source Whitelist
        if (!this.authorizedSources.has(dataSourceId)) {
            return { data: null, status: 'UNAUTHORIZED', error: 'Source not approved' };
        }

        console.log(`[AU-Bridge] AUTHORIZED: Agent ${runtimeContext.agentId} accessing ${dataSourceId}.`);
        return { data: [], status: 'SUCCESS' };
    }
}

export const auDataBridge = new AUDataBridge();
