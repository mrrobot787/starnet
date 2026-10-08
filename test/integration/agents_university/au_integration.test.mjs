import assert from 'assert';
import path from 'path';
import fs from 'fs/promises';
import { pathToFileURL } from 'url';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REGISTRY_ADAPTER_PATH = pathToFileURL(path.join(__dirname, '../../../sidecar/agents/au-registry-adapter.mjs')).href;
const DATA_BRIDGE_PATH = pathToFileURL(path.join(__dirname, '../../../sidecar/services/au-data-bridge.mjs')).href;

const { auRegistryAdapter } = await import(REGISTRY_ADAPTER_PATH);
const { auDataBridge } = await import(DATA_BRIDGE_PATH);
import approvalLedger from '../../../sidecar/governance/approval-ledger.js';

async function runTests() {
    console.log('🚀 Starting EP-000001 Agents University Integration Test Suite\n');
    let passed = 0;
    let failed = 0;

    async function test(id, description, fn) {
        try {
            await fn();
            console.log(`✅ ${id}: ${description}`);
            passed++;
        } catch (e) {
            console.error(`❌ ${id}: ${description}\n   Error: ${e.message}`);
            failed++;
        }
    }

    process.env.STARNET_AUTH_TOKEN = 'verified-token-123';
    await auRegistryAdapter.initialize();
    await auDataBridge.initialize();

    const validAgent = {
        agent_id: 'test-agent-01',
        title: 'Test Agent',
        version: '1.0.0',
        owner: { unit: 'Test Unit', contact: 'test@starnet.com' },
        environment: {
            name: 'Research Library',
            runtime: ['python3.11'],
            network: { egress: ['internet'], ingress: ['api'] }
        },
        tools: [{ name: 'search_tool', capabilities: ['search'] }],
        system_prompt: 'You are a helpful assistant for testing purposes.',
        autonomy: { level: 1, description: 'Assist' },
        guardrails: { red_lines: ['Do not reveal secrets'] }
    };

    const agentHash = 'hash-123';

    await test('AU-T01', 'Valid AU agent definition', async () => {
        const result = await auRegistryAdapter.validateAndMapAgent(validAgent);
        assert.strictEqual(result.starnetId, 'au-test-agent-01');
    });

    await test('AU-T03', 'Autonomy level 3 rejection', async () => {
        const level3Agent = { ...validAgent, autonomy: { level: 3 } };
        await assert.rejects(async () => await auRegistryAdapter.validateAndMapAgent(level3Agent), /UNAUTHORIZED_AUTONOMY_LEVEL/);
    });

    await test('AU-T09', 'Data bridge secret isolation', async () => {
        const bridgeContent = await fs.readFile(DATA_BRIDGE_PATH, 'utf8');
        const lines = bridgeContent.split('\n');
        const hasRealReference = lines.some(line => !line.trim().startsWith('//') && line.includes('config.json'));
        assert.ok(!hasRealReference, 'Bridge must not reference AU config.json in executable code');
    });

    await test('AU-T10-A', 'Data bridge: Reject missing trusted context', async () => {
        const result = await auDataBridge.fetchGovernedData('clinical_records', 'SELECT *', {});
        assert.strictEqual(result.status, 'UNAUTHORIZED');
        assert.strictEqual(result.error, 'Missing trusted runtime context');
    });

    await test('AU-T10-B', 'Data bridge: Reject PENDING_REVIEW agent', async () => {
        await approvalLedger.setApproval('au-test-agent-01', {
            definitionHash: agentHash, status: 'PENDING_REVIEW', approver: 'sys', timestamp: new Date().toISOString()
        });
        const result = await auDataBridge.fetchGovernedData('clinical_records', 'SELECT *', {
            agentId: 'au-test-agent-01',
            definitionHash: agentHash,
            sessionToken: 'valid-session'
        });
        assert.strictEqual(result.status, 'UNAUTHORIZED');
        assert.strictEqual(result.error, 'Agent not approved for execution');
    });

    await test('AU-T10-C', 'Data bridge: Reject hash mismatch', async () => {
        await approvalLedger.setApproval('au-test-agent-01', {
            definitionHash: 'correct-hash', status: 'ACTIVE', approver: 'sys', timestamp: new Date().toISOString()
        });
        const result = await auDataBridge.fetchGovernedData('clinical_records', 'SELECT *', {
            agentId: 'au-test-agent-01',
            definitionHash: 'wrong-hash',
            sessionToken: 'valid-session'
        });
        assert.strictEqual(result.status, 'UNAUTHORIZED');
    });

    await test('AU-T10-D', 'Data bridge: Allow ACTIVE agent with grant', async () => {
        await approvalLedger.setApproval('au-test-agent-01', {
            definitionHash: agentHash, status: 'ACTIVE', approver: 'sys', timestamp: new Date().toISOString()
        });
        const result = await auDataBridge.fetchGovernedData('clinical_records', 'SELECT *', {
            agentId: 'au-test-agent-01',
            definitionHash: agentHash,
            sessionToken: 'valid-session'
        });
        assert.strictEqual(result.status, 'SUCCESS');
    });

    console.log(`\nTest Summary: ${passed}/${failed + passed} passed.`);
    if (failed > 0) process.exit(1);
}

runTests().catch(e => {
    console.error(e);
    process.exit(1);
});
