# vercel_wsgi.py — minimal WSGI adapter for Vercel Python runtime
# Sumber: disederhanakan dari adapter open-source. Cukup untuk Django/Flask standar.

import base64
import urllib.parse
from io import BytesIO

def _build_environ(event):
    method = event.get("httpMethod") or event.get("method") or "GET"
    path = urllib.parse.unquote(event.get("path", "/"))
    raw_qs = event.get("rawQueryString") or event.get("queryString") or ""
    headers = event.get("headers") or {}
    body = event.get("body") or ""
    is_b64 = event.get("isBase64Encoded", False)

    if isinstance(headers, list):
        # kadang dikirim sebagai list of {key,value}
        headers = {h.get("key") or h.get("name"): h.get("value") for h in headers if h}

    if is_b64 and isinstance(body, str):
        body_bytes = base64.b64decode(body)
    elif isinstance(body, str):
        body_bytes = body.encode("utf-8")
    else:
        body_bytes = body or b""

    environ = {
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "https",
        "wsgi.input": BytesIO(body_bytes),
        "wsgi.errors": BytesIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "REQUEST_METHOD": method,
        "SCRIPT_NAME": "",
        "PATH_INFO": path,
        "QUERY_STRING": raw_qs,
        "SERVER_NAME": headers.get("host", "localhost"),
        "SERVER_PORT": headers.get("x-forwarded-port", "443"),
        "SERVER_PROTOCOL": "HTTP/1.1",
        "CONTENT_LENGTH": str(len(body_bytes)),
    }

    # Map headers -> environ
    for k, v in headers.items():
        key = "HTTP_" + k.upper().replace("-", "_")
        if key in ("HTTP_CONTENT_TYPE", "HTTP_CONTENT_LENGTH"):
            key = key[5:]
        environ[key] = v

    return environ, body_bytes

def handle(event, context, app):
    environ, _ = _build_environ(event)

    status_headers = {"status": "500 Internal Server Error", "headers": []}
    body_chunks = []

    def start_response(status, response_headers, exc_info=None):
        status_headers["status"] = status
        status_headers["headers"] = response_headers
        # WSGI callable must return a write() callable; but we just ignore chunked writes
        return body_chunks.append

    result = app(environ, start_response)
    try:
        for data in result:
            if data:
                body_chunks.append(data)
    finally:
        if hasattr(result, "close"):
            result.close()

    body = b"".join(body_chunks)
    status_code = int(status_headers["status"].split(" ", 1)[0])

    # Headers: convert list of tuples -> dict (merge duplicates simply by last wins)
    resp_headers = {}
    for k, v in status_headers["headers"]:
        resp_headers[k] = v

    # Pilih encoding aman (latin-1 untuk arbitrary bytes; Vercel akan kirim apa adanya)
    # Kalau kamu butuh base64, ubah sesuai kebutuhan.
    try:
        body_text = body.decode("utf-8")
        is_b64 = False
        resp_body = body_text
    except UnicodeDecodeError:
        is_b64 = True
        resp_body = base64.b64encode(body).decode("ascii")

    return {
        "statusCode": status_code,
        "headers": resp_headers,
        "body": resp_body,
        "isBase64Encoded": is_b64,
    }
