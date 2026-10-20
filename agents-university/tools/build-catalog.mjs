#!/usr/bin/env node
/* Builds agents-university/catalog.json, the machine-readable index the
   agents-university-library skill reads. Output is deterministic (sorted, no timestamps)
   so `--check` can fail CI when the catalog is stale.

   usage: node agents-university/tools/build-catalog.mjs [--check] */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, relative, extname, basename, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'catalog.json');
const SKIP_TOP = new Set(['tools', 'skill']);
const SKIP_FILES = new Set(['catalog.json']);

const AREAS = {
  'training-hospital': {
    title: 'Agent Training Hospital',
    summary: 'Hospital roles (triage nurse, attending physician, pharmacist, CMA orchestrator), ontology, schema, policy service, pipeline integration, demos.',
    source: 'mrrobot787/ClosedLoopSystem_AML_Ops_PitCrew (AgentHospital, services/hospital, agents/)'
  },
  'data-management': {
    title: 'Agent University Data Manager',
    summary: 'Data source registry, governance framework, scoring, safety gates, storage layers, orchestrator, connector configs.',
    source: 'mrrobot787/ClosedLoopSystem_AML_Ops_PitCrew (DataManagement)'
  },
  'agent-registry': {
    title: 'AML University Agent Registry',
    summary: 'Agent registry package (models, database, API, CLI, checkpoints, monitoring, safety guards), JSON schema, examples.',
    source: 'mrrobot787/ClosedLoopSystem_AML_Ops_PitCrew (agents/registry, schemas, examples)'
  },
  'launchers': {
    title: 'AML University launchers',
    summary: 'Launcher, test runner, desktop shortcut, university.ps1 helper.',
    source: 'mrrobot787/ClosedLoopSystem_AML_Ops_PitCrew'
  },
  'triage-agent': {
    title: 'Agents University triage agent',
    summary: 'University triage agent script, tests, design doc, Streamlit dashboard.',
    source: 'mrrobot787/AML'
  },
  'docs': {
    title: 'Agents University documentation',
    summary: 'Rebranding summary, verifier architecture, engineering replication reports, execution-ready pack.',
    source: 'mrrobot787/ClosedLoopSystem_AML_Ops_PitCrew, local drafts'
  },
  'deploy': {
    title: 'Deployment',
    summary: 'nginx site config for the AML University site.',
    source: 'mrrobot787/ClosedLoopSystem_AML_Ops_PitCrew (nginx)'
  },
  '.': {
    title: 'Overview',
    summary: 'Folder map and provenance for the consolidated assets.',
    source: 'mrrobot787/starnet'
  }
};

const KINDS = {
  '.md': 'doc', '.txt': 'doc', '.py': 'code', '.js': 'code', '.mjs': 'code', '.sql': 'schema',
  '.yaml': 'config', '.yml': 'config', '.json': 'config', '.conf': 'config', '.bat': 'script', '.ps1': 'script'
};

function walk(dir, out = []) {
  for (const name of readdirSync(dir).sort()) {
    const full = join(dir, name);
    const rel = relative(ROOT, full).replace(/\\/g, '/');
    if (statSync(full).isDirectory()) {
      if (!rel.includes('/') && SKIP_TOP.has(name)) continue;
      walk(full, out);
    } else if (!SKIP_FILES.has(rel)) {
      out.push(rel);
    }
  }
  return out;
}

function clip(s, n) {
  s = String(s || '').replace(/\s+/g, ' ').trim();
  return s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s;
}

