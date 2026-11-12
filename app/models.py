from core.validate import require_row
TABLES=('categories','regulations','documents','links')

def find(db, kind, id):
    return require_row(db,kind,id,TABLES)

def rows(db,sql,args=()):
    return [dict(r) for r in db.execute(sql,args)]

def state(db,f,public=False):
    sql='''SELECT r.*,c.name category,(SELECT id FROM documents d WHERE d.regulation_id=r.id ORDER BY id DESC LIMIT 1) document_id FROM regulations r JOIN categories c ON c.id=r.category_id WHERE r.archived=?'''
    records=rows(db,sql,(0 if public or f.get('archived')!='1' else 1,))
    q=str(f.get('q','')).lower().strip()[:120]
    records=[r for r in records if (not public or r['published'] and r['document_id']) and (not q or q in (r['number']+' '+r['title']).lower()) and (not f.get('year') or str(r['year'])==str(f['year'])) and (not f.get('category_id') or str(r['category_id'])==str(f['category_id'])) and (not f.get('status') or r['status']==f['status'])]
    visible=rows(db,'SELECT id FROM regulations WHERE published=1 AND archived=0 AND EXISTS(SELECT id FROM documents d WHERE d.regulation_id=regulations.id)') if public else rows(db,'SELECT id FROM regulations')
    ids={r['id'] for r in visible}
    links=rows(db,'SELECT l.*,s.title source,t.title target FROM links l JOIN regulations s ON s.id=l.source_id JOIN regulations t ON t.id=l.target_id ORDER BY l.id DESC')
    links=[l for l in links if l['source_id'] in ids and l['target_id'] in ids]
    categories=rows(db,'SELECT * FROM categories ORDER BY name')
    if public:
        keys=('id','number','year','title','category_id','category','issued_on','status','status_note','document_id')
        records=[{k:r[k] for k in keys} for r in records]
        links=[{k:l[k] for k in ('id','source_id','target_id','source','target','kind')} for l in links]
        categories=rows(db,'SELECT DISTINCT c.* FROM categories c JOIN regulations r ON r.category_id=c.id WHERE r.published=1 AND r.archived=0 AND EXISTS(SELECT id FROM documents d WHERE d.regulation_id=r.id) ORDER BY c.name')
    return {'regulations':records,'categories':categories,'links':links,'summary':{'count':len(records),'valid':sum(r['status']=='Berlaku' for r in records),'revoked':sum(r['status']=='Dicabut' for r in records)},'allRegulations':[] if public else rows(db,'SELECT id,title name FROM regulations WHERE archived=0 ORDER BY year DESC,number')}

def document(db,id,authenticated):
    d=find(db,'documents',id)
    r=find(db,'regulations',d['regulation_id'])
    latest=db.execute('SELECT MAX(id) FROM documents WHERE regulation_id=?',(r['id'],)).fetchone()[0]
    if not authenticated and (not r['published'] or r['archived'] or latest!=d['id']):
        from core.security import Problem
        raise Problem('Dokumen tidak tersedia.',404)
    return d
