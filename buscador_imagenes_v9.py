#!/usr/bin/env python3
"""Buscador asistido de fotografías de Wikimedia Commons para un catálogo JSON.
No asigna fotografías sin aprobación explícita por ID y candidato.
"""
import argparse, csv, datetime as dt, html, json, re, shutil, sys, time, unicodedata
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from email.utils import parsedate_to_datetime
from datetime import timezone
import random, hashlib
from collections import Counter

API = 'https://commons.wikimedia.org/w/api.php'
AGENT = 'ArbolesExoticosOccidenteImageResearch/1.1 (catalog research; contact: https://github.com/JP-Cor/Arboles-Exoticos-Occidente)'
MIN_GAP = 5.0
_last_request = 0.0
LICENSES = ('cc0', 'cc-by-3.0', 'cc-by-4.0', 'cc-by-sa-3.0', 'cc-by-sa-4.0', 'public domain', 'public-domain', 'pdm')
FIELDS = ('especie', 'nombre', 'nombre_comun', 'nombreComun', 'producto', 'variedad', 'cientifico', 'nombre_cientifico')

def throttled_open(req, timeout=35, retries=4):
    """Controla la tasa de peticiones y respeta Retry-After sin evadir límites."""
    global _last_request
    for attempt in range(retries + 1):
        wait = MIN_GAP - (time.monotonic() - _last_request)
        if wait > 0: time.sleep(wait)
        _last_request = time.monotonic()
        try:
            return urlopen(req, timeout=timeout)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise
            header = exc.headers.get('Retry-After', '').strip()
            pause = min(900, 30 * (2 ** attempt))
            if header:
                try: pause = max(pause, min(900, float(header)))
                except ValueError:
                    try:
                        date = parsedate_to_datetime(header)
                        pause = max(pause, min(900, (date - dt.datetime.now(timezone.utc)).total_seconds()))
                    except (TypeError, ValueError, OverflowError): pass
            pause += random.uniform(0, 2)
            print(f'HTTP {exc.code}: esperando {pause:.0f} s (intento {attempt+1}/{retries})', flush=True)
            time.sleep(pause)

def api(params):
    p = {'format':'json', 'formatversion':2, **params}
    req = Request(API + '?' + urlencode(p), headers={'User-Agent': AGENT, 'Accept':'application/json'})
    with throttled_open(req, timeout=35) as r: return json.load(r)

def download(url, path, limit=15_000_000):
    req=Request(url, headers={'User-Agent': AGENT})
    with throttled_open(req,timeout=60) as r, open(path,'wb') as f:
        total=0
        while True:
            block=r.read(65536)
            if not block: break
            total+=len(block)
            if total>limit: raise ValueError('Archivo demasiado grande')
            f.write(block)

def slug(s):
    s=unicodedata.normalize('NFKD',str(s))
    s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+','-',s.lower())).strip('-')[:85] or 'especie'

def clean(s): return re.sub('<[^>]*>', '', html.unescape(str(s or ''))).strip()

def load_catalog(path):
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if isinstance(data,list): return data,data,None
    if isinstance(data,dict):
        for key in ('productos','inventario','items','catalogo','data'):
            if isinstance(data.get(key),list): return data,data[key],key
    raise ValueError('No se encontró lista de productos. Ajusta load_catalog() a tu JSON.')

# V4: una fotografía real existente se conserva SIEMPRE.
# El logo es solo una imagen provisional, incluso si existe físicamente.
GENERIC_NAMES = {'logo.jpeg', 'logo.jpg', 'logo.png', 'logo.webp',
                 'logo-generico.webp', 'imagen-generica.webp', 'sin-foto.webp'}

def is_generic(v):
    if not isinstance(v, str) or not v.strip():
        return True
    s = v.strip().replace('\\', '/').split('?', 1)[0].strip('/').casefold()
    parts = s.split('/')
    return (parts[-1] in GENERIC_NAMES or
            ('generica' in parts and parts[-1].startswith('logo.')))

