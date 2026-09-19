import os
import logging
from flask import Flask, send_from_directory, request, Response, jsonify
import urllib.request
import urllib.parse

# Отключаем логи (анонимность)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/healthz')
def health():
    return jsonify(status='ok')

@app.route('/api/proxy')
def proxy():
    """Прокси для запросов к Audius — скрывает источник от посетителя."""
    target = request.args.get('url')
    if not target:
        return jsonify(error='missing url'), 400
    # Белый список хостов (безопасность)
    allowed = ['discoveryprovider.audius.co', 'audius.co', 'api.audius.co']
    host = urllib.parse.urlparse(target).hostname or ''
    if not any(host == h or host.endswith('.' + h) for h in allowed):
        return jsonify(error='host not allowed'), 403
    try:
        req = urllib.request.Request(target, headers={'User-Agent': 'Mozilla/5.0 LimonMusic'})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
            ctype = r.headers.get('Content-Type', 'application/octet-stream')
            return Response(data, content_type=ctype)
    except Exception as e:
        return jsonify(error=str(e)), 502

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
