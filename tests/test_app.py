import io
import secrets
import pytest
from pypdf import PdfReader,PdfWriter
from pypdf.generic import DictionaryObject,NameObject,TextStringObject
from app import create_app
from app.example import sample_pdf
from core.db import connect
from core.security import add_user

@pytest.fixture
def env(tmp_path):
    app=create_app({'TESTING':True,'INSTANCE_DIR':str(tmp_path)})
    db=connect(tmp_path)
    password=secrets.token_hex(20)
    for name,role in [('admin','Admin'),('staff','Petugas')]:
        add_user(db,name,'Penguji '+role,role,password)
    db.close()
    clients={}
    for name in ['admin','staff']:
        c=app.test_client()
        r=c.post('/api/login',json={'username':name,'password':password})
        clients[name]=(c,{'X-CSRF-Token':r.json['csrf']})
    c,h=clients['admin']
    assert c.post('/api/categories',json={'name':'Kategori Contoh'},headers=h).status_code==200
    assert c.post('/api/regulations',json=regulation(),headers=h).status_code==200
    return app,clients,tmp_path

def regulation(**extra):
    return {'number':'CONTOH-01','year':2026,'title':'Dokumen Contoh Demonstrasi','category_id':1,'issued_on':'2026-11-01','status':'Berlaku','status_note':'','note':'Catatan internal khusus uji',**extra}

def upload(c,h,id=1,content=None,name='contoh.pdf',mime='application/pdf',ack='1'):
    return c.post(f'/api/regulations/{id}/pdf',data={'file':(io.BytesIO(sample_pdf() if content is None else content),name,mime),'demo_ack':ack},headers=h,content_type='multipart/form-data')

def publish(c,h,id=1,value=1):
    return c.post(f'/api/regulations/{id}/publish',json={'published':value},headers=h)

def test_crud_and_archive_restore(env):
    _,clients,_=env
    c,h=clients['admin']
    assert c.put('/api/categories/1',json={'name':'Kategori Diubah'},headers=h).status_code==200
    assert c.put('/api/regulations/1',json=regulation(title='Contoh Diubah'),headers=h).status_code==200
    assert c.delete('/api/categories/1',json={},headers=h).status_code==409
    assert publish(c,h).status_code==409
    assert upload(c,h).status_code==200
    assert publish(c,h).status_code==200
    assert c.delete('/api/regulations/1',json={},headers=h).status_code==200
    assert c.get('/api/public').json['regulations']==[]
    assert len(c.get('/api/state?archived=1').json['regulations'])==1
    assert c.post('/api/regulations/1/restore',json={},headers=h).status_code==200
    assert c.get('/api/state').json['regulations'][0]['published']==0
    c.post('/api/categories',json={'name':'Tidak dipakai'},headers=h)
    assert c.delete('/api/categories/2',json={},headers=h).status_code==200

def test_public_projection_download_visibility_and_versions(env):
    app,clients,_=env
    c,h=clients['admin']
    anonymous=app.test_client()
    assert upload(c,h).status_code==200
    assert anonymous.get('/api/documents/1').status_code==404
    assert publish(c,h).status_code==200
    data=anonymous.get('/api/public').json
    assert len(data['regulations'])==1
    assert 'Catatan internal khusus uji' not in str(data)
    assert 'note' not in data['regulations'][0]
    r=anonymous.get('/api/documents/1')
    assert r.status_code==200 and r.mimetype=='application/pdf'
    assert 'attachment' in r.headers['Content-Disposition']
    assert r.data==sample_pdf()
    assert upload(c,h).status_code==200
    assert anonymous.get('/api/documents/1').status_code==404
    assert anonymous.get('/api/documents/2').status_code==404
    assert publish(c,h).status_code==200
    assert anonymous.get('/api/documents/2').status_code==200
    assert c.get('/api/documents/1').status_code==200
    publish(c,h,value=0)
    assert anonymous.get('/api/documents/2').status_code==404
    assert anonymous.get('/api/public').json['regulations']==[]

def test_pdf_validation_format_size_encryption_active_content(env):
    _,clients,folder=env
    c,h=clients['admin']
    assert upload(c,h,name='bad.exe').status_code==400
    assert upload(c,h,mime='text/plain').status_code==400
    assert upload(c,h,content=b'%PDF-1.4\ninvalid\n%%EOF').status_code==400
    assert upload(c,h,content=b'%PDF-'+b'x'*(5*1024*1024)+b'%%EOF').status_code==413
    assert upload(c,h,ack='0').status_code==400
    writer=PdfWriter()
    writer.append(PdfReader(io.BytesIO(sample_pdf())))
    writer.encrypt('test-password-only')
    output=io.BytesIO()
    writer.write(output)
    assert upload(c,h,content=output.getvalue()).status_code==400
    writer=PdfWriter()
    writer.append(PdfReader(io.BytesIO(sample_pdf())))
    writer._root_object[NameObject('/OpenAction')]=DictionaryObject({NameObject('/S'):NameObject('/JavaScript'),NameObject('/JS'):TextStringObject('app.alert(1)')})
    output=io.BytesIO()
    writer.write(output)
    assert upload(c,h,content=output.getvalue()).status_code==400
    writer=PdfWriter()
    writer.add_blank_page(width=100,height=100)
    output=io.BytesIO()
    writer.write(output)
    assert upload(c,h,content=output.getvalue()).status_code==400
    assert not (folder/'uploads').exists()