def photo_path(v, root):
    if not isinstance(v, str) or not v.strip() or is_generic(v):
        return None
    s = v.strip().replace('\\', '/')
    # Una URL externa no se sustituye automáticamente: requiere auditoría manual.
    if s.startswith(('http:', 'https:', 'data:', '//')):
        return 'EXTERNA_NO_SUSTITUIR'
    s = s.split('?', 1)[0].lstrip('/')
    options = [root / s, root / 'imagenes' / s, root / 'Inventario' / s]
    return next((p for p in options if p.is_file()), None)

def pending(rows, root):
    out = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        value = row.get('foto')
        # V4: solo imágenes vacías, logos o rutas locales rotas.
        if photo_path(value, root):
            continue
        name = next((str(row.get(k)).strip() for k in FIELDS if row.get(k)), '')
        if not name:
            continue
        out.append({'index': i, 'id': str(row.get('id', i)), 'name': name,
                    'scientific': str(row.get('cientifico') or row.get('nombre_cientifico') or '').strip(),
                    'previous': value or ''})
    return out

# V3: no aceptar homónimos (personas, edificios) como evidencia botánica.
ALIASES = {'lamb hass':['lamb hass','lamb-hass'], 'holls':['holls'], 'oro verde':['oro verde']}
BOTANICAL = ('avocado','aguacate','persea','fruit','fruto','fruta','plant','planta','tree','arbol','cultivar','variety','variedad','botanical','botanica','citrus','mango','mangifera','theobroma','cacao','flower','flor','leaves','hojas','seed','semilla')
NEGATIVE = ('portrait','retrato','building','edificio','hotel','church','iglesia','politician','politico','bishop','obispo','king','rey','street','calle','city','ciudad','actor','actress','football','soccer','estadio')
GENERIC_SCIENTIFIC = {'persea americana','citrus sinensis','mangifera indica','theobroma cacao','citrus reticulata'}

def normalized(value):
    return ' '.join(slug(value).replace('-', ' ').split())

def has_phrase(text, phrase):
    return bool(re.search(r'(?<!\w)' + re.escape(normalized(phrase)) + r'(?!\w)', text))

def botanical_context(g):
    """Contexto botánico sin asumir que un nombre comercial identifica la variedad."""
    sci = normalized(g.get('scientific', ''))
    name = normalized(g['name'])
    if 'persea americana' in sci or any(x in name for x in ('hass', 'holls', 'oro verde', 'aguacate')):
        return ['avocado', 'aguacate', 'persea americana']
    if 'punica granatum' in sci or 'granada' in name:
        return ['pomegranate', 'granada fruit', 'punica granatum']
    if 'rubus' in sci or 'mora' in name:
        return ['rubus', 'blackberry', 'mora fruit']
    if sci:
        return [sci, sci.split()[0]]
    return ['fruit', 'tree', 'plant']


# V8: evita que fotos de comida, mercados o variedades diferentes parezcan
# evidencia varietal. Una coincidencia textual NO certifica una variedad.
IRRELEVANT = ('salad', 'ensalada', 'fruit salad', 'smoothie', 'juice', 'jugo',
              'recipe', 'receta', 'restaurant', 'market', 'mercado', 'fruit bowl',
              'mixed fruit', 'fruits', 'basket', 'canasta', 'plate', 'plato',
              'guacamole', 'sandwich', 'cake', 'pastel', 'coconut', 'coco')
PLANT_CONTEXT = ('avocado', 'aguacate', 'persea', 'pomegranate', 'granada',
                 'punica', 'rubus', 'blackberry', 'mora', 'fruit', 'fruto',
                 'tree', 'arbol', 'plant', 'planta', 'leaves', 'hojas',
                 'branch', 'rama', 'orchard', 'cultivar', 'variety', 'variedad',
                 'citrus', 'mango', 'flower', 'flor', 'seed', 'semilla')
OTHER_CULTIVARS = ('lamb hass', 'hass', 'holls', 'oro verde', 'fuerte', 'reed',
                   'bacon', 'valencia', 'washington', 'navel', 'king',
                   'minneola', 'orlando')

