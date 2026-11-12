import hashlib
import io
import uuid
from pathlib import Path
from pypdf import PdfReader
from pypdf.generic import IndirectObject, DictionaryObject, ArrayObject
from core.db import transaction
from core.security import Problem
from .models import find
MAX_SIZE=5*1024*1024
FORBIDDEN={'/OpenAction','/AA','/JS','/JavaScript','/AcroForm','/EmbeddedFiles','/Launch','/RichMediaContent','/XFA','/AF','/A'}

def validate_pdf(upload):
    if not upload or not upload.filename or not upload.filename.lower().endswith('.pdf') or upload.mimetype!='application/pdf':
        raise Problem('Unggah berkas PDF dengan tipe application/pdf.')
    content=upload.stream.read(MAX_SIZE+1)
    if len(content)>MAX_SIZE:
        raise Problem('Ukuran PDF maksimal 5 MB.',413)
    if not content.startswith(b'%PDF-') or not content.rstrip().endswith(b'%%EOF'):
        raise Problem('Berkas bukan PDF yang utuh.')
    try:
        reader=PdfReader(io.BytesIO(content),strict=True)
        if reader.is_encrypted or not 1<=len(reader.pages)<=100:
            raise ValueError('encrypted or pages')
        visited=set()
        count=0
        def scan(obj,depth=0):
            nonlocal count
            count+=1
            if depth>60 or count>15000:
                raise ValueError('complexity')
            if isinstance(obj,IndirectObject):
                key=(obj.idnum,obj.generation)
                if key in visited:
                    return
                visited.add(key)
                scan(obj.get_object(),depth+1)
            elif isinstance(obj,DictionaryObject):
                if FORBIDDEN.intersection(obj.keys()):
                    raise ValueError('active content')
                for value in obj.values():
                    scan(value,depth+1)
            elif isinstance(obj,ArrayObject):
                for value in obj:
                    scan(value,depth+1)
        scan(reader.trailer)
        text=' '.join((p.extract_text() or '') for p in reader.pages).upper()
        if 'DEMONSTRASI' not in text or 'TIDAK RESMI' not in text:
            raise Problem('PDF harus memuat teks DEMONSTRASI dan TIDAK RESMI. Gunakan berkas contoh yang disediakan.')
    except Problem:
        raise
    except Exception as error:
        raise Problem('PDF tidak valid, terenkripsi, terlalu kompleks, atau mengandung aksi/formulir/lampiran yang tidak didukung.') from error
    return content

def save(db,folder,id,upload,actor):
    item=find(db,'regulations',id)
    if item['archived']:
        raise Problem('Pulihkan arsip sebelum mengunggah.',409)
    content=validate_pdf(upload)
    directory=(Path(folder)/'uploads').resolve()
    directory.mkdir(parents=True,exist_ok=True)
    token=uuid.uuid4().hex+'.pdf'
    target=directory/token
    try:
        with target.open('xb') as output:
            output.write(content)
        with transaction(db):
            db.execute('INSERT INTO documents(regulation_id,token,sha256,size,actor_id) VALUES(?,?,?,?,?)',(id,token,hashlib.sha256(content).hexdigest(),len(content),actor))
            db.execute('UPDATE regulations SET published=0 WHERE id=?',(id,))
    except Exception:
        if target.parent==directory and target.exists():
            target.unlink()
        raise

def path_for(folder,token):
    directory=(Path(folder)/'uploads').resolve()
    target=(directory/token).resolve()
    if target.parent!=directory or not target.is_file():
        raise Problem('Berkas tidak tersedia.',404)
    return target
