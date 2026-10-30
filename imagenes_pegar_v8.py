#!/usr/bin/env python3
"""Galería local: pegar imágenes del portapapeles y asignarlas por especie/categoría."""
import base64, datetime as dt, io, json, re, shutil, threading, unicodedata, argparse, sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from PIL import Image, ImageOps, UnidentifiedImageError

FIELDS=('especie','nombre','nombre_comun','nombreComun','producto','variedad','cientifico','nombre_cientifico')
GENERIC={'logo.jpeg','logo.jpg','logo.png','logo.webp','logo-generico.webp','imagen-generica.webp','sin-foto.webp'}

def inventory(path):
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if isinstance(data,list):return data,data
    if isinstance(data,dict):
        for k in ('productos','inventario','items','catalogo','data'):
            if isinstance(data.get(k),list):return data,data[k]
    raise ValueError('Formato de inventario no reconocido')

def name(r):return next((str(r[k]).strip() for k in FIELDS if r.get(k)), 'Sin nombre')
def slug(v):
    v=unicodedata.normalize('NFKD',str(v))
    v=''.join(c for c in v if not unicodedata.combining(c))
    return re.sub('-+','-',re.sub('[^a-z0-9]+','-',v.lower())).strip('-') or 'sin-nombre'
def is_real(r,root):
    if r.get('foto_referencia') is True:return False
    v=r.get('foto')
    if not isinstance(v,str) or not v.strip():return False
    if v.startswith(('http:','https:','//','data:')):return True
    p=v.replace('\\','/').split('?')[0].lstrip('/')
    if p.split('/')[-1].lower() in GENERIC:return False
    return any((b/p).is_file() for b in (root,root/'imagenes',root/'Inventario'))
def groups(rows,root):
    d={}
    for r in rows:
        if not isinstance(r,dict):continue
        key=(name(r).casefold(),str(r.get('cientifico') or r.get('nombre_cientifico') or '').casefold())
        g=d.setdefault(key,{'name':name(r),'rows':[],'ids':[]})
        g['rows'].append(r);g['ids'].append(str(r.get('id','')))
    result=[]
    for g in d.values():
        pending=[r for r in g['rows'] if not is_real(r,root) and r.get('foto_referencia') is not True]
        if not pending:continue
        cats={slug(r.get('categoria') or r.get('categoría') or r.get('category') or 'sin-categoria') for r in g['rows']}
        result.append({'name':g['name'],'ids':[str(r.get('id')) for r in pending],
                       'category':next(iter(cats)) if len(cats)==1 else 'categoria-ambigua',
                       'count':len(pending)})
    return sorted(result,key=lambda x:x['name'].casefold())
def output_path(root,species,rows):
    cats={slug(r.get('categoria') or r.get('categoría') or r.get('category') or 'sin-categoria') for r in rows}
    if len(cats)!=1:raise ValueError('Categorías diferentes para la misma especie')
    base=root/'imagenes';cat=next(iter(cats))
    existing=next((d for d in base.iterdir() if d.is_dir() and slug(d.name)==cat),None) if base.is_dir() else None
    folder=existing or base/cat
    folder.mkdir(parents=True,exist_ok=True)
    stem=slug(species);target=folder/(stem+'.webp')
    if target.exists():
        for i in range(2,10000):
            t=folder/(f'{stem}-referencia-{i}.webp')
            if not t.exists():return t
        raise ValueError('Demasiados archivos con ese nombre')
    return target