def evidence(g, candidate):
    """Filtro conservador basado en metadatos, nunca en identidad visual."""
    title = normalized(candidate.get('title', ''))
    description = normalized(candidate.get('description', ''))
    hay = title + ' ' + description
    name = normalized(g['name'])
    sci = normalized(g.get('scientific', ''))
    context = botanical_context(g)
    if any(has_phrase(hay, term) for term in NEGATIVE + IRRELEVANT):
        return None
    if not any(has_phrase(hay, term) for term in context + list(PLANT_CONTEXT)):
        return None
    # Priorizar la frase más larga para evitar que 'hass' invalide 'lamb hass'.
    for other in sorted(OTHER_CULTIVARS, key=len, reverse=True):
        if has_phrase(hay, other) and not has_phrase(name, other) and not has_phrase(hay, name):
            return None
    exact = has_phrase(hay, name)
    # Una variedad no se confirma por el nombre científico de la especie.
    if exact:
        return ('variedad_mencionada', 'Nombre comercial mencionado; identidad varietal NO verificada. Revisar fuente.')
    if sci and has_phrase(hay, sci):
        return ('especie_sin_variedad', 'Nombre científico de especie; NO confirma la variedad.')
    if any(has_phrase(hay, term) for term in context):
        return ('especie_sin_variedad', 'Coincidencia botánica general; NO confirma la variedad.')
    return None

def search_group(g, limit):
    name = g['name'].strip()
    sci = g.get('scientific', '').strip()
    context = botanical_context(g)
    # Consultas de variedad primero, con exclusiones para reducir ruido.
    queries = [f'"{name}" {context[0]}', f'"{name}" cultivar tree']
    if sci:
        queries.append(f'"{name}" "{sci}"')
    # Fallback genérico únicamente para revisión manual.
    queries.append(f'"{sci}" fruit tree' if sci else f'{name} {context[0]} tree')
    found, seen = [], set()
    for q in dict.fromkeys(queries):
        for c in search(q, min(40, max(limit * 6, 18))):
            identity = c.get('page') or c.get('url')
            if identity in seen:
                continue
            seen.add(identity)
            result = evidence(g, c)
            if result:
                c['match_level'], c['evidence'] = result
                c['filter_version'] = 8
                found.append(c)
        if len(found) >= limit and sum(c['match_level'] == 'variedad_mencionada' for c in found) >= limit:
            break
    found.sort(key=lambda c: (c['match_level'] != 'variedad_mencionada',
                              not has_phrase(normalized(c.get('title','')), normalized(name)),
                              c.get('title','')))
    return found[:limit]

def search(q,limit=5):
    data=api({'action':'query','generator':'search','gsrsearch':'filetype:bitmap '+q,'gsrnamespace':6,'gsrlimit':limit,'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':1000})
    found=[]
    for pg in data.get('query',{}).get('pages',[]):
        infos=pg.get('imageinfo') or []
        if not infos: continue
        inf=infos[0]; meta=inf.get('extmetadata',{})
        get=lambda k: clean(meta.get(k,{}).get('value',''))
        lic=get('LicenseShortName'); code=get('License').lower()
        valid=any(x in (lic+' '+code).lower() for x in LICENSES)
        url=inf.get('thumburl') or inf.get('url','')
        if not valid or not url: continue
        if not url.lower().split('?')[0].endswith(('.jpg','.jpeg','.png','.webp')): continue
        found.append({'title':pg.get('title',''),'url':url,'page':inf.get('descriptionurl',''),
                      'author':get('Artist'),'license':lic,'license_url':get('LicenseUrl'),
                      'attribution':get('Attribution'),'description':get('ImageDescription')[:800]})
    return found

