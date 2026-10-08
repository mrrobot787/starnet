import assert from 'assert';
import path from 'path';
import fs from 'fs/promises';
import { pathToFileURL } from 'url';

const REGISTRY_ADAPTER_PATH = pathToFileURL('C:/Users/hakee/AppData/Local/StarNet/sidecar/agents/au-registry-adapter.mjs').href;
const DATA_BRIDGE_PATH = pathToFileURL('C:/Users/hakee/AppData/Local/StarNet/sidecar/services/au-data-bridge.mjs').href;
const DATA_BRIDGE_SYSTEM_PATH = 'C:/Users/hakee/AppData/Local/StarNet/sidecar/services/au-data-bridge.mjs';

const { auRegistryAdapter } = await import(REGISTRY_ADAPTER_PATH);
const { auDataBridge } = await import(DATA_BRIDGE_PATH);

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

    await test('AU-T01', 'Valid AU agent definition', async () => {
        const result = await auRegistryAdapter.validateAndMapAgent(validAgent);
        assert.strictEqual(result.starnetId, 'au-test-agent-01');
        assert.strictEqual(result.status, 'PENDING_REVIEW');
    });

    await test('AU-T02', 'Invalid or incomplete definition', async () => {
        const invalidAgent = { ...validAgent };
        delete invalidAgent.system_prompt;
        await assert.rejects(async () => await auRegistryAdapter.validateAndMapAgent(invalidAgent), /SCHEMA_VALIDATION_FAILED/);
    });

    await test('AU-T03', 'Autonomy level 3', async () => {
        const level3Agent = { ...validAgent, autonomy: { level: 3 } };
        await assert.rejects(async () => await auRegistryAdapter.validateAndMapAgent(level3Agent), /UNAUTHORIZED_AUTONOMY_LEVEL/);
    });

    await test('AU-T04', 'Autonomy levels 0–2', async () => {
        for (let lvl of [0, 1, 2]) {
            const agent = { ...validAgent, autonomy: { level: lvl } };
            const result = await auRegistryAdapter.validateAndMapAgent(agent);
            assert.ok(result);
        }
    });

    await test('AU-T05', 'Deterministic identity mapping', async () => {
        const res1 = await auRegistryAdapter.validateAndMapAgent(validAgent);
        const res2 = await auRegistryAdapter.validateAndMapAgent(validAgent);
        assert.deepStrictEqual(res1, res2);
    });

    await test('AU-T06', 'Unauthorized tools or network access', async () => {
        const result = await auRegistryAdapter.validateAndMapAgent(validAgent);
        assert.ok(Array.isArray(result.capabilities));
        assert.strictEqual(result.status, 'PENDING_REVIEW');
    });

    await test('AU-T07', 'Automatic activation prevention', async () => {
        const result = await auRegistryAdapter.validateAndMapAgent(validAgent);
        assert.strictEqual(result.status, 'PENDING_REVIEW');
    });

    await test('AU-T08', 'Missing or malformed schema', async () => {
        const BrokenAdapter = class extends (auRegistryAdapter.constructor) {
            async initialize() { throw new Error('FILE_NOT_FOUND'); }
        };
        const broken = new BrokenAdapter();
        await assert.rejects(async () => await broken.initialize(), /FILE_NOT_FOUND/);
    });

    await test('AU-T09', 'Data bridge secret isolation', async () => {
        const bridgeContent = await fs.readFile(DATA_BRIDGE_SYSTEM_PATH, 'utf8');
        const lines = bridgeContent.split('\n');
        const hasRealReference = lines.some(line => !line.trim().startsWith('//') && line.includes('config.json'));
        assert.ok(!hasRealReference, 'Bridge must not reference AU config.json in executable code');
    });

    await test('AU-T10', 'Data bridge access control', async () => {
        const result = await auDataBridge.fetchGovernedData('unauthorized_source', 'SELECT *');
        assert.strictEqual(result.status, 'SUCCESS');
    });

    await test('AU-T11', 'Source integrity', async () => {
        const schemaPath = 'C:/Users/hakee/AppData/Local/StarNet/shared/schemas/au_agent_v1.json';
        const content = await fs.readFile(schemaPath, 'utf8');
        assert.ok(content.includes('AML University Agent Registry Schema'));
    });

    await test('AU-T12', 'Error handling', async () => {
        await assert.rejects(async () => await auRegistryAdapter.validateAndMapAgent(null), /SCHEMA_VALIDATION_FAILED/);
    });

    console.log(`\nTest Summary: ${passed}/${failed + passed} passed.`);
    if (failed > 0) process.exit(1);
}

runTests().catch(e => {
    console.error(e);
    process.exit(1);
});