PAGE=r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pegar fotos por especie · Árboles Exóticos Occidente</title>
<style>*{box-sizing:border-box}body{margin:0;background:#edf4ee;color:#153e28;font:16px system-ui,Arial}main{max-width:1280px;margin:auto;padding:24px}header{background:#fff;border-radius:18px;padding:25px;margin-bottom:20px;box-shadow:0 3px 15px #0001}h1{margin:0 0 12px}input[type=search]{width:100%;padding:13px;border:1px solid #b2c9b8;border-radius:10px;font:inherit}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:18px}.card{background:white;padding:19px;border-radius:16px;box-shadow:0 3px 14px #0001;min-width:0}h2{font-size:21px;margin:0 0 7px}.muted{color:#607569;font-size:13px}.paste{margin:15px 0;min-height:190px;border:2px dashed #83b79a;background:#f6faf6;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;padding:12px;cursor:pointer;outline-offset:3px;text-align:center}.paste:focus,.paste:hover{border-color:#08723c;background:#eaf6ed}.paste img{max-width:100%;max-height:230px;object-fit:contain}.paste .hint{font-size:13px;color:#486c57}.actions{display:flex;gap:8px;flex-wrap:wrap}button{border:0;background:#086739;color:white;padding:11px 13px;border-radius:9px;cursor:pointer;font:inherit}button.alt{background:#e1f0e6;color:#115c36}button:disabled{opacity:.5}.status{font-size:13px;min-height:20px;overflow-wrap:anywhere}.notice{background:#fff1ce;border-radius:10px;padding:13px;margin-top:15px}.empty{padding:30px;background:white;border-radius:12px}@media(max-width:600px){main{padding:10px}.grid{grid-template-columns:1fr}header,.card{padding:15px}}</style></head><body><main><header><h1>🌳 Pegar imágenes por especie</h1><p>Solo especies sin fotografía asignada. Abrí Google Imágenes, copiá la foto y pegala directamente en la tarjeta de la especie con <b>Ctrl + V</b>.</p><input type="search" id="search" placeholder="Buscar especie o categoría…"><p id="counter" class="muted"></p><div class="notice">⚠️ Se guardan como <b>referencias visuales provisionales</b>, no como fotografías botánicas verificadas. Copiar una imagen de Google no otorga derechos de publicación: usá únicamente imágenes propias o con permiso/licencia compatible.</div></header><div id="grid" class="grid"></div></main><script>
let items=[],images=new Map();const $=id=>document.getElementById(id);
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function load(){const r=await fetch('/api/groups',{cache:'no-store'});if(!r.ok)throw Error('Error al leer inventario');items=await r.json();render()}
function render(){let q=$('search').value.toLocaleLowerCase();let list=items.filter(x=>(x.name+' '+x.category).toLocaleLowerCase().includes(q));$('counter').textContent=`${list.length} de ${items.length} especies pendientes`;
$('grid').innerHTML=list.map((g,i)=>{let k=g.ids.join(',');let saved=images.get(k);return `<article class="card" data-ids="${esc(k)}"><h2>${esc(g.name)}</h2><p class="muted">Categoría: ${esc(g.category)} · IDs: ${esc(g.ids.join(', '))}</p><div class="paste" tabindex="0" role="button" aria-label="Pegar imagen para ${esc(g.name)}"><div class="placeholder" ${saved?'hidden':''}>📋 <b>Hacé clic aquí y presioná Ctrl + V</b><span class="hint">Copiá primero la fotografía desde Google Imágenes</span></div><img ${saved?'src="'+saved+'"':'hidden'} alt="Vista previa de la fotografía copiada"></div><div class="actions"><button class="save" ${saved?'':'disabled'}>💾 Guardar y asignar</button><button class="alt clear">🗑 Limpiar</button><button class="alt google">🔎 Buscar en Google</button></div><p class="status" role="status"></p></article>`}).join('')||'<div class="empty">No quedan especies pendientes para esta búsqueda.</div>';
for(let card of document.querySelectorAll('.card')){let g=items.find(x=>x.ids.join(',')===card.dataset.ids);let paste=card.querySelector('.paste');paste.onclick=()=>paste.focus();card.querySelector('.google').onclick=()=>window.open('https://www.google.com/search?tbm=isch&q='+encodeURIComponent(g.name+' fruta árbol'),'_blank','noopener');card.querySelector('.clear').onclick=()=>{images.delete(card.dataset.ids);render()};card.querySelector('.save').onclick=()=>save(card,g);paste.onpaste=e=>onPaste(e,card);paste.onkeydown=e=>{if(e.key==='Enter')paste.focus()}}}
async function onPaste(e,card){const f=Array.from(e.clipboardData?.items||[]).find(x=>x.type.startsWith('image/'))?.getAsFile();if(!f){card.querySelector('.status').textContent='❌ El portapapeles no contiene una imagen. En Google, usá “Copiar imagen”, no “Copiar dirección de imagen”.';return}e.preventDefault();if(f.size>15_000_000){card.querySelector('.status').textContent='❌ Imagen mayor a 15 MB';return}let reader=new FileReader();reader.onload=()=>{images.set(card.dataset.ids,reader.result);let img=card.querySelector('img');img.src=reader.result;img.hidden=false;card.querySelector('.placeholder').hidden=true;card.querySelector('.save').disabled=false;card.querySelector('.status').textContent='✅ Imagen copiada. Revisá la vista previa y presioná Guardar y asignar.'};reader.readAsDataURL(f)}
async function save(card,g){let raw=images.get(card.dataset.ids);if(!raw)return;let btn=card.querySelector('.save'),status=card.querySelector('.status');if(!confirm('¿Guardar imagen provisional para '+g.name+' y sus '+g.ids.length+' presentaciones pendientes?'))return;btn.disabled=true;status.textContent='Convirtiendo y guardando WebP…';try{let r=await fetch('/api/assign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids:g.ids,image:raw.split(',')[1],source:'Portapapeles: referencia visual manual'})});let data=await r.json();if(!r.ok)throw Error(data.error||'Error');images.delete(card.dataset.ids);await load();alert('✅ '+data.message+'\nRuta: '+data.path)}catch(err){status.textContent='❌ '+err.message;btn.disabled=false}}
$('search').addEventListener('input',render);load().catch(e=>$('counter').textContent='❌ '+e.message);
</script></body></html>'''

def serve(root,inv,port):
    lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def reply(self,code,payload,ctype='application/json'):
            content=json.dumps(payload,ensure_ascii=False).encode('utf-8') if ctype=='application/json' else payload.encode('utf-8')
            self.send_response(code);self.send_header('Content-Type',ctype+'; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
        def do_GET(self):
            path=urlparse(self.path).path
            if path in ('/','/index.html'):return self.reply(200,PAGE,'text/html')
            if path=='/api/groups':
                try:return self.reply(200,groups(inventory(inv)[1],root))
                except Exception as exc:return self.reply(500,{'error':str(exc)})
            return self.reply(404,{'error':'No encontrado'})
        def do_POST(self):
            if self.path!='/api/assign':return self.reply(404,{'error':'No encontrado'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=22_000_000:raise ValueError('Solicitud demasiado grande')
                data=json.loads(self.rfile.read(n));ids={str(x) for x in data['ids']}
                if not ids or len(ids)>100:raise ValueError('IDs inválidos')
                blob=base64.b64decode(data['image'],validate=True)
                if len(blob)>15_000_000:raise ValueError('Imagen mayor a 15 MB')
                with Image.open(io.BytesIO(blob)) as original:
                    if original.width*original.height>40_000_000:raise ValueError('Imagen demasiado grande')
                    im=ImageOps.exif_transpose(original).convert('RGBA');im.thumbnail((900,900),Image.Resampling.LANCZOS)
                    bg=Image.new('RGB',(900,900),'white');bg.paste(im,((900-im.width)//2,(900-im.height)//2),im)
                    out=io.BytesIO();bg.save(out,'WEBP',quality=85,method=6)
                with lock:
                    obj,rows=inventory(inv)
                    selected=[r for r in rows if isinstance(r,dict) and str(r.get('id')) in ids]
                    if {str(r.get('id')) for r in selected}!=ids:raise ValueError('IDs desconocidos')
                    if len({(name(r).casefold(),str(r.get('cientifico') or r.get('nombre_cientifico') or '').casefold()) for r in selected})!=1:raise ValueError('IDs de diferentes especies')
                    if any(is_real(r,root) or r.get('foto_referencia') is True for r in selected):raise ValueError('La especie ya tiene una imagen asignada. Recargá la página.')
                    target=output_path(root,name(selected[0]),selected)
                    target.write_bytes(out.getvalue());rel=target.relative_to(root).as_posix()
                    for r in selected:
                        r['foto_anterior_referencia']=r.get('foto');r['foto']=rel;r['foto_referencia']=True
                        r['foto_referencia_aviso']='Imagen ilustrativa provisional; no confirma especie ni variedad.'
                        r['foto_referencia_origen']='Imagen pegada manualmente del portapapeles; licencia y autor pendientes de revisión'
                    backup=inv.with_name(inv.stem+'.backup-pegado-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
                    shutil.copy2(inv,backup)
                    tmp=inv.with_suffix('.json.tmp')
                    try:
                        tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(inv)
                    except Exception:
                        target.unlink(missing_ok=True);raise
                return self.reply(200,{'message':f'{len(selected)} presentaciones actualizadas. Respaldo: {backup.name}','path':rel})
            except (ValueError,KeyError,UnidentifiedImageError) as exc:return self.reply(400,{'error':str(exc)})
            except Exception as exc:return self.reply(500,{'error':str(exc)})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Galería de pegado: http://127.0.0.1:{port}/')
    print('Ctrl+C para detener el servidor.')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

def main():
    p=argparse.ArgumentParser(description='V8: pegar imagen copiada en cada especie pendiente y asignar WebP por categoría')
    p.add_argument('--root',default='.')
    p.add_argument('--inventory',default='Inventario/inventario.json')
    p.add_argument('--port',type=int,default=8766)
    a=p.parse_args();root=Path(a.root).resolve();inv=(root/a.inventory).resolve()
    if not inv.is_file():raise FileNotFoundError(inv)
    serve(root,inv,a.port)
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