def build_html(groups, dest, decisions=None):
    """Galería interactiva local; exporta CSV sin modificar inventario."""
    decisions = decisions or {}
    pieces = ['<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Revisión de fotografías</title><style>\nbody{font:16px system-ui;max-width:1250px;margin:25px auto;padding:0 16px;background:#f3f7f3;color:#193d2c}section{background:white;padding:20px;margin:22px 0;border-radius:16px;box-shadow:0 3px 12px #0001}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:16px}.card{padding:12px;border:1px solid #dce8dc;border-radius:12px;min-width:0;overflow-wrap:anywhere}img{width:100%;height:195px;object-fit:contain;background:#f5f5f5;border-radius:8px}small{display:block;margin:7px 0}code{font-size:11px;overflow-wrap:anywhere}.toolbar{position:sticky;top:0;background:#e4f0e5;padding:12px;border-radius:10px;z-index:2}button{border:0;border-radius:8px;padding:10px 14px;cursor:pointer;background:#16663c;color:white}select{padding:9px;width:100%;margin-top:10px;border:1px solid #a9c6ae;border-radius:7px}a{color:#12613a}p{line-height:1.5}\n</style></head><body><h1>Revisión manual de fotografías</h1><p>Revisa la identidad de cada variedad y la licencia. Ninguna imagen se integra sin aprobación explícita. Si no la has revisado, deja PENDIENTE.</p><div class="toolbar"><button onclick="guardarProyecto()" type="button">💾 Guardar en el proyecto</button> <button onclick="exportar()" type="button">⬇ Exportar CSV</button> <button onclick="pendientes()" type="button">↩ Marcar todas pendientes</button> <label style="display:inline-block;margin:8px">📂 Importar CSV <input type="file" id="importar" accept=".csv,text/csv"></label> <span id="contador"></span><small>Para guardar directamente, abrí la galería mediante el comando servir. Si la abrís como archivo local, usá Exportar CSV y reemplazá el archivo manualmente. <strong id="estadoGuardado"></strong></small></div>']
    for g in groups:
        pieces.append('<section><h2>'+html.escape(g['name'])+'</h2><p>IDs: '+html.escape(', '.join(g['ids']))+'</p><div class="grid">')
        for c in g['candidates']:
            cid=c['candidate_id']
            state=decisions.get(cid, {}).get('aprobar', 'PENDIENTE').strip().upper()
            if state not in ('SI','NO','PENDIENTE'): state='PENDIENTE'
            pieces.append('<div class="card" data-group="'+html.escape(g['name']+'|'+g['scientific'],quote=True)+'"><img loading="lazy" src="'+html.escape(c['url'],quote=True)+'" alt="Candidato"><p><code>'+html.escape(cid)+'</code></p><small>'+html.escape(c['title'])+'</small><small>Licencia: '+html.escape(c['license'])+'</small><small>'+html.escape(c.get('evidence',''))+'</small><a target="_blank" rel="noopener" href="'+html.escape(c['page'],quote=True)+'">Ver fuente y autor</a><label><small>Decisión</small><select class="decision" data-id="'+html.escape(cid,quote=True)+'"><option value="PENDIENTE"'+(' selected' if state=='PENDIENTE' else '')+'>🟡 Pendiente</option><option value="SI"'+(' selected' if state=='SI' else '')+'>🟢 Aprobar</option><option value="NO"'+(' selected' if state=='NO' else '')+'>🔴 Rechazar</option></select></label><label><small>Nota (opcional)</small><input class="nota" style="width:95%" value="'+html.escape(decisions.get(cid,{}).get('nota',''),quote=True)+'"></label></div>')
        pieces.append('</div></section>')
    pieces.append(r"""<script>
const storageKey='arboles-exoticos-revision-v9';
function controles(){return [...document.querySelectorAll('.decision')];}
function filas(){return controles().map(s=>[s.dataset.id,s.value,s.closest('.card').querySelector('.nota').value]);}
function actualizar(){const a=filas(),n=x=>a.filter(r=>r[1]===x).length;document.getElementById('contador').textContent=`${n('SI')} aprobadas · ${n('NO')} rechazadas · ${n('PENDIENTE')} pendientes`;}
function guardar(){document.getElementById('estadoGuardado').textContent='Cambios sin guardar en CSV';try{localStorage.setItem(storageKey,JSON.stringify(Object.fromEntries(filas().map(r=>[r[0],[r[1],r[2]]]))));}catch(e){console.warn('No se pudo guardar temporalmente',e);}actualizar();}
function restaurar(){try{let saved=JSON.parse(localStorage.getItem(storageKey)||'{}');for(const s of controles()){const v=saved[s.dataset.id];if(v && ['SI','NO','PENDIENTE'].includes(v[0])){s.value=v[0];s.closest('.card').querySelector('.nota').value=v[1]||'';}}}catch(e){console.warn(e);}actualizar();}
async function guardarProyecto(){
if(location.protocol==='file:'){alert('Para guardar directamente, ejecutá el comando servir y abrí la dirección local que muestra la terminal.');return;}
 const btn=document.querySelector('button[onclick="guardarProyecto()"]');btn.disabled=true;
 try{
  const resp=await fetch('/guardar-aprobaciones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filas:filas()})});
  const result=await resp.json();if(!resp.ok)throw Error(result.error||'Error al guardar');
  document.getElementById('estadoGuardado').textContent='Guardado: '+result.total+' decisiones';
  alert('Guardado correctamente en reportes/busqueda_fotografias/aprobaciones.csv ('+result.total+' decisiones).');
 }catch(e){alert('No se guardó el CSV: '+e.message);}finally{btn.disabled=false;}
}
function exportar(){const quote=s=>'"'+String(s).replaceAll('"','""')+'"';const csv='candidate_id,aprobar,nota\r\n'+filas().map(r=>r.map(quote).join(',')).join('\r\n');const blob=new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='aprobaciones.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);}
function pendientes(){if(!confirm('¿Marcar TODOS los candidatos como PENDIENTE? No modifica el inventario.'))return;controles().forEach(s=>s.value='PENDIENTE');guardar();}
function parseCSV(txt){txt=txt.replace(/^\uFEFF/,'');let rows=[],row=[],field='',quoted=false;for(let i=0;i<txt.length;i++){let ch=txt[i];if(ch==='"'){if(quoted && txt[i+1]==='"'){field+='"';i++;}else quoted=!quoted;}else if(ch===','&&!quoted){row.push(field);field='';}else if((ch==='\n'||ch==='\r')&&!quoted){if(ch==='\r'&&txt[i+1]==='\n')i++;row.push(field);if(row.some(x=>x!==''))rows.push(row);row=[];field='';}else field+=ch;}row.push(field);if(row.some(x=>x!==''))rows.push(row);if(quoted)throw Error('CSV con comillas sin cerrar');return rows;}
document.getElementById('importar').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{const rows=parseCSV(await file.text());const head=rows.shift();const id=head.indexOf('candidate_id'),estado=head.indexOf('aprobar'),nota=head.indexOf('nota');if(id<0||estado<0)throw Error('El CSV debe contener candidate_id y aprobar');const byId=new Map(controles().map(s=>[s.dataset.id,s]));let count=0;for(const r of rows){const s=byId.get(r[id]),v=(r[estado]||'').trim().toUpperCase();if(s&&['SI','NO','PENDIENTE'].includes(v)){s.value=v;s.closest('.card').querySelector('.nota').value=nota<0?'':r[nota]||'';count++;}}guardar();alert('Importadas '+count+' decisiones. Exportá el CSV para guardar los cambios en el proyecto.');}catch(err){alert('No se pudo importar: '+err.message);}finally{e.target.value='';}});
document.addEventListener('change',e=>{if(e.target.matches('.decision')&&e.target.value==='SI'){const card=e.target.closest('.card'),group=card.dataset.group;const others=controles().filter(s=>s!==e.target&&s.closest('.card').dataset.group===group&&s.value==='SI');if(others.length){if(confirm('Ya hay otra foto aprobada para esta especie. ¿Sustituir la aprobación anterior?'))others.forEach(s=>s.value='PENDIENTE');else e.target.value='PENDIENTE';}}if(e.target.matches('.decision'))guardar();});
document.addEventListener('input',e=>{if(e.target.matches('.nota'))guardar();});
restaurar();
</script></body></html>""")
    dest.write_text('\n'.join(pieces),encoding='utf-8')

