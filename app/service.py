from core.db import transaction
from core.validate import text,integer,date,choice
from core.security import Problem
from .models import find

def category(db,b,id=None):
    name=text(b.get('name'),'Kategori',100)
    with transaction(db):
        if id:
            find(db,'categories',id)
            db.execute('UPDATE categories SET name=? WHERE id=?',(name,id))
        else:
            db.execute('INSERT INTO categories(name) VALUES(?)',(name,))

def regulation(db,b,id=None):
    number=text(b.get('number'),'Nomor contoh',50)
    year=integer(b.get('year'),'Tahun',1900,2200)
    title=text(b.get('title'),'Judul contoh',200)
    if not any(word in title.upper() for word in ('CONTOH','DEMONSTRASI')):
        raise Problem('Judul harus memuat Contoh atau Demonstrasi agar tidak disalahartikan sebagai peraturan asli.')
    category_id=integer(b.get('category_id'),'Kategori',1)
    issued=date(b.get('issued_on'))
    status=choice(b.get('status'),('Berlaku','Dicabut'),'Status')
    status_note=text(b.get('status_note',''),'Penjelasan status',600,status=='Dicabut')
    note=text(b.get('note',''),'Catatan internal',1500,False)
    if int(issued[:4])!=year:
        raise Problem('Tahun harus sesuai tanggal dokumen contoh.')
    find(db,'categories',category_id)
    with transaction(db):
        if id:
            old=find(db,'regulations',id)
            if old['archived']:
                raise Problem('Pulihkan arsip sebelum mengedit.',409)
            if db.execute('SELECT id FROM links WHERE source_id=? OR target_id=?',(id,id)).fetchone() and (old['issued_on']!=issued or old['number']!=number or old['year']!=year):
                raise Problem('Nomor, tahun dan tanggal dokumen yang memiliki hubungan dipertahankan.',409)
            if status=='Berlaku' and db.execute("SELECT id FROM links WHERE target_id=? AND kind='Mencabut'",(id,)).fetchone():
                raise Problem('Dokumen telah memiliki hubungan pencabutan.',409)
            db.execute('UPDATE regulations SET number=?,year=?,title=?,category_id=?,issued_on=?,status=?,status_note=?,note=? WHERE id=?',(number,year,title,category_id,issued,status,status_note,note,id))
        else:
            db.execute('INSERT INTO regulations(number,year,title,category_id,issued_on,status,status_note,note) VALUES(?,?,?,?,?,?,?,?)',(number,year,title,category_id,issued,status,status_note,note))

def publish(db,id,value):
    value=integer(value,'Publikasi',0,1)
    item=find(db,'regulations',id)
    if item['archived'] or value and not db.execute('SELECT id FROM documents WHERE regulation_id=?',(id,)).fetchone():
        raise Problem('Dokumen aktif harus memiliki PDF contoh sebelum dipublikasikan.',409)
    with transaction(db):
        db.execute('UPDATE regulations SET published=? WHERE id=?',(value,id))

def archive(db,id,restore=False):
    find(db,'regulations',id)
    with transaction(db):
        db.execute('UPDATE regulations SET archived=?,published=0 WHERE id=?',(0 if restore else 1,id))

def link(db,b,actor):
    source,target=integer(b.get('source_id'),'Dokumen baru',1),integer(b.get('target_id'),'Dokumen terdahulu',1)
    kind=choice(b.get('kind'),('Mengubah','Mencabut'),'Hubungan')
    note=text(b.get('note'),'Catatan hubungan demonstrasi',1000)
    with transaction(db):
        a,z=find(db,'regulations',source),find(db,'regulations',target)
        if source==target or a['archived'] or z['archived'] or a['issued_on']<z['issued_on']:
            raise Problem('Hubungan harus antar dokumen aktif, dari tanggal yang sama atau lebih baru ke terdahulu.')
        if db.execute('WITH RECURSIVE walk(id) AS (SELECT target_id FROM links WHERE source_id=? UNION SELECT l.target_id FROM links l JOIN walk w ON l.source_id=w.id) SELECT id FROM walk WHERE id=?',(target,source)).fetchone():
            raise Problem('Hubungan berulang atau siklus tidak diperbolehkan.',409)
        if kind=='Mencabut' and a['status']!='Berlaku':
            raise Problem('Dokumen pencabut harus berstatus Berlaku.',409)
        db.execute('INSERT INTO links(source_id,target_id,kind,note,actor_id) VALUES(?,?,?,?,?)',(source,target,kind,note,actor))
        if kind=='Mencabut':
            db.execute("UPDATE regulations SET status='Dicabut',status_note=? WHERE id=?",('Dicabut oleh dokumen contoh '+a['number']+'/'+str(a['year']),target))
