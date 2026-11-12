def sample_pdf():
    lines = ['DOKUMEN DEMONSTRASI - TIDAK RESMI', 'Contoh berkas untuk pengujian portofolio.', 'Tidak mempunyai kekuatan hukum.', 'Tidak diterbitkan oleh instansi pemerintah.', 'Digunakan untuk menguji arsip, pencarian, dan unduhan.']
    commands = ['BT /F1 18 Tf 50 770 Td']
    for i, line in enumerate(lines):
        if i:
            commands.append('0 -30 Td /F1 12 Tf')
        commands.append('('+line+') Tj')
    commands.append('ET')
    stream = '\n'.join(commands).encode('ascii')
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Count 1 /Kids [3 0 R] >>', b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>', b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    result = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    start = len(result)
    result.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        result.extend(f'{offset:010d} 00000 n \n'.encode())
    result.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
    return bytes(result)