def group_key(g):
    return slug(g['name']) + '-' + hashlib.sha256((g['name'].casefold() + '|' + g['scientific'].casefold()).encode()).hexdigest()[:12]

def save_results(selected, out):
    (out/'candidatos.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
    csv_path = out/'aprobaciones.csv'
    existing = {}
    if csv_path.exists():
        with csv_path.open(encoding='utf-8-sig', newline='') as f:
            existing = {r['candidate_id']:r for r in csv.DictReader(f)}
    with csv_path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['candidate_id','aprobar','nota'])
        for g in selected:
            for c in g['candidates']:
                old=existing.get(c['candidate_id'],{})
                w.writerow([c['candidate_id'],old.get('aprobar','PENDIENTE'),old.get('nota','')])
    with csv_path.open(encoding='utf-8-sig',newline='') as f:
        decisions={r['candidate_id']:r for r in csv.DictReader(f)}
    build_html(selected,out/'revision.html',decisions)

def cmd_search(a):
    root=Path(a.root).resolve(); path=(root/a.inventory).resolve(); _,rows,_=load_catalog(path)
    pend=pending(rows,root)
    groups={}
    for p in pend:
        k=(p['name'].casefold(),p['scientific'].casefold())
        if k not in groups: groups[k]={'name':p['name'],'scientific':p['scientific'],'ids':[],'candidates':[]}
        groups[k]['ids'].append(p['id'])
    out=root/'reportes'/'busqueda_fotografias';out.mkdir(parents=True,exist_ok=True)
    cache_file=out/'cache_busquedas.json'
    cache=json.loads(cache_file.read_text(encoding='utf-8')) if cache_file.exists() else {}
    selected=[]
    for g in groups.values():
        key=group_key(g)
        if key in cache and cache[key].get('status')=='ok' and cache[key].get('version')==8 and not a.refresh:
            continue  # grupos ya investigados, incluso cuando no hubo candidatos
        selected.append(g)
        if len(selected)>=a.limit: break
    if not selected:
        print('No hay nuevos grupos para consultar. Usa --refresh si deseas repetir búsquedas.');return
    print('V8: búsqueda más selectiva; ninguna fotografía se aprueba automáticamente.')
    for ix,g in enumerate(selected,1):
        key=group_key(g)
        try:
            cs=search_group(g,a.candidates)
            for c in cs: c['candidate_id']=key+'-'+hashlib.sha256(('v8|'+(c.get('page') or c['url'])).encode()).hexdigest()[:12]
            g['candidates']=cs
            cache[key]={'status':'ok','version':8,'candidates':cs,'updated':dt.datetime.now().isoformat()}
            print(f"[{ix}/{len(selected)}] {g['name']}: {len(cs)} candidatos ({sum(c['match_level']=='variedad_mencionada' for c in cs)} con nombre exacto)",flush=True)
        except Exception as e:
            cache[key]={'status':'error','error':str(e)}
            print(f"[{ix}/{len(selected)}] ERROR {g['name']}: {e}",file=sys.stderr,flush=True)
        cache_file.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding='utf-8')
        # checkpoint sin borrar aprobaciones anteriores; acumular grupos en reporte
        previous=[]
        candidates_file=out/'candidatos.json'
        if candidates_file.exists():
            try: previous=json.loads(candidates_file.read_text(encoding='utf-8'))
            except (ValueError,OSError): pass
        if cache[key]['status']=='ok':
            previous=[x for x in previous if group_key(x)!=key]+[g]
        save_results(previous,out)
        time.sleep(max(0,a.delay))
    print('Revisión:',out/'revision.html')
    print('Aprobaciones:',out/'aprobaciones.csv')
    print('Pendientes:',len(pend),'| Grupos:',len(groups))

