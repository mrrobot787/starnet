#!/usr/bin/env node
/* Agents University library finder. Zero dependencies; Node 18+.

   Finds and reads the consolidated Agents University / Agent Training Hospital assets in
   mrrobot787/starnet under agents-university/. Uses a local checkout when one is found,
   otherwise reads the public repo over HTTPS and caches files by content hash.

   usage:
     node au.mjs areas
     node au.mjs list   [--area A] [--kind K]
     node au.mjs search <terms...> [--area A] [--kind K] [--limit N] [--quick]
     node au.mjs show   <path> [--lines START:END] [--all]
     node au.mjs where
   global flags: --json  --root DIR  --ref GIT_REF */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname, resolve, basename } from 'node:path';
import { tmpdir } from 'node:os';

const REPO = 'mrrobot787/starnet';
const DIR = 'agents-university';
const DEFAULT_REFS = ['refs/heads/feat/harness-backend', 'refs/heads/chore/import-agents-university'];
const SHOW_MAX_LINES = 400;
const TIMEOUT_MS = 15000;

function parseArgs(argv) {
  const out = { _: [], flags: {} };
  const valued = new Set(['area', 'kind', 'limit', 'lines', 'root', 'ref']);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const [k, v] = a.slice(2).split('=', 2);
      if (v !== undefined) out.flags[k] = v;
      else if (valued.has(k)) out.flags[k] = argv[++i];
      else out.flags[k] = true;
    } else out._.push(a);
  }
  return out;
}

const sha = text => createHash('sha256').update(text, 'utf8').digest('hex');
const lf = text => text.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
const clip = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);

function findLocalRoot(explicit) {
  for (const given of [explicit, process.env.AU_ROOT].filter(Boolean)) {
    const p = resolve(given);
    for (const cand of [p, join(p, DIR)]) if (existsSync(join(cand, 'catalog.json'))) return cand;
    throw new Error('no catalog.json under ' + p);
  }
  for (let d = process.cwd(); ; d = dirname(d)) {
    for (const cand of [join(d, DIR), d]) {
      if (basename(cand) === DIR && existsSync(join(cand, 'catalog.json'))) return cand;
    }
    if (dirname(d) === d) return null;
  }
}

async function httpText(url) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(url, { signal: ctrl.signal, headers: { 'user-agent': 'agents-university-library/1' } });
    if (!r.ok) { const e = new Error('HTTP ' + r.status + ' for ' + url); e.status = r.status; throw e; }
    return await r.text();
  } catch (e) {
    if (ctrl.signal.aborted) throw new Error('timed out fetching ' + url);
    throw e;
  } finally { clearTimeout(t); }
}

async function openSource(flags) {
  const root = findLocalRoot(flags.root);
  if (root) {
    const catalog = JSON.parse(lf(readFileSync(join(root, 'catalog.json'), 'utf8')));
    return { kind: 'local', location: root, catalog, read: async p => lf(readFileSync(join(root, p), 'utf8')) };
  }
  const refs = flags.ref ? [flags.ref] : (process.env.AU_REF ? [process.env.AU_REF] : DEFAULT_REFS);
  let lastErr;
  for (const ref of refs) {
    const base = 'https://raw.githubusercontent.com/' + REPO + '/' + ref + '/' + DIR + '/';
    try {
      const catalog = JSON.parse(lf(await httpText(base + 'catalog.json')));
      const cacheDir = join(tmpdir(), 'agents-university-cache');
      mkdirSync(cacheDir, { recursive: true });
      const read = async p => {
        const entry = catalog.files.find(f => f.path === p);
        const cached = entry && join(cacheDir, entry.sha256 + '.txt');
        if (cached && existsSync(cached)) return readFileSync(cached, 'utf8');
        const text = lf(await httpText(base + p.split('/').map(encodeURIComponent).join('/')));
        if (entry && sha(text) === entry.sha256) writeFileSync(cached, text);
        return text;
      };
      return { kind: 'remote', location: base, ref, catalog, read };
    } catch (e) { lastErr = e; if (e.status !== 404) break; }
  }
  throw new Error('could not reach the Agents University catalog (' + (lastErr && lastErr.message) + '). ' +
    'Pass --root <path to agents-university> or --ref <git ref>.');
}

