"""Transportes opcionais, configurados exclusivamente pelo ambiente."""
import hmac
import json
import os
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import quote
from .booking import APIError, phone, instant, ACTIVE


class Integrations:
    @staticmethod
    def post_json(url, body, headers=None):
        request = Request(url, data=json.dumps(body).encode(),
                          headers={'Content-Type': 'application/json', **(headers or {})}, method='POST')
        try:
            with urlopen(request, timeout=3) as response:
                raw = response.read()
                try:
                    result = json.loads(raw) if raw else {}
                except ValueError:
                    result = {}
                return True, result
        except (URLError, OSError, ValueError):
            return False, {}

    def whatsapp(self, tel, text):
        base = os.environ.get('EVOLUTION_URL')
        if not base:
            return 'simulado'
        ok, _ = self.post_json(base.rstrip('/') + '/message/sendText/' + quote(os.environ.get('EVOLUTION_INSTANCIA', ''), safe=''),
                              {'number': tel.lstrip('+'), 'text': text},
                              {'apikey': os.environ.get('EVOLUTION_API_KEY', '')})
        return 'enviado' if ok else 'pendente'

    def telegram(self, text, reply=None):
        values = [os.environ.get(k) for k in ('TELEGRAM_API_URL', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_SEGREDO')]
        if not all(values):
            return None
        base, token, chat, _ = values
        body = {'chat_id': chat, 'text': text}
        if reply is not None:
            body['reply_to_message_id'] = reply
        ok, result = self.post_json(base.rstrip('/') + '/bot' + quote(token, safe='') + '/sendMessage', body)
        return result.get('result', {}).get('message_id') if ok else None

    def notify_reservation(self, db, reservation, conversation=False):
        pending = reservation['status'] == 'pendente'
        if not pending and not conversation:
            return
        client = self.find(db, 'clientes', reservation['cliente_id'])
        prefix = f"Grupo grande #{reservation['id']}: " if pending else 'Nova reserva: '
        self.telegram(prefix + instant(reservation['inicio']).strftime('%d/%m %H:%M') +
                      f" {client['nome']} — {reservation['pessoas']} pessoas")

    def relay_human(self, db, item, text, opening=False):
        prefix = f"#{item['id']} {item.get('nome') or item['telefone']}"
        message = (f"{prefix} {item['telefone']} — {item['motivo']}: {text}" if opening else f'{prefix}: {text}')
        mid = self.telegram(message, None if opening else item.get('message_id'))
        if mid is not None:
            item.setdefault('telegram_messages', []).append(mid)
            if opening:
                item['message_id'] = mid
            self.store.update(db, 'humano', item)

    def webhook_auth(self, path, headers):
        if path.startswith('/webhook/evolution/'):
            secret = os.environ.get('WEBHOOK_SEGREDO', '')
            if not secret or not hmac.compare_digest(path.encode(), ('/webhook/evolution/' + secret).encode()):
                raise APIError(404, 'rota_inexistente')
        if path == '/webhook/telegram':
            secret = os.environ.get('TELEGRAM_SEGREDO', '')
            if not secret or not hmac.compare_digest(headers.get('X-Telegram-Bot-Api-Secret-Token', '').encode(), secret.encode()):
                raise APIError(401, 'nao_autorizado')

    def evolution_webhook(self, body):
        with self.store.transaction() as db:
            data = body.get('data') or {}
            key = data.get('key') or {}
            jid = key.get('remoteJid', '')
            identifier = key.get('id')
            if body.get('event') != 'messages.upsert' or key.get('fromMe') or not jid.endswith('@s.whatsapp.net') or not identifier:
                return 200, {'ok': True}
            if any(m['id'] == identifier for m in self.store.items(db, 'evolution_recebidas')):
                return 200, {'ok': True}
            try:
                tel = phone(jid.split('@')[0])
            except APIError:
                return 200, {'ok': True}
            message = data.get('message') or {}
            text = message.get('conversation') or (message.get('extendedTextMessage') or {}).get('text')
            if isinstance(text, str) and text:
                replies = self.converse(db, tel, text, origin='whatsapp')
            else:
                replies = ['Por enquanto só consigo ler mensagens de texto.']
                self.history(db, tel, 'saida', replies[0])
            for reply in replies:
                self.whatsapp(tel, reply)
            self.store.insert(db, 'evolution_recebidas', {'id': identifier})
        return 200, {'ok': True}

    def telegram_webhook(self, body):
        message = body.get('message') or {}
        if str((message.get('chat') or {}).get('id')) != os.environ.get('TELEGRAM_CHAT_ID'):
            return 200, {'ok': True}
        text = message.get('text')
        if not isinstance(text, str) or not text.strip():
            return 200, {'ok': True}
        parts = text.split(maxsplit=2)
        command = parts[0].split('@')[0]
        try:
            if command in ('/responder', '/encerrar') and len(parts) >= 2:
                self.conversation_dispatch('POST', f'/api/atendimento-humano/{parts[1]}/{command[1:]}',
                                           {'texto': parts[2] if len(parts) > 2 else ''}, {})
            elif command in ('/aprovar', '/recusar') and len(parts) == 2:
                self.booking_dispatch('POST', f'/api/reservas/{parts[1]}/{command[1:]}', {}, {})
                self.telegram(f"#{parts[1]}: {command[1:]} concluído")
            elif command == '/fila':
                _, result = self.conversation_dispatch('GET', '/api/atendimento-humano', {}, {})
                self.telegram('\n'.join(f"#{h['id']} {h.get('nome') or h['telefone']}" for h in result['fila']) or 'Fila vazia.')
            elif command == '/reservas':
                day = parts[1] if len(parts) > 1 else self.now().date().isoformat()
                _, result = self.booking_dispatch('GET', '/api/reservas', {}, {'data': day})
                self.telegram('\n'.join(f"{r['inicio'][11:]} {r['nome']} — {r['pessoas']} pessoas — {'+'.join(r['mesas'])} ({r['status']})" for r in result['reservas'] if r['status'] in ACTIVE) or 'Sem reservas.')
            else:
                mid = (message.get('reply_to_message') or {}).get('message_id')
                with self.store.transaction() as db:
                    human = next((h for h in self.store.items(db, 'humano') if h['status'] == 'aberto' and mid is not None and mid in h.get('telegram_messages', [])), None)
                if human:
                    self.conversation_dispatch('POST', f"/api/atendimento-humano/{human['id']}/responder", {'texto': text}, {})
        except APIError as error:
            self.telegram('Não foi possível: ' + error.message)
        return 200, {'ok': True}