def cmd_apply(a):
    from PIL import Image, ImageOps, UnidentifiedImageError
    root=Path(a.root).resolve(); inv=(root/a.inventory).resolve()
    data,rows,_=load_catalog(inv)
    out=root/'reportes'/'busqueda_fotografias'
    groups=json.loads((out/'candidatos.json').read_text(encoding='utf-8'))
    with (out/'aprobaciones.csv').open(encoding='utf-8-sig',newline='') as f: approved=[r['candidate_id'].strip() for r in csv.DictReader(f) if r['aprobar'].strip().upper()=='SI']
    candidates={c['candidate_id']:(g,c) for g in groups for c in g['candidates']}
    for cid in approved:
        if cid in candidates and (candidates[cid][1].get('filter_version') != 8 or not evidence(candidates[cid][0], candidates[cid][1])):
            raise ValueError('Candidato anterior o sin evidencia botánica suficiente: '+cid)
    if len(approved)!=len(set(approved)):raise ValueError('Aprobación duplicada')
    chosen={}
    for cid in approved:
        if cid not in candidates:raise ValueError('Candidato desconocido: '+cid)
        g,c=candidates[cid]; key=(g['name'].casefold(),g['scientific'].casefold())
        if key in chosen:raise ValueError('Solo una imagen por grupo: '+g['name'])
        if c.get('match_level') == 'especie_sin_variedad':
            raise ValueError('Candidato genérico sin variedad confirmada: '+cid+'. No se puede aplicar automáticamente; requiere una fotografía varietal identificada.')
        chosen[key]=(g,c)
    if not chosen:print('No hay aprobaciones. Nada que modificar.');return
    print('Aprobaciones:',len(chosen),'| Modo:', 'APLICAR' if a.confirm else 'SIMULACIÓN')
    if not a.confirm:print('Para escribir cambios, ejecuta con --confirm después de revisar.');return
    backup=inv.with_name(inv.stem+'.backup-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+inv.suffix)
    shutil.copy2(inv,backup)
    dest=root/'imagenes'/'automatizadas';dest.mkdir(parents=True,exist_ok=True)
    records=[]; updated=0
    for key,(g,c) in chosen.items():
        target=dest/(slug(g['name'])+'-'+slug(g['scientific'])+'.webp')
        temp=out/'descarga_temporal.img'
        try:
            if target.exists():
                raise ValueError('Archivo destino ya existe; no se sobrescribe: '+str(target))
            download(c['url'],temp)
            with Image.open(temp) as raw:
                im=ImageOps.exif_transpose(raw).convert('RGBA')
                im.thumbnail((800,800),Image.Resampling.LANCZOS)
                bg=Image.new('RGB',(800,800),'white')
                if im.mode=='RGBA':bg.paste(im,((800-im.width)//2,(800-im.height)//2),im)
                else:bg.paste(im,((800-im.width)//2,(800-im.height)//2))
                bg.save(target,format='WEBP',quality=85,method=6)
            with Image.open(target) as check:check.verify()
            rel=target.relative_to(root).as_posix()
            changed=[]
            for row in rows:
                if not isinstance(row,dict):continue
                name=next((str(row.get(k)).strip() for k in FIELDS if row.get(k)), '')
                sci=str(row.get('cientifico') or row.get('nombre_cientifico') or '').strip()
                if (name.casefold(),sci.casefold())==key and not photo_path(row.get('foto'),root):
                    row['foto']=rel;changed.append(str(row.get('id','')));updated+=1
            records.append({**c,'especie':g['name'],'cientifico':g['scientific'],'foto':rel,'ids':changed,'modificaciones':'Redimensionado proporcional, lienzo blanco 800x800 y conversión WebP calidad 85'})
            print('Integrado:',g['name'],'IDs:',','.join(changed))
        except Exception as e: print('SIN INTEGRAR:',g['name'],str(e),file=sys.stderr)
        finally:temp.unlink(missing_ok=True)
    if updated:
        temporary=inv.with_suffix(inv.suffix+'.tmp')
        temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        temporary.replace(inv)
    report=out/('integracion-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
    report.write_text(json.dumps({'backup':str(backup),'productos_actualizados':updated,'fuentes':records},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Actualizados:',updated,'| Respaldo:',backup,'| Reporte:',report)


def cmd_serve(a):
    """Servidor exclusivamente local para guardar aprobaciones.csv con consentimiento."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse
    root = Path(a.root).resolve()
    out = root / 'reportes' / 'busqueda_fotografias'
    page = out / 'revision.html'
    candidates_path = out / 'candidatos.json'
    if not page.is_file() or not candidates_path.is_file():
        raise FileNotFoundError('Primero ejecutá buscar para generar revision.html y candidatos.json')
    groups = json.loads(candidates_path.read_text(encoding='utf-8'))
    known = {c['candidate_id'] for g in groups for c in g.get('candidates', [])}

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, mime='application/json; charset=utf-8'):
            data = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if urlparse(self.path).path in ('/', '/revision.html'):
                self.send(200, page.read_text(encoding='utf-8'), 'text/html; charset=utf-8')
            else:
                self.send(404, json.dumps({'error': 'No encontrado'}))

        def do_POST(self):
            if urlparse(self.path).path != '/guardar-aprobaciones':
                self.send(404, json.dumps({'error': 'No encontrado'})); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2_000_000:
                    raise ValueError('Tamaño de solicitud no permitido')
                origin = self.headers.get('Origin', '')
                if origin and origin != f'http://127.0.0.1:{a.port}':
                    raise ValueError('Origen no autorizado')
                body = json.loads(self.rfile.read(length))
                rows = body.get('filas')
                if not isinstance(rows, list):
                    raise ValueError('Formato de decisiones incorrecto')
                seen = set()
                checked = []
                for row in rows:
                    if not isinstance(row, list) or len(row) != 3:
                        raise ValueError('Fila inválida')
                    cid, decision, note = row
                    if not isinstance(cid, str) or cid not in known or cid in seen:
                        raise ValueError('Identificador desconocido o duplicado')
                    if decision not in ('SI', 'NO', 'PENDIENTE') or not isinstance(note, str) or len(note) > 1000:
                        raise ValueError('Decisión o nota inválida')
                    seen.add(cid)
                    checked.append((cid, decision, note))
                if seen != known:
                    raise ValueError('Faltan candidatos: recargá la galería antes de guardar')
                # Una sola aprobación por especie/variedad.
                groups_by_cid = {c['candidate_id']:group_key(g) for g in groups for c in g.get('candidates', [])}
                approved_groups = set()
                for cid, decision, _ in checked:
                    if decision == 'SI':
                        key = groups_by_cid[cid]
                        if key in approved_groups:
                            raise ValueError('Hay dos fotografías aprobadas para una misma variedad')
                        approved_groups.add(key)
                out.mkdir(parents=True, exist_ok=True)
                target = out / 'aprobaciones.csv'
                if target.exists():
                    backup = out / ('aprobaciones.backup-' + dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.csv')
                    shutil.copy2(target, backup)
                temp = out / 'aprobaciones.csv.tmp'
                with temp.open('w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(('candidate_id', 'aprobar', 'nota'))
                    writer.writerows(checked)
                temp.replace(target)
                self.send(200, json.dumps({'total': len(checked)}))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self.send(400, json.dumps({'error': str(exc)}, ensure_ascii=False))
            except Exception as exc:
                self.send(500, json.dumps({'error': str(exc)}, ensure_ascii=False))

    address = f'http://127.0.0.1:{a.port}/revision.html'
    print('Galería local:', address, flush=True)
    print('Guardado directo en:', out / 'aprobaciones.csv', flush=True)
    print('Presioná Ctrl+C para cerrar el servidor.', flush=True)
    with ThreadingHTTPServer(('127.0.0.1', a.port), Handler) as server:
        try: server.serve_forever()
        except KeyboardInterrupt: pass

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='V9: guardado directo local y búsqueda más precisa y galería visual con decisiones y exportación CSV; conservar imágenes existentes y buscar solo faltantes. Buscar imágenes con revisión manual, sin asignación automática dudosa')
    parser.add_argument('action',choices=['buscar','aplicar','servir'])
    parser.add_argument('--port',type=int,default=8765,help='Puerto local de la galería')
    parser.add_argument('--root',default='.',help='Raíz del repositorio')
    parser.add_argument('--inventory',default='Inventario/inventario.json',help='Ruta relativa del inventario')
    parser.add_argument('--limit',type=int,default=25,help='Grupos por búsqueda')
    parser.add_argument('--candidates',type=int,default=5,help='Candidatos por grupo')
    parser.add_argument('--refresh',action='store_true',help='Repetir grupos ya investigados (con precaución)')
    parser.add_argument('--delay',type=float,default=5.0,help='Pausa entre consultas')
    parser.add_argument('--confirm',action='store_true',help='Permite escribir inventario y descargar aprobadas')
    args=parser.parse_args()
    try:
        if args.action=='buscar':cmd_search(args)
        elif args.action=='servir':cmd_serve(args)
        else:cmd_apply(args)
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr);sys.exit(1)