function filterEntries(files, flags) {
  return files.filter(f => (!flags.area || f.area === flags.area) && (!flags.kind || f.kind === flags.kind));
}

async function readAll(src, entries, warnings) {
  const out = new Map();
  let i = 0;
  async function worker() {
    while (i < entries.length) {
      const e = entries[i++];
      try {
        const text = await src.read(e.path);
        if (sha(text) !== e.sha256) warnings.push(e.path + ' differs from catalog.json (edited locally or catalog is stale)');
        out.set(e.path, text);
      } catch (err) { warnings.push('could not read ' + e.path + ': ' + err.message); }
    }
  }
  await Promise.all(Array.from({ length: src.kind === 'remote' ? 8 : 1 }, worker));
  return out;
}

function scoreEntry(e, terms, text) {
  const title = e.title.toLowerCase(), path = e.path.toLowerCase(), summary = e.summary.toLowerCase();
  const body = text ? text.toLowerCase() : '';
  let score = 0, matched = 0;
  for (const t of terms) {
    let s = 0;
    if (title.includes(t)) s += 5;
    if (path.includes(t)) s += 3;
    if (summary.includes(t)) s += 2;
    if (body) {
      let n = 0, at = -1;
      while (n < 20 && (at = body.indexOf(t, at + 1)) >= 0) n++;
      s += n * 0.5;
    }
    if (s > 0) matched++;
    score += s;
  }
  return { score, matched };
}

function snippets(text, terms, max = 3) {
  const out = [];
  const lines = text.split('\n');
  for (let i = 0; i < lines.length && out.length < max; i++) {
    const l = lines[i].toLowerCase();
    if (terms.some(t => l.includes(t))) out.push({ line: i + 1, text: clip(lines[i].trim(), 160) });
  }
  return out;
}

function resolvePath(files, arg) {
  const want = arg.replace(/\\/g, '/').replace(/^\.?\/?(agents-university\/)?/, '');
  const exact = files.find(f => f.path === want);
  if (exact) return [exact];
  const lower = want.toLowerCase();
  return files.filter(f => f.path.toLowerCase().endsWith('/' + lower) || basename(f.path).toLowerCase() === lower ||
    f.path.toLowerCase().includes(lower));
}

function print(flags, data, text) {
  if (flags.json) process.stdout.write(JSON.stringify(data, null, 2) + '\n');
  else process.stdout.write(text.join('\n') + '\n');
}