def test_file_cleanup_on_database_failure(env):
    _,clients,folder=env
    c,h=clients['admin']
    db=connect(folder)
    db.execute("CREATE TRIGGER force_failure BEFORE INSERT ON documents BEGIN SELECT RAISE(ABORT,'test failure'); END")
    db.commit()
    db.close()
    assert upload(c,h).status_code==409
    assert list((folder/'uploads').glob('*.pdf'))==[]
    db=connect(folder)
    assert db.execute('SELECT COUNT(*) FROM documents').fetchone()[0]==0
    db.close()

def test_amendment_repeal_cycle_chronology_and_status_transaction(env):
    _,clients,_=env
    c,h=clients['admin']
    c.post('/api/regulations',json=regulation(number='CONTOH-02',issued_on='2026-11-10'),headers=h)
    link={'source_id':2,'target_id':1,'kind':'Mencabut','note':'Hubungan pencabutan demonstrasi'}
    assert c.post('/api/links',json=link,headers=h).status_code==200
    rows=c.get('/api/state').json['regulations']
    assert next(r for r in rows if r['id']==1)['status']=='Dicabut'
    assert c.put('/api/regulations/1',json=regulation(),headers=h).status_code==409
    assert c.post('/api/links',json=link,headers=h).status_code==409
    assert c.post('/api/links',json={**link,'source_id':1,'target_id':1},headers=h).status_code==400
    assert c.post('/api/links',json={**link,'source_id':1,'target_id':2,'kind':'Mengubah'},headers=h).status_code==400
    c.post('/api/regulations',json=regulation(number='CONTOH-03',issued_on='2026-11-10'),headers=h)
    assert c.post('/api/links',json={**link,'source_id':3,'target_id':2,'kind':'Mengubah'},headers=h).status_code==200
    assert c.post('/api/links',json={**link,'source_id':2,'target_id':3,'kind':'Mengubah'},headers=h).status_code==409
    assert c.put('/api/regulations/2',json=regulation(number='BARU',issued_on='2026-11-10'),headers=h).status_code==409

def test_search_filters_and_private_relationships(env):
    app,clients,_=env
    c,h=clients['admin']
    upload(c,h)
    publish(c,h)
    c.post('/api/regulations',json=regulation(number='CONTOH-02',title='Contoh Rahasia Uji',issued_on='2026-11-10'),headers=h)
    c.post('/api/links',json={'source_id':2,'target_id':1,'kind':'Mengubah','note':'Internal hubungan'},headers=h)
    anonymous=app.test_client()
    state=anonymous.get('/api/public?q=CONTOH-01&year=2026&category_id=1&status=Berlaku').json
    assert len(state['regulations'])==1 and state['links']==[]
    assert 'Rahasia Uji' not in str(state)
    assert anonymous.get('/api/public?q=tidakada').json['regulations']==[]
    assert len(c.get('/api/state?q=rahasia').json['regulations'])==1
    r=anonymous.get('/contoh.pdf')
    assert r.status_code==200
    assert 'DEMONSTRASI' in PdfReader(io.BytesIO(r.data)).pages[0].extract_text()

def test_metadata_validation(env):
    _,clients,_=env
    c,h=clients['admin']
    for values in [regulation(year=2025),regulation(title='Dokumen tanpa penanda'),regulation(year=2201),regulation(issued_on='2026-02-30'),regulation(status='Dicabut'),regulation(category_id=999)]:
        assert c.post('/api/regulations',json=values,headers=h).status_code in (400,404)
    assert c.post('/api/regulations',json=regulation(),headers=h).status_code==409

def test_access_csrf_origin_isolation_and_role_refresh(env):
    app,clients,folder=env
    c,h=clients['staff']
    assert app.test_client().get('/api/state').status_code==401
    assert c.post('/api/regulations',json=regulation(number='X'),headers=h).status_code==403
    assert upload(c,h).status_code==403
    admin,ah=clients['admin']
    assert upload(admin,{}).status_code==403
    assert upload(admin,{**ah,'Origin':'https://example.invalid'}).status_code==403
    wrong=app.test_client()
    wrong.set_cookie('app_session',admin.get_cookie('produk_hukum_desa_session').value)
    assert wrong.get('/api/state').status_code==401
    db=connect(folder)
    db.execute("UPDATE users SET role='Petugas' WHERE username='admin'")
    db.commit()
    db.close()
    assert admin.post('/api/categories',json={'name':'Role lama'},headers=ah).status_code==403
    c.post('/api/logout',json={},headers=h)
    assert c.get('/api/state').status_code==401

def test_restart_files_and_relational_integrity(env):
    _,clients,folder=env
    c,h=clients['admin']
    assert upload(c,h).status_code==200
    assert publish(c,h).status_code==200
    app=create_app({'TESTING':True,'INSTANCE_DIR':str(folder)})
    assert app.test_client().get('/api/documents/1').data==sample_pdf()
    db=connect(folder)
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    db.close()
