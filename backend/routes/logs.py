import io, os, zipfile

from flask import Blueprint, abort, send_file
from path_provider import PathProvider


logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/download-logs', methods=['GET'])
def download_logs():
    zip_buffer = zip_logs()
    filename = f"autobot_logs.zip"
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )

def zip_logs():
    logs_dir = PathProvider.get_logs_dir()
    if not os.path.isdir(logs_dir):
        abort(404, error="Logs directory not found!")
    
    # Crear buffer en memoria
    buffer = io.BytesIO()
    # Crear ZIP en el buffer
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for filename in os.listdir(logs_dir):
            if filename.lower().endswith('.log'):
                filepath = os.path.join(logs_dir, filename)
                z.write(filepath, arcname=filename)
    buffer.seek(0)
    return buffer