# -*- coding: utf-8 -*-
"""
Rebuild the binder_showcase/ website ASSETS (data.js, cifs.js, pae/*.png).

WHAT THIS DOES / DOES NOT DO
  - Regenerates assets/ from the current resultv3/ results. Run it after new AF3 jobs land.
  - Does NOT write index.html — that is the hand-authored app (edit it directly for UI changes).

USAGE
  python binder_showcase/build/build_site.py            # threshold = 0.7 (default)
  python binder_showcase/build/build_site.py 0.75       # lighter variant

DEPENDENCIES:  numpy, matplotlib, Pillow  (torch NOT required — PAE/pLDDT come from full_data JSON)
"""
import json, os, io, base64, re, collections, sys, urllib.request, ssl
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

# ---- paths (robust: derived from this file's location) ----
BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
OUT       = os.path.dirname(BUILD_DIR)                 # .../binder_showcase
ROOT      = os.path.dirname(OUT)                       # .../tcr-redesign
ASSETS    = os.path.join(OUT, 'assets')
PAEDIR    = os.path.join(ASSETS, 'pae')
os.chdir(ROOT)
for d in (ASSETS, PAEDIR): os.makedirs(d, exist_ok=True)

THR = float(sys.argv[1]) if len(sys.argv) > 1 else 0.7

# ---- ensure 3Dmol-min.js present (download once if missing) ----
tdmol = os.path.join(ASSETS, '3Dmol-min.js')
if not os.path.exists(tdmol):
    print('3Dmol-min.js missing -> downloading from 3dmol.org ...')
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request('https://3dmol.org/build/3Dmol-min.js', headers={'User-Agent': 'Mozilla/5.0'})
    open(tdmol, 'wb').write(urllib.request.urlopen(req, timeout=30, context=ctx).read())

# ---- one-pass index of every model_0.cif under resultv3/hotspot (exclude archive) ----
idx = {}
for root, dirs, files in os.walk('resultv3/hotspot'):
    if '_archive_' in root: continue
    for fn in files:
        m = re.match(r'fold_(.+)_model_0\.cif$', fn)
        if m:
            fid = m.group(1); base = fid[:-4] if fid.endswith('_v54') else fid
            idx[base] = os.path.join(root, fn).replace(os.sep, '/')
print('indexed model_0.cif files:', len(idx))

def norm(cid): return cid.lower().replace('-', '_').replace('.', '_')

def parse_chains(path):
    """Residue count per chain from the mmCIF _atom_site loop."""
    header = []; cols = {}; in_loop = False; seq = collections.defaultdict(set)
    for line in open(path):
        if line.startswith('_atom_site.'):
            header.append(line.strip().split('.')[1]); in_loop = True; continue
        if in_loop and (line.startswith('ATOM') or line.startswith('HETATM')):
            if not cols: cols = {n: i for i, n in enumerate(header)}
            p = line.split()
            try: seq[p[cols['label_asym_id']]].add(p[cols['label_seq_id']])
            except Exception: pass
        elif in_loop and not line.startswith('_'):
            if not (line.startswith('ATOM') or line.startswith('HETATM')): in_loop = False
    return {k: len(v) for k, v in seq.items()}

def roles_of(chains, binder_len):
    """peptide = shortest chain; binder = remaining chain closest to the designed length; rest = MHC."""
    items = sorted(chains.items(), key=lambda kv: kv[1]); role = {}
    if items:
        role[items[0][0]] = 'peptide'
        rem = [k for k, _ in items[1:]]
        if rem:
            b = min(rem, key=lambda k: abs(chains[k] - binder_len)); role[b] = 'binder'
            for k in rem:
                if k != b: role[k] = 'mhc'
    return role

def render_pae(pae, tcids, roles, outpath):
    """AF3-style PAE heatmap: green colormap, chain boundaries, role labels. Downsampled + palette-quantized PNG."""
    a = np.array(pae, dtype='float32'); N = a.shape[0]; cap = 170
    if N > cap:
        step = int(np.ceil(N / cap)); nb = int(np.ceil(N / step)); pad = nb * step - N
        a = np.pad(a, ((0, pad), (0, pad)), mode='edge').reshape(nb, step, nb, step).mean(axis=(1, 3))
        scale = a.shape[0] / N
    else:
        scale = 1.0
    fig, ax = plt.subplots(figsize=(2.5, 2.5), dpi=100)
    ax.imshow(a, cmap='Greens_r', vmin=0, vmax=31.75, interpolation='nearest')
    segs = []; start = 0
    for i in range(1, N + 1):
        if i == N or tcids[i] != tcids[i - 1]: segs.append((start, i, tcids[start])); start = i
    for s, e, _ in segs[1:]:
        ax.axhline(s * scale - 0.5, color='white', lw=0.7); ax.axvline(s * scale - 0.5, color='white', lw=0.7)
    rm = {'binder': 'Binder', 'mhc': 'MHC', 'peptide': 'Pep'}
    ticks = [((s + e) / 2) * scale for s, e, _ in segs]; labs = [rm.get(roles.get(c, ''), c) for s, e, c in segs]
    ax.set_xticks(ticks); ax.set_xticklabels(labs, fontsize=7, color='#425a57')
    ax.set_yticks(ticks); ax.set_yticklabels(labs, fontsize=7, color='#425a57', rotation=90, va='center')
    ax.tick_params(length=0)
    for sp in ax.spines.values(): sp.set_visible(False)
    fig.tight_layout(pad=0.15)
    buf = io.BytesIO(); fig.savefig(buf, format='png', pad_inches=0.03, bbox_inches='tight'); plt.close(fig)
    buf.seek(0); Image.open(buf).convert('RGB').quantize(colors=96, method=Image.MEDIANCUT).save(outpath, optimize=True)

