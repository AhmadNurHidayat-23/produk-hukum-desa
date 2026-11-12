import io
from flask import Blueprint,g,request,jsonify,current_app,render_template,send_file
from core.auth import require,data
from core.security import Problem
from core.db import transaction
from . import models,service,uploads
from .example import sample_pdf
api=Blueprint('api',__name__)

@api.get('/kelola')
def manage():
    return render_template('manage.html')

@api.get('/contoh.pdf')
def example():
    return send_file(io.BytesIO(sample_pdf()),mimetype='application/pdf',as_attachment=True,download_name='dokumen-demonstrasi-tidak-resmi.pdf')

@api.get('/api/public')
def public():
    return jsonify(models.state(g.db,request.args,True))

@api.get('/api/state')
@require()
def state():
    return jsonify(models.state(g.db,request.args))

@api.get('/api/documents/<int:id>')
def download(id):
    item=models.document(g.db,id,bool(g.user))
    return send_file(uploads.path_for(current_app.config['INSTANCE_DIR'],item['token']),mimetype='application/pdf',as_attachment=True,download_name=f'dokumen-contoh-{id}.pdf')

@api.route('/api/<kind>',methods=['POST'])
@api.route('/api/<kind>/<int:id>',methods=['PUT','DELETE'])
@require(('Admin',))
def save(kind,id=None):
    if kind not in ('categories','regulations','links'):
        raise Problem('Alamat tidak tersedia.',404)
    if kind=='links':
        if request.method!='POST':
            raise Problem('Hubungan dipertahankan sebagai riwayat.',405)
        service.link(g.db,data(),g.user['id'])
    elif request.method=='DELETE':
        if kind=='regulations':
            service.archive(g.db,id)
        else:
            models.find(g.db,kind,id)
            with transaction(g.db):
                g.db.execute('DELETE FROM categories WHERE id=?',(id,))
    else:
        (service.regulation if kind=='regulations' else service.category)(g.db,data(),id)
    return jsonify(message='Arsip contoh disimpan.')

@api.post('/api/regulations/<int:id>/<action>')
@require(('Admin',))
def action(id,action):
    if action=='pdf':
        if request.form.get('demo_ack')!='1':
            raise Problem('Konfirmasi bahwa berkas merupakan dokumen demonstrasi.')
        uploads.save(g.db,current_app.config['INSTANCE_DIR'],id,request.files.get('file'),g.user['id'])
    elif action=='publish':
        service.publish(g.db,id,data().get('published'))
    elif action=='restore':
        service.archive(g.db,id,True)
    else:
        raise Problem('Alamat tidak tersedia.',404)
    return jsonify(message='Dokumen contoh diperbarui.')