function describe(rel, text) {
  const ext = extname(rel).toLowerCase();
  const lines = text.split('\n');
  let title = '', summary = '';
  if (ext === '.md') {
    let fenced = false;
    for (const l of lines) {
      if (/^\s*```/.test(l)) { fenced = !fenced; continue; }
      if (!fenced && /^\s{0,3}#{1,3}\s+\S/.test(l)) { title = l.trim().replace(/^#+\s+/, ''); break; }
    }
    let inFence = false, inFront = lines[0] === '---';
    for (let i = inFront ? 1 : 0; i < lines.length; i++) {
      const l = lines[i].trim();
      if (inFront) { if (l === '---') inFront = false; continue; }
      if (l.startsWith('```')) { inFence = !inFence; continue; }
      if (inFence || !l || /^(#|[-*_=]{3,}|\||<|!\[|\[!\[)/.test(l)) continue;
      summary = l.replace(/^[-*>]\s+/, '').replace(/\*\*/g, '');
      break;
    }
  } else if (ext === '.py') {
    const m = text.match(/^(?:#![^\n]*\n)?(?:\s*#[^\n]*\n)*\s*(?:"""|''')([\s\S]*?)(?:"""|''')/);
    const doc = m ? m[1].trim().split('\n').map(s => s.trim()).filter(Boolean) : [];
    title = doc[0] || '';
    summary = doc.slice(1).join(' ');
    if (!title) {
      const c = lines.find(l => /^#(?!!)\s*\S/.test(l));
      title = c ? c.replace(/^#\s*/, '') : '';
    }
  } else if (ext === '.ps1' && /\.SYNOPSIS/i.test(text)) {
    const at = lines.findIndex(l => /^\s*\.SYNOPSIS/i.test(l));
    title = (lines.slice(at + 1).find(l => l.trim()) || '').trim();
    const d = lines.findIndex(l => /^\s*\.DESCRIPTION/i.test(l));
    if (d >= 0) summary = lines.slice(d + 1).filter(l => l.trim() && !/^\s*\./.test(l)).slice(0, 4).join(' ');
  } else {
    const c = lines.find(l => /^\s*(#(?!!)|--|\/\/|REM\s|::)\s*\S/i.test(l));
    title = c ? c.replace(/^\s*(#|--|\/\/|REM|::)\s*/i, '') : '';
    if (ext === '.json') {
      try { const j = JSON.parse(text); title = j.title || j.name || j.$id || title; summary = j.description || ''; } catch (_) {}
    } else if (ext === '.yaml' || ext === '.yml') {
      const d = lines.find(l => /^\s*(name|description):\s*\S/.test(l));
      if (!title && d) title = d.replace(/^\s*\w+:\s*/, '').replace(/^["']|["']$/g, '');
    }
  }
  return { title: clip(title || basename(rel), 120), summary: clip(summary, 280) };
}

function build() {
  const files = walk(ROOT).map(rel => {
    const raw = readFileSync(join(ROOT, rel));
    const text = raw.toString('utf8').replace(/\r\n/g, '\n');
    const area = rel.includes('/') ? rel.split('/')[0] : '.';
    const { title, summary } = describe(rel, text);
    return {
      path: rel,
      area,
      kind: /(^|\/)tests?\/|(^|\/)test_[^/]+$/.test(rel) ? 'test' : (KINDS[extname(rel).toLowerCase()] || 'other'),
      title,
      summary,
      lines: text.split('\n').length,
      bytes: Buffer.byteLength(text, 'utf8'),
      sha256: createHash('sha256').update(text, 'utf8').digest('hex')
    };
  });
  const counts = {};
  for (const f of files) counts[f.area] = (counts[f.area] || 0) + 1;
  const areas = Object.keys(AREAS).filter(a => counts[a]).map(a => Object.assign({ id: a, files: counts[a] }, AREAS[a]));
  const unknown = Object.keys(counts).filter(a => !AREAS[a]);
  if (unknown.length) throw new Error('add AREAS entries for: ' + unknown.join(', '));
  return JSON.stringify({
    format: 'agents-university-catalog/v1',
    repo: 'mrrobot787/starnet',
    root: 'agents-university',
    note: 'Text is hashed with LF line endings. Databases, logs, and env files are intentionally absent.',
    areas,
    files
  }, null, 2) + '\n';
}

const next = build();
if (process.argv.includes('--check')) {
  const cur = existsSync(OUT) ? readFileSync(OUT, 'utf8').replace(/\r\n/g, '\n') : '';
  if (cur !== next) {
    console.error('agents-university/catalog.json is stale; run: node agents-university/tools/build-catalog.mjs');
    process.exit(1);
  }
  console.log('catalog.json is up to date');
} else {
  writeFileSync(OUT, next);
  const n = JSON.parse(next).files.length;
  console.log('wrote ' + relative(process.cwd(), OUT) + ' (' + n + ' files)');
}