# ---- load results ----
meta = json.load(open('resultv3/candidates_metadata.json')); cands = meta['candidates']
def comp(c):
    a = c.get('af3') or {}; return a.get('composite_iptm')
def gpos(c):
    return (c.get('geom') or {}).get('position')   # on_peptide / touching / off_peptide
scored = [c for c in cands if comp(c) is not None]

# The DB decides what is a correct result — the site only displays it. `triage` is
# written by scripts/apply_geom_triage.py from REAL binder<->peptide geometry:
#   ACCEPT = on/edge peptide contact AND composite >= threshold  (position-verified hit)
#   REDESIGN = docked on peptide but weak -> ProteinMPNN pool
#   REJECT = off_peptide (bound to MHC / floating) — NOT shown
# Sync the displayed threshold to whatever the DB used, so all text stays consistent.
GT = meta.get('_summary', {}).get('geom_triage', {})
THR = GT.get('threshold', THR)
hits = [c for c in scored if c.get('triage') == 'ACCEPT' and norm(c['id']) in idx]
hits.sort(key=lambda c: -comp(c))
# dedup by id (same designed binder folded in >1 batch): keep the higher-composite occurrence
seen = set(); uniq = []
for c in hits:
    if c['id'] in seen: continue
    seen.add(c['id']); uniq.append(c)
n_jobs = len(hits); hits = uniq
grank = {c['id']: i + 1 for i, c in enumerate(hits)}
print('composite >=', THR, ':', n_jobs, 'AF3 jobs ->', len(hits), 'unique designs')

# ---- per-design: CIF text, chain roles, PAE png, pLDDT ----
CIFS = {}; binder_objs = {}
for k, c in enumerate(hits):
    cid = c['id']; cif = idx[norm(cid)]; jf = os.path.dirname(cif); fid = os.path.basename(jf)
    bs = (c.get('af3') or {}).get('best_seed', 0)
    chains = parse_chains(cif); roles = roles_of(chains, int(c['length']))
    fd = json.load(open(os.path.join(jf, 'fold_' + fid + '_full_data_' + str(bs) + '.json')))
    ap = np.array(fd['atom_plddts'], dtype='float32'); acid = fd['atom_chain_ids']
    bch = next((ch for ch, r in roles.items() if r == 'binder'), None)
    mask = np.array([x == bch for x in acid], dtype=bool)
    plddt_all = float(ap.mean()); plddt_bind = float(ap[mask].mean()) if mask.any() else plddt_all
    render_pae(fd['pae'], fd['token_chain_ids'], roles, os.path.join(PAEDIR, cid + '.png'))
    CIFS[cid] = open(cif, encoding='utf-8', errors='replace').read()
    a = c['af3']
    binder_objs[cid] = {'id': cid, 'grank': grank[cid], 'peptide': c['peptide'], 'mhc': c['mhc'],
        'cls': c.get('mhc_class'), 'category': c.get('category'), 'source': c.get('source'),
        'composite': round(comp(c), 3), 'bp_iptm': round(a.get('binder_pep_iptm', 0), 3),
        'iptm': round(a.get('iptm', 0), 3), 'ptm': round(a.get('ptm', 0), 3),
        'ranking': round(a.get('ranking_score', 0), 2), 'length': int(c['length']),
        'plddt': round(plddt_all, 1), 'plddt_binder': round(plddt_bind, 1),
        'sequence': c['sequence'], 'roles': roles, 'peptide_contact': a.get('peptide_contact'),
        # real geometric position (heavy-atom binder<->peptide)
        'position': gpos(c),
        'min_dist_bp': (c.get('geom') or {}).get('min_dist_bp'),
        'n_pep_contact': (c.get('geom') or {}).get('n_pep_contact')}
    if (k + 1) % 20 == 0: print('  processed', k + 1, '/', len(hits))

