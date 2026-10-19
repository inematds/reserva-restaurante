"""Clientes e alocação transacional, independentes do canal de atendimento."""
from datetime import datetime, timedelta
import re
import unicodedata
from uuid import uuid4


class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


def phone(value):
    if not isinstance(value, str) or re.search(r'[^0-9+()\s-]', value):
        raise APIError(400, 'telefone_invalido')
    digits = re.sub(r'\D', '', value)
    if len(digits) in (12, 13) and digits.startswith('55'):
        digits = digits[2:]
    if len(digits) not in (10, 11):
        raise APIError(400, 'telefone_invalido')
    return '+55' + digits


def required(body, *keys):
    if any(key not in body for key in keys):
        raise APIError(422, 'campos_obrigatorios')


def instant(value):
    try:
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', value):
            raise ValueError()
        return datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except ValueError:
        raise APIError(422, 'horario_invalido')


ACTIVE = {'reservada', 'confirmada', 'pendente', 'chegou', 'no_show'}


class Booking:
    def find(self, db, kind, identifier):
        item = next((i for i in self.store.items(db, kind) if str(i['id']) == str(identifier)), None)
        if item is None:
            raise APIError(404, 'nao_encontrado')
        return item

    def validate_client(self, item):
        item['telefone'] = phone(item['telefone'])
        birthday = item.get('aniversario')
        if birthday is not None:
            try:
                if not isinstance(birthday, str) or not re.fullmatch(r'\d{2}-\d{2}', birthday):
                    raise ValueError()
                datetime.strptime('2000-' + birthday, '%Y-%m-%d')
            except ValueError:
                raise APIError(400, 'aniversario_invalido')
        if item['origem'] not in ('salao', 'whatsapp', 'chat', 'telefone', 'site', 'indicacao', 'equipe', 'outro'):
            raise APIError(422, 'origem_invalida')

    def check_room(self, room):
        if room is not None and room not in [s['id'] for s in self.config['saloes']]:
            raise APIError(404, 'salao_inexistente')

    def grid(self, db, day, duration=0):
        try:
            date = datetime.strptime(day, '%Y-%m-%d')
        except (ValueError, TypeError):
            raise APIError(422, 'data_invalida')
        if day in self.config.get('feriados', []):
            return []
        weekday = ('seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom')[date.weekday()]
        result = []
        for shift in self.store.items(db, 'turnos'):
            if not shift['ativo'] or weekday not in shift['dias']:
                continue
            start, end = (instant(day + 'T' + shift[k]) for k in ('inicio', 'fim'))
            while start < end and start + timedelta(minutes=duration) <= end:
                result.append({'inicio': start.isoformat(timespec='minutes'), 'turno': shift['id']})
                start += timedelta(minutes=self.config['passo_min'])
        return sorted(result, key=lambda h: h['inicio'])

    def allocate(self, db, start, people, room=None, table=None, exclude=None):
        self.check_room(room)
        tables = self.store.items(db, 'mesas')
        combinations = self.config.get('combinacoes', [])
        chosen = None
        if table is not None:
            chosen = next((t for t in tables + combinations if t['id'] == table), None)
            if chosen is None:
                raise APIError(404, 'mesa_inexistente')
        if type(people) is not int or people < 1:
            raise APIError(422, 'pessoas_invalidas')
        begin = instant(start)
        duration = next(r['min'] for r in self.config['duracao'] if r['ate'] is None or people <= r['ate'])
        end = (begin + timedelta(minutes=duration)).isoformat(timespec='minutes')
        candidates = self.grid(db, start[:10], duration)
        shift = next((h['turno'] for h in candidates if h['inicio'] == start), None)
        if shift is None or begin < self.now() + timedelta(hours=self.config['antecedencia_min_horas']) or begin.date() > self.now().date() + timedelta(days=self.config['janela_dias']):
            raise APIError(422, 'horario_invalido')
        active = [r for r in self.store.items(db, 'reservas') if r['status'] in ACTIVE and r['id'] != exclude]
        occupied = {t for r in active if start < r['fim'] and end > r['inicio'] for t in r['mesas']}
        blocks = [b for b in self.store.items(db, 'bloqueios') if start < b['fim'] and end > b['inicio']]
        if any(not b.get('mesa') and not b.get('salao') for b in blocks):
            raise APIError(422, 'restaurante_bloqueado')
        def members(candidate):
            ids = candidate.get('mesas', [candidate['id']])
            return [t for t in tables if t['id'] in ids]
        def suitable(candidate):
            group = members(candidate)
            return (candidate['min'] <= people <= candidate['max'] and
                    len(group) == len(candidate.get('mesas', [candidate['id']])) and bool(group) and
                    all(t['ativa'] and (room is None or t['salao'] == room) for t in group))
        def free(candidate):
            return all(t['id'] not in occupied and not any(b.get('mesa') == t['id'] or
                       (not b.get('mesa') and b.get('salao') == t['salao']) for b in blocks) for t in members(candidate))
        if chosen is not None and not suitable(chosen):
            raise APIError(422, 'mesa_invalida')
        choices = [chosen] if chosen is not None else sorted(tables, key=lambda t: t['max']) + sorted(combinations, key=lambda t: t['max'])
        selected = next((c for c in choices if suitable(c) and free(c)), None)
        if selected is None:
            raise APIError(409, 'sem_mesa')
        limit = self.config.get('limite_pessoas_por_horario')
        if limit is not None and sum(r['pessoas'] for r in active if r['inicio'] == start) + people > limit:
            raise APIError(409, 'limite_cozinha')
        return {'inicio': start, 'fim': end, 'pessoas': people, 'turno': shift,
                'salao': members(selected)[0]['salao'], 'mesas': selected.get('mesas', [selected['id']]),
                'status': 'pendente' if people >= self.config['grupo_grande_a_partir'] else 'reservada'}

    def slots(self, db, query):
        self.check_room(query.get('salao'))
        try:
            people = int(query.get('pessoas', ''))
            if people < 1:
                raise ValueError()
        except (ValueError, TypeError):
            raise APIError(422, 'pessoas_invalidas')
        result = []
        for h in self.grid(db, query.get('data')):
            try:
                self.allocate(db, h['inicio'], people, query.get('salao'))
                result.append(h)
            except APIError as error:
                if error.status not in (409, 422):
                    raise
        return result

    def reservation_list(self, db, query):
        clients = {c['id']: c for c in self.store.items(db, 'clientes')}
        result = []
        for r in self.store.items(db, 'reservas'):
            day = r['inicio'][:10]
            if query.get('data', day) != day or day < query.get('de', day) or day > query.get('ate', day):
                continue
            if any(query.get(k, r[k]) != r[k] for k in ('turno', 'salao', 'cliente_id')):
                continue
            client = clients[r['cliente_id']]
            result.append({**r, 'nome': client['nome'], 'telefone': client['telefone']})
        return sorted(result, key=lambda r: (r['inicio'], r['id']))

    def booking_dispatch(self, method, path, body, query):
        parts = path.strip('/').split('/')
        kind = parts[1]
        identifier = parts[2] if len(parts) > 2 else None
        action = parts[3] if len(parts) > 3 else None
        with self.store.transaction() as db:
            existing = self.find(db, kind, identifier) if identifier is not None else None
            if kind == 'horarios' and method == 'GET':
                return 200, {'horarios': self.slots(db, query)}
            if kind == 'clientes':
                if method == 'DELETE' and existing and action is None:
                    self.anonymize(db, existing)
                    return 204, None
                if method == 'GET' and identifier is None:
                    term = normalized(query.get('busca', ''))
                    digits = re.sub(r'\D', '', term)
                    return 200, {'clientes': [c for c in self.store.items(db, kind) if term in normalized(c['nome']) or (digits and digits in (c['telefone'] or ''))]}
                if method == 'GET' and action == 'dados':
                    return 200, {'cliente': existing, 'reservas': self.reservation_list(db, {'cliente_id': existing['id']}), 'mensagens': [{k: m[k] for k in ('direcao', 'texto', 'quando')} for m in self.store.items(db, 'mensagens') if m.get('cliente_id') == existing['id'] or (existing['telefone'] is not None and m['telefone'] == existing['telefone'])]}
                if method in ('POST', 'PUT') and action is None:
                    if method == 'POST':
                        required(body, 'nome', 'telefone')
                    item = dict(existing or {'id': uuid4().hex, 'consentimento_marketing': False, 'nao_contatar': False,
                                'aniversario': None, 'origem': 'equipe', 'ultima_visita': None, 'visitas': 0})
                    item.update({k: body[k] for k in ('nome', 'telefone', 'consentimento_marketing', 'nao_contatar', 'aniversario', 'origem') if k in body})
                    self.validate_client(item)
                    duplicate = next((c for c in self.store.items(db, kind) if c['telefone'] == item['telefone'] and c['id'] != item['id']), None)
                    if duplicate:
                        if method == 'POST':
                            return 200, {'id': duplicate['id']}
                        raise APIError(409, 'telefone_repetido')
                    if existing:
                        self.store.update(db, kind, item)
                    else:
                        self.store.insert(db, kind, item)
                    return (200, item) if existing else (201, {'id': item['id']})
            if kind == 'reservas':
                if method == 'GET' and identifier is None:
                    return 200, {'reservas': self.reservation_list(db, query)}
                if method == 'POST' and identifier is None:
                    required(body, 'cliente_id', 'inicio', 'pessoas')
                    client = self.find(db, 'clientes', body['cliente_id'])
                    item = self.allocate(db, body['inicio'], body['pessoas'], body.get('salao'), body.get('mesa'))
                    item.update(id=uuid4().hex, cliente_id=client['id'], observacao=body.get('observacao', ''))
                    self.store.insert(db, kind, item)
                    return 201, item
                if method == 'POST' and existing:
                    if action in ('cancelar', 'remarcar'):
                        if existing['status'] not in ('reservada', 'confirmada', 'pendente'):
                            raise APIError(409, 'status')
                        if action == 'cancelar':
                            self.cancel(db, existing)
                        else:
                            if not any(k in body for k in ('inicio', 'pessoas')):
                                raise APIError(422, 'campos_obrigatorios')
                            allocation = self.allocate(db, body.get('inicio', existing['inicio']), body.get('pessoas', existing['pessoas']), exclude=existing['id'])
                            existing.update(allocation)
                            existing.pop('confirmacao_enviada', None)
                    elif action in ('aprovar', 'recusar'):
                        if existing['status'] != 'pendente':
                            raise APIError(409, 'status')
                        existing['status'] = 'reservada' if action == 'aprovar' else 'recusada'
                        client = self.find(db, 'clientes', existing['cliente_id'])
                        self.output(db, client, 'aprovacao' if action == 'aprovar' else 'recusa',
                                    ('Confirmada: ' + self.describe(existing)) if action == 'aprovar' else 'Não foi possível aprovar sua reserva.', existing['id'])
                    elif action == 'chegada':
                        if existing['status'] not in ('reservada', 'confirmada'):
                            raise APIError(409, 'status')
                        if type(body.get('compareceu')) is not bool:
                            raise APIError(422, 'compareceu_invalido')
                        existing['status'] = 'chegou' if body['compareceu'] else 'no_show'
                    else:
                        raise APIError(404, 'rota_inexistente')
                    self.store.update(db, kind, existing)
                    if existing['status'] == 'chegou':
                        client = self.find(db, 'clientes', existing['cliente_id'])
                        visits = [r for r in self.store.items(db, kind) if r['cliente_id'] == client['id'] and r['status'] == 'chegou']
                        client.update(visitas=len(visits), ultima_visita=max(r['inicio'][:10] for r in visits))
                        self.store.update(db, 'clientes', client)
                    return 200, existing if action == 'remarcar' else {'status': existing['status']}
            if kind == 'ocupacao' and method == 'GET':
                self.check_room(query.get('salao'))
                tables = {t['id'] for t in self.store.items(db, 'mesas') if t['ativa'] and (not query.get('salao') or t['salao'] == query['salao'])}
                result = []
                for h in self.grid(db, query.get('data')):
                    reservations = [r for r in self.store.items(db, 'reservas') if r['status'] in ACTIVE and r['inicio'] <= h['inicio'] < r['fim'] and tables.intersection(r['mesas'])]
                    occupied = {t for r in reservations for t in r['mesas']} & tables
                    result.append({**h, 'mesas_total': len(tables), 'mesas_ocupadas': len(occupied), 'pessoas': sum(r['pessoas'] for r in reservations)})
                return 200, {'data': query.get('data'), 'horarios': result}
        raise APIError(404, 'rota_inexistente')