async function main() {
  const { _: [cmd = 'help', ...rest], flags } = parseArgs(process.argv.slice(2));
  if (cmd === 'help' || flags.help) {
    console.log(readFileSync(new URL(import.meta.url), 'utf8').match(/usage:[\s\S]*?\*\//)[0].replace(/\*\/$/, '').trim());
    return;
  }
  const src = await openSource(flags);
  const files = src.catalog.files;
  const warnings = [];

  if (cmd === 'where') {
    print(flags, { source: src.kind, location: src.location, ref: src.ref || null, files: files.length },
      ['source: ' + src.kind, 'location: ' + src.location, src.ref ? 'ref: ' + src.ref : '', 'files: ' + files.length].filter(Boolean));
  } else if (cmd === 'areas') {
    print(flags, src.catalog.areas, src.catalog.areas.map(a =>
      a.id.padEnd(18) + String(a.files).padStart(3) + ' files  ' + a.title + '\n' + ' '.repeat(18) + a.summary + '\n' + ' '.repeat(18) + 'source: ' + a.source));
  } else if (cmd === 'list') {
    const list = filterEntries(files, flags);
    print(flags, list, list.map(f => f.path.padEnd(64) + ' ' + f.kind.padEnd(6) + ' ' + clip(f.title, 70)));
  } else if (cmd === 'search') {
    const query = rest.join(' ').trim().toLowerCase();
    if (!query) throw new Error('search needs terms, e.g.: search triage nurse risk');
    const terms = Array.from(new Set(query.split(/\s+/).filter(t => t.length > 1)));
    const pool = filterEntries(files, flags);
    const texts = flags.quick ? new Map() : await readAll(src, pool, warnings);
    let scored = pool.map(e => Object.assign({ entry: e }, scoreEntry(e, terms, texts.get(e.path))))
      .filter(r => r.score > 0);
    const all = scored.filter(r => r.matched === terms.length);
    const mode = all.length ? 'all terms' : 'any term';
    if (all.length) scored = all;
    scored.sort((a, b) => b.score - a.score || a.entry.path.localeCompare(b.entry.path));
    const limit = Math.max(1, Number(flags.limit) || 8);
    const top = scored.slice(0, limit).map(r => ({
      path: r.entry.path, area: r.entry.area, kind: r.entry.kind, score: Math.round(r.score * 10) / 10,
      title: r.entry.title, summary: r.entry.summary,
      snippets: texts.has(r.entry.path) ? snippets(texts.get(r.entry.path), terms) : []
    }));
    const lines = [scored.length + ' match(es) for "' + query + '" (' + mode + '), showing ' + top.length + ':'];
    for (const r of top) {
      lines.push('', '[' + r.score + '] ' + r.path + '  (' + r.area + ', ' + r.kind + ')', '    ' + r.title + (r.summary ? ' - ' + clip(r.summary, 140) : ''));
      for (const s of r.snippets) lines.push('    L' + s.line + ': ' + s.text);
    }
    if (top.length) lines.push('', 'read one with: node au.mjs show ' + top[0].path);
    print(flags, { query, mode, total: scored.length, results: top }, lines);
  } else if (cmd === 'show') {
    if (!rest[0]) throw new Error('show needs a path, e.g.: show training-hospital/core/triage_nurse.py');
    const hits = resolvePath(files, rest[0]);
    if (hits.length !== 1) {
      const msg = hits.length ? 'ambiguous path; candidates:\n  ' + hits.map(h => h.path).join('\n  ') : 'no file matches ' + rest[0] + '; try: search ' + rest[0];
      throw Object.assign(new Error(msg), { code: 2 });
    }
    const e = hits[0];
    const text = (await readAll(src, [e], warnings)).get(e.path);
    if (text == null) throw new Error(warnings.pop() || 'could not read ' + e.path);
    const all = text.split('\n');
    let [start, end] = String(flags.lines || '').split(':').map(n => parseInt(n, 10));
    start = Math.max(1, start || 1);
    end = Math.min(all.length, end || (flags.all ? all.length : start + SHOW_MAX_LINES - 1));
    const body = all.slice(start - 1, end);
    const lines = ['# ' + e.path + '  (' + e.area + ', ' + e.kind + ', ' + all.length + ' lines)', '# ' + e.title, ''];
    body.forEach((l, i) => lines.push(String(start + i).padStart(5) + '| ' + l));
    if (end < all.length) lines.push('', '... ' + (all.length - end) + ' more lines; continue with --lines ' + (end + 1) + ':' + Math.min(all.length, end + SHOW_MAX_LINES));
    print(flags, { path: e.path, area: e.area, kind: e.kind, title: e.title, start, end, totalLines: all.length, content: body.join('\n') }, lines);
  } else {
    throw Object.assign(new Error('unknown command "' + cmd + '"; run: node au.mjs help'), { code: 2 });
  }
  for (const w of warnings) console.error('warning: ' + w);
}

main().catch(err => {
  console.error('error: ' + err.message);
  process.exit(err.code === 2 ? 2 : 1);
});
