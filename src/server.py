"""HTTP JSON e autenticação central; regras de cadastros persistentes."""
from datetime import datetime
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
from urllib.parse import urlsplit
from uuid import uuid4

from .storage import ROOT


class APIError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


class Application:
    def __init__(self, store):
        self.store = store
        self.config = store.config
        fixed = os.environ.get("RESERVA_AGORA")
        self.fixed_now = datetime.strptime(fixed, "%Y-%m-%dT%H:%M") if fixed else None

    def now(self):
        return self.fixed_now or datetime.now().replace(second=0, microsecond=0)

    def dispatch(self, method, path, body):
        if method == "GET" and path == "/api/saude":
            return 200, {"ok": True, "versao": (ROOT / "VERSION").read_text().strip()}
        if method == "GET" and path == "/api/saloes":
            return 200, {"saloes": self.config["saloes"]}
        parts = path.strip("/").split("/")
        if len(parts) not in (2, 3) or parts[0] != "api" or parts[1] not in ("mesas", "turnos", "faq"):
            raise APIError(404, "rota_inexistente")
        kind = parts[1]
        identifier = parts[2] if len(parts) == 3 else None
        with self.store.transaction() as db:
            items = self.store.items(db, kind)
            existing = next((item for item in items if item["id"] == identifier), None)
            if identifier is not None and existing is None:
                raise APIError(404, "nao_encontrado")
            if method == "GET" and identifier is None:
                if kind == "turnos":
                    items = [item for item in items if item["ativo"]]
                return 200, {kind: items}
            if method == "DELETE" and identifier is not None:
                if kind == "faq":
                    db.execute("DELETE FROM cadastros WHERE tipo=? AND id=?", (kind, identifier))
                    return 204, None
                flag = "ativa" if kind == "mesas" else "ativo"
                existing[flag] = False
                self.store.update(db, kind, existing)
                return 200, {flag: False}
            if (method == "POST" and identifier is None) or (method == "PUT" and identifier is not None and kind != "faq"):
                fields = {"mesas": ("id", "salao", "min", "max"),
                          "turnos": ("id", "nome", "dias", "inicio", "fim"),
                          "faq": ("perguntas", "resposta")}[kind]
                if method == "POST" and any(key not in body for key in fields):
                    raise APIError(422, "campos_obrigatorios")
                item = dict(existing or {})
                item.update({key: body[key] for key in fields if key != "id" and key in body})
                if existing is None:
                    item["id"] = body.get("id") if kind != "faq" else uuid4().hex
                    if not isinstance(item["id"], str) or not item["id"]:
                        raise APIError(422, "id_invalido")
                    if any(other["id"] == item["id"] for other in items):
                        raise APIError(409, "id_repetido")
                    if kind != "faq":
                        item["ativa" if kind == "mesas" else "ativo"] = True
                self.validate(kind, item, items)
                if existing is None:
                    self.store.insert(db, kind, item)
                else:
                    self.store.update(db, kind, item)
                return (201 if existing is None else 200), item
        raise APIError(404, "rota_inexistente")

    def validate(self, kind, item, items):
        if kind == "mesas":
            if item["salao"] not in [s["id"] for s in self.config["saloes"]]:
                raise APIError(404, "salao_inexistente")
            if any(type(item[key]) is not int for key in ("min", "max")) or not 1 <= item["min"] <= item["max"]:
                raise APIError(422, "capacidade_invalida")
        if kind == "turnos":
            days = item["dias"]
            if not isinstance(days, list) or not days or any(day not in ("seg", "ter", "qua", "qui", "sex", "sab", "dom") for day in days):
                raise APIError(422, "dias_invalidos")
            for key in ("inicio", "fim"):
                if not isinstance(item[key], str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", item[key]):
                    raise APIError(422, "horario_invalido")
            if item["inicio"] >= item["fim"]:
                raise APIError(422, "intervalo_invalido")
            if item["ativo"] and any(other["id"] != item["id"] and other["ativo"] and
                    set(days).intersection(other["dias"]) and item["inicio"] < other["fim"] and
                    item["fim"] > other["inicio"] for other in items):
                raise APIError(422, "turnos_sobrepostos")
        if kind == "faq":
            if not isinstance(item["perguntas"], list) or not item["perguntas"] or not all(isinstance(q, str) and q.strip() for q in item["perguntas"]) or not isinstance(item["resposta"], str) or not item["resposta"].strip():
                raise APIError(422, "faq_invalido")


PUBLIC = {("GET", "/"), ("GET", "/equipe"), ("GET", "/api/saude"),
          ("GET", "/api/saloes"), ("GET", "/api/turnos"),
          ("GET", "/api/horarios"), ("POST", "/api/mensagens")}


def make_server(app, host, port):
    class Handler(BaseHTTPRequestHandler):
        def handle_request(self):
            path = urlsplit(self.path).path
            try:
                if path.startswith("/api/") and (self.command, path) not in PUBLIC:
                    expected = app.config.get("token", "")
                    supplied = self.headers.get("X-Token", "")
                    if not expected or not hmac.compare_digest(supplied.encode(), expected.encode()):
                        raise APIError(401, "nao_autorizado")
                body = {}
                if self.command in ("POST", "PUT"):
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                        if not 0 <= length <= 1024 * 1024:
                            raise ValueError()
                        body = json.loads(self.rfile.read(length))
                        if not isinstance(body, dict):
                            raise ValueError()
                    except (ValueError, UnicodeError):
                        raise APIError(422, "json_invalido")
                status, result = app.dispatch(self.command, path, body)
            except APIError as error:
                status, result = error.status, {"erro": error.message}
            payload = b"" if status == 204 else json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            if status != 204:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = do_POST = do_PUT = do_DELETE = handle_request

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer((host, port), Handler)