# ---- group by pMHC target ----
groups = collections.defaultdict(list)
for c in hits: groups[(c['peptide'], c['mhc'])].append(c)
targets = []
for (pep, mhc), cs in groups.items():
    cs = sorted(cs, key=lambda c: -comp(c)); bl = [binder_objs[c['id']] for c in cs]
    targets.append({'key': pep + '|' + mhc, 'peptide': pep, 'mhc': mhc, 'cls': cs[0].get('mhc_class'),
        'category': cs[0].get('category'), 'best': round(comp(cs[0]), 3), 'n': len(bl), 'binders': bl})
targets.sort(key=lambda t: -t['best'])

# ---- summary chart datasets (candidate-row level, over all scored) ----
THRS = [0.5, 0.6, 0.7, 0.8]; nsc = len(scored)
pass_counts = {t: sum(1 for c in scored if comp(c) >= t) for t in THRS}
tgt_best = collections.defaultdict(float)
for c in scored: tgt_best[(c['peptide'], c['mhc'])] = max(tgt_best[(c['peptide'], c['mhc'])], comp(c))
coverage = {t: sum(1 for v in tgt_best.values() if v >= t) for t in THRS}
def cs_(sub):
    v = [comp(c) for c in sub]; n = len(v)
    return {'n': n, 'mean': round(sum(v) / n, 3), 'hit07': sum(1 for x in v if x >= 0.7),
            'rate07': round(sum(1 for x in v if x >= 0.7) / n, 4)}
cls = {'I': cs_([c for c in scored if c.get('mhc_class') == 'I']), 'II': cs_([c for c in scored if c.get('mhc_class') == 'II'])}
cat_order = ['training', 'training_uncovered', 'unseen', 'neoantigen', 'autoimmune', 'infectious', 'infectious_variant', 'TAA']
cath = collections.Counter(c.get('category') for c in scored if comp(c) >= 0.7)
cat_data = [{'cat': k, 'hits07': cath.get(k, 0)} for k in cat_order if cath.get(k, 0) > 0]
edges = [round(0.10 + 0.05 * i, 2) for i in range(17)]; hist = [0] * (len(edges) - 1)
for c in scored:
    v = comp(c)
    for i in range(len(edges) - 1):
        if edges[i] <= v < edges[i + 1] or (i == len(edges) - 2 and v == edges[-1]): hist[i] += 1; break
dist = {'edges': edges, 'counts': hist}
cmp_rows = json.load(open('resultv3/redesign_v2_comparison.json'))['rows']
ba = [{'peptide': r['peptide'], 'mhc': r['mhc'], 'v1': round(r['v1_composite'], 3),
       'v2': round(r['v2_composite'], 3), 'd': round(r['v2_composite'] - r['v1_composite'], 3)} for r in cmp_rows]
rescued = sorted([b for b in ba if b['v2'] >= 0.7], key=lambda b: -b['v2'])
CFM_S, AF3_MIN, AF3_COST = 1.27, 3.5, 0.10   # RTX4070 s/cand ; A100 min/AF3-job ; $/job
timing = []
for t in [0.6, 0.7, 0.8]:
    rate = pass_counts[t] / nsc; jph = 1 / rate
    timing.append({'thr': t, 'rate': round(rate * 100, 1), 'jobs_per_hit': round(jph, 1),
        'cfm_s': round(jph * CFM_S, 0), 'e2e_min': round(jph * AF3_MIN, 0), 'cost': round(jph * AF3_COST, 2)})

# ---- triage funnel (from the DB's triage labels, over all scored designs) ----
tri = collections.Counter(c.get('triage') for c in scored)
pos = collections.Counter(gpos(c) for c in scored if c.get('geom'))
triage = {'n_scored': nsc,
          'accept': tri.get('ACCEPT', 0), 'redesign': tri.get('REDESIGN', 0),
          'reject': tri.get('REJECT', 0),
          'on_peptide': pos.get('on_peptide', 0), 'touching': pos.get('touching', 0),
          'off_peptide': pos.get('off_peptide', 0)}

DATA = {'meta': {'n_scored': nsc, 'N_TARGETS': 187, 'thr': THR, 'n_hits': len(hits), 'n_jobs': n_jobs,
                 'n_targets': len(targets)},
        'pass_counts': pass_counts, 'coverage': coverage, 'cls': cls, 'cat_data': cat_data,
        'dist': dist, 'rescued': rescued, 'timing': timing, 'targets': targets, 'triage': triage}

# ---- write assets ----
with open(os.path.join(ASSETS, 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.DATA=' + json.dumps(DATA, ensure_ascii=False, separators=(',', ':')) + ';')
with open(os.path.join(ASSETS, 'cifs.js'), 'w', encoding='utf-8') as f:
    f.write('window.CIFS=' + json.dumps(CIFS, ensure_ascii=False, separators=(',', ':')) + ';')
print('DONE. designs=%d  targets=%d  data.js=%.2fMB  cifs.js=%.1fMB  pae=%d files'
      % (len(hits), len(targets), os.path.getsize(os.path.join(ASSETS, 'data.js')) / 1e6,
         os.path.getsize(os.path.join(ASSETS, 'cifs.js')) / 1e6, len(os.listdir(PAEDIR))))
