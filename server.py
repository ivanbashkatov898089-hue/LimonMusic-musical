import os
import logging
import urllib.request
import urllib.parse
from flask import Flask, send_from_directory, request, Response, jsonify

# Отключаем логи Werkzeug — анонимность
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__, static_folder='.', static_url_path='')

# Белый список разрешённых хостов (безопасность)
ALLOWED_HOSTS = [
    'discoveryprovider.audius.co',
    'audius.co',
    'api.audius.co',
    'archive.org',
    'www.archive.org',
    'ia601234.us.archive.org',  # узлы archive.org отдают файлы с разных поддоменов
]

@app.route('/')
def index():
    # Проверяем, пришел ли запрос на старый домен
    if request.host == 'limonmusic.jo3.org':
        # Если да — перенаправляем на рабочий поддомен
        return redirect('https://server.limonmusic.jo3.org', code=301)
    return send_from_directory('.', 'index.html')

# Публичные IP archive.org (для download-домена)
def is_allowed_host(host):
    if not host:
        return False
    if host in ALLOWED_HOSTS:
        return True
    # Разрешаем поддомены archive.org (*.archive.org)
    if host.endswith('.archive.org'):
        return True
    # Разрешаем поддомены audius.co
    if host.endswith('.audius.co'):
        return True
    return False

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/healthz')
def health():
    return jsonify(status='ok')

@app.route('/api/proxy')
def proxy():
    """Универсальный прокси для Audius и Internet Archive."""
    target = request.args.get('url')
    if not target:
        return jsonify(error='missing url'), 400

    try:
        parsed = urllib.parse.urlparse(target)
    except Exception:
        return jsonify(error='invalid url'), 400

    if parsed.scheme not in ('http', 'https'):
        return jsonify(error='invalid scheme'), 400

    if not is_allowed_host(parsed.hostname):
        return jsonify(error='host not allowed'), 403

    try:
        req = urllib.request.Request(
            target,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; LimonMusic/3.0)',
                'Accept': '*/*',
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            ctype = r.headers.get('Content-Type', 'application/octet-stream')
            resp = Response(data, content_type=ctype)
            # CORS на всякий случай (фронт всё равно same-origin)
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.headers['Cache-Control'] = 'public, max-age=3600'
            return resp
    except urllib.error.HTTPError as e:
        return jsonify(error=f'upstream {e.code}'), 502
    except urllib.error.URLError as e:
        return jsonify(error=f'upstream unreachable: {e.reason}'), 502
    except Exception as e:
        return jsonify(error=str(e)), 502


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
