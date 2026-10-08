import fs from 'fs/promises';
import path from 'path';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { fileURLToPath } from 'url';

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCHEMA_PATH = path.join(__dirname, '../../shared/schemas/au_agent_v1.json');

export class AURegistryAdapter {
    constructor() {
        this.validator = null;
    }

    async initialize() {
        try {
            const schemaData = JSON.parse(await fs.readFile(SCHEMA_PATH, 'utf8'));
            this.validator = ajv.compile(schemaData);
            console.log('[AU-Adapter] Schema initialized.');
        } catch (error) {
            console.error('[AU-Adapter] Schema load failure:', error);
            throw new Error('SCHEMA_LOAD_FAILURE');
        }
    }

    async validateAndMapAgent(agentDefinition) {
        if (!this.validator) await this.initialize();

        if (!agentDefinition) {
            throw new Error('SCHEMA_VALIDATION_FAILED: Input is null or undefined');
        }

        const isValid = this.validator(agentDefinition);
        if (!isValid) {
            const errors = this.validator.errors.map(e => `${e.instancePath} ${e.message}`).join('; ');
            throw new Error(`SCHEMA_VALIDATION_FAILED: ${errors}`);
        }

        if (agentDefinition.autonomy.level === 3) {
            throw new Error('UNAUTHORIZED_AUTONOMY_LEVEL: Level 3 restricted.');
        }

        return {
            starnetId: `au-${agentDefinition.agent_id}`,
            provenance: 'agents-university',
            version: agentDefinition.version,
            capabilities: agentDefinition.tools.map(t => t.name),
            constraints: agentDefinition.guardrails.red_lines,
            status: 'PENDING_REVIEW'
        };
    }
}

export const auRegistryAdapter = new AURegistryAdapter();
