"""Conversa e tarefas persistentes, usando o mesmo alocador das rotas da equipe."""
from datetime import datetime, timedelta
import re
from uuid import uuid4
from .booking import APIError, normalized, phone, required, instant


def words(text):
    return re.findall(r'\w+', normalized(text))


class Conversation:
    def bind_history(self, db, tel, client_id):
        # Claim only unowned messages: a recycled phone must not inherit another client.
        for message in self.store.items(db, 'mensagens'):
            if message['telefone'] == tel and not message.get('cliente_id'):
                message['cliente_id'] = client_id
                self.store.update(db, 'mensagens', message)

    def history(self, db, tel, direction, text):
        client = next((c for c in self.store.items(db, 'clientes') if c['telefone'] == tel), None)
        self.store.insert(db, 'mensagens', {'id': uuid4().hex, 'telefone': tel, 'cliente_id': client['id'] if client else None,
            'direcao': direction, 'texto': text, 'quando': self.now().isoformat(timespec='minutes')})

    def output(self, db, client, kind, text, reservation=None, **extra):
        item = dict(id=uuid4().hex, tipo=kind, telefone=client['telefone'], cliente_id=client['id'],
                    texto=text, reserva_id=reservation, status='simulado', quando=self.now().isoformat(timespec='minutes'), **extra)
        item['status'] = self.whatsapp(client['telefone'], text)
        self.store.insert(db, 'saida', item)
        self.history(db, client['telefone'], 'saida', text)
        return item

    def cancel(self, db, reservation):
        if reservation['status'] not in ('reservada', 'confirmada', 'pendente'):
            raise APIError(409, 'status')
        reservation['status'] = 'cancelada'
        self.store.update(db, 'reservas', reservation)
        for entry in self.store.items(db, 'espera'):
            if entry['status'] != 'pendente' or entry['data'] != reservation['inicio'][:10] or entry['turno'] != reservation['turno']:
                continue
            client = self.find(db, 'clientes', entry['cliente_id'])
            if client['nao_contatar'] or not client['telefone']:
                continue
            try:
                self.allocate(db, reservation['inicio'], entry['pessoas'])
            except APIError:
                continue
            entry.update(status='ofertada', inicio=reservation['inicio'])
            self.store.update(db, 'espera', entry)
            self.output(db, client, 'espera', f"Vaga às {entry['inicio'][11:]}. Responda 1 para reservar.", espera_id=entry['id'])
            break

    def new_wait(self, db, body):
        required(body, 'cliente_id', 'data', 'turno', 'pessoas')
        self.find(db, 'clientes', body['cliente_id'])
        if not self.find(db, 'turnos', body['turno'])['ativo']:
            raise APIError(404, 'turno_inativo')
        if type(body['pessoas']) is not int or body['pessoas'] < 1:
            raise APIError(422, 'pessoas_invalidas')
        try:
            datetime.strptime(body['data'], '%Y-%m-%d')
        except (ValueError, TypeError):
            raise APIError(422, 'data_invalida')
        item = {k: body[k] for k in ('cliente_id', 'data', 'turno', 'pessoas')}
        item.update(id=uuid4().hex, status='pendente')
        self.store.insert(db, 'espera', item)
        return item

    def conversation_dispatch(self, method, path, body, query):
        with self.store.transaction() as db:
            if path == '/api/mensagens' and method == 'POST':
                required(body, 'telefone', 'texto')
                if not isinstance(body['texto'], str):
                    raise APIError(422, 'texto_invalido')
                return 200, {'respostas': self.converse(db, phone(body['telefone']), body['texto'])}
            if path == '/api/saida' and method == 'GET':
                return 200, {'mensagens': self.store.items(db, 'saida')}
            if path == '/api/espera':
                if method == 'POST':
                    return 201, {'id': self.new_wait(db, body)['id']}
                if method == 'GET':
                    entries = []
                    for entry in self.store.items(db, 'espera'):
                        if entry['data'] == query.get('data', entry['data']):
                            client = self.find(db, 'clientes', entry['cliente_id'])
                            entries.append({**entry, 'nome': client['nome'], 'telefone': client['telefone']})
                    return 200, {'espera': entries}
            if path == '/api/tarefas/rodar' and method == 'POST':
                now = instant(body['agora']) if 'agora' in body else self.now()
                resent = 0
                for item in self.store.items(db, 'saida'):
                    if item['status'] != 'pendente' or not item['telefone'] or item.get('obsoleta'):
                        continue
                    client = next((c for c in self.store.items(db, 'clientes') if c['id'] == item['cliente_id']), None)
                    if item['tipo'] in ('confirmacao', 'espera', 'aniversario', 'reativacao', 'campanha') and (not client or client['nao_contatar']):
                        continue
                    item['status'] = self.whatsapp(item['telefone'], item['texto'])
                    self.store.update(db, 'saida', item)
                    resent += item['status'] == 'enviado'
                count = 0
                for r in self.store.items(db, 'reservas'):
                    c = self.find(db, 'clientes', r['cliente_id'])
                    if r['status'] == 'reservada' and not r.get('confirmacao_enviada') and not c['nao_contatar'] and c['telefone'] and now < instant(r['inicio']) <= now + timedelta(hours=self.config['confirmacao_horas']):
                        self.output(db, c, 'confirmacao', f"Confirme {self.describe(r)}: 1 confirmar / 2 cancelar.", r['id'])
                        r['confirmacao_enviada'] = True
                        self.store.update(db, 'reservas', r)
                        count += 1
                for c in self.store.items(db, 'clientes'):
                    if not c['consentimento_marketing'] or c['nao_contatar'] or not c['telefone']:
                        continue
                    if c.get('aniversario') == now.strftime('%m-%d') and c.get('aniversario_ano') != now.year:
                        self.output(db, c, 'aniversario', f"Feliz aniversário, {c['nome'].split()[0]}!")
                        c['aniversario_ano'] = now.year
                        count += 1
                    if c['ultima_visita'] and now.date() >= datetime.strptime(c['ultima_visita'], '%Y-%m-%d').date() + timedelta(days=self.config['reativacao_dias']) and c.get('reativacao_visita') != c['ultima_visita']:
                        self.output(db, c, 'reativacao', f"Venha nos visitar em {self.config['nome']}!")
                        c['reativacao_visita'] = c['ultima_visita']
                        count += 1
                    self.store.update(db, 'clientes', c)
                return 200, {'enviadas': count, 'reenviadas': resent}
            if path == '/api/campanhas' and method == 'POST':
                if not isinstance(body.get('texto'), str) or not body['texto'].strip():
                    raise APIError(422, 'texto_invalido')
                count = 0
                for c in self.store.items(db, 'clientes'):
                    if c['consentimento_marketing'] and not c['nao_contatar'] and c['telefone']:
                        self.output(db, c, 'campanha', body['texto'])
                        count += 1
                return 200, {'enviadas': count}
            if path == '/api/atendimento-humano' and method == 'GET':
                return 200, {'fila': [h for h in self.store.items(db, 'humano') if h['status'] == 'aberto']}
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[1] == 'atendimento-humano':
                h = self.find(db, 'humano', parts[2])
                if method == 'POST' and parts[3] == 'encerrar':
                    h['status'] = 'encerrado'
                    self.store.update(db, 'humano', h)
                    return 200, {'status': h['status']}
                if method == 'POST' and parts[3] == 'responder':
                    if not isinstance(body.get('texto'), str) or not body['texto'].strip():
                        raise APIError(422, 'texto_invalido')
                    c = next((c for c in self.store.items(db, 'clientes') if c['telefone'] == h['telefone']), {'id': None, 'telefone': h['telefone']})
                    self.output(db, c, 'humano', body['texto'])
                    return 200, {'ok': True}
        raise APIError(404, 'rota_inexistente')

    @staticmethod
    def describe(r):
        return f"{instant(r['inicio']).strftime('%d/%m %H:%M')} — {r['pessoas']} pessoas"

    def converse(self, db, tel, text, origin='chat'):
        self.history(db, tel, 'entrada', text)
        state = next((s for s in self.store.items(db, 'conversas') if s['id'] == tel), None)
        if state is None:
            state = {'id': tel, 'step': None, 'misses': 0, 'stop': False}
            self.store.insert(db, 'conversas', state)
        client = next((c for c in self.store.items(db, 'clientes') if c['telefone'] == tel), None)
        norm = ' '.join(words(text))
        def reply(message):
            self.store.update(db, 'conversas', state)
            if message is None:
                return []
            self.history(db, tel, 'saida', message)
            return [message]
        def human(reason):
            item = dict(id=uuid4().hex, telefone=tel, nome=client['nome'] if client else None,
                motivo=reason, status='aberto', ultima_mensagem=text)
            self.store.insert(db, 'humano', item)
            self.relay_human(db, item, text, opening=True)
            state.update(step=None, misses=0)
        if norm in ('parar', 'sair', 'pare'):
            state['stop'] = True
            if client:
                client['nao_contatar'] = True
                self.store.update(db, 'clientes', client)
            return reply('Você não vai mais receber mensagens automáticas.')
        opened = next((h for h in self.store.items(db, 'humano') if h['telefone'] == tel and h['status'] == 'aberto'), None)
        if opened:
            self.relay_human(db, opened, text)
            return reply(None)
        if any(t in norm for t in ('atendente', 'humano', 'falar com alguem')):
            human('pedido de atendente')
            return reply('Vou chamar um atendente.')
        if state['step']:
            state['misses'] = 0
            if norm == 'cancelar' or (state['step'] == 'cancel' and norm == '0'):
                state['step'] = None
                return reply('Fluxo cancelado.')
            step = state['step']
            if step == 'name':
                if not text.strip():
                    return reply('Qual seu nome?')
                client = dict(id=uuid4().hex, nome=text.strip(), telefone=tel, consentimento_marketing=False,
                              nao_contatar=state['stop'], aniversario=None, origem=origin, ultima_visita=None, visitas=0)
                self.store.insert(db, 'clientes', client)
                self.bind_history(db, tel, client['id'])
                state['step'] = 'people'
                return reply('Quantas pessoas?')
            if step == 'people':
                if not norm.isdecimal() or int(norm) < 1:
                    return reply('Quantas pessoas? Informe um número inteiro maior que zero.')
                state.update(step='day', pessoas=int(norm))
                return reply('Qual dia?')
            if step == 'day':
                try:
                    today = self.now().date()
                    if norm in ('hoje', 'amanha'):
                        day = today + timedelta(days=norm == 'amanha')
                    else:
                        value = text.strip()
                        if re.fullmatch(r'\d{2}/\d{2}', value):
                            day = datetime.strptime(value + '/' + str(today.year), '%d/%m/%Y').date()
                            if day < today:
                                day = day.replace(year=today.year + 1)
                        else:
                            day = datetime.strptime(value, '%d/%m/%Y').date()
                    date = day.isoformat()
                    if day < today or day > today + timedelta(days=self.config['janela_dias']) or not self.grid(db, date):
                        raise ValueError()
                except (ValueError, APIError):
                    return reply('Não é possível nesse dia. Qual dia deseja?')
                state['data'] = date
                state['slots'] = self.slots(db, {'data': date, 'pessoas': state['pessoas']})[:8]
                shifts = {h['turno'] for h in self.grid(db, date)}
                state['shifts'] = [s for s in self.store.items(db, 'turnos') if s['id'] in shifts]
                state['step'] = 'slot' if state['slots'] else 'wait'
            if state['step'] == 'slot':
                if step == 'slot' and norm.isdecimal() and 1 <= int(norm) <= len(state['slots']):
                    h = state['slots'][int(norm)-1]
                    try:
                        r = self.allocate(db, h['inicio'], state['pessoas'])
                    except APIError:
                        state['step'] = 'day'
                        return reply('Horário ocupado. Escolha outro dia.')
                    r.update(id=uuid4().hex, cliente_id=client['id'], observacao='')
                    self.store.insert(db, 'reservas', r)
                    self.notify_reservation(db, r, conversation=True)
                    state['step'] = None
                    return reply(('Aguardando aprovação da equipe: ' if r['status'] == 'pendente' else 'Reservado: ') + self.describe(r))
                shifts = {s['id']: s['nome'] for s in state['shifts']}
                return reply('\n'.join(f"{i}) {h['inicio'][11:]} ({shifts[h['turno']]})" for i, h in enumerate(state['slots'], 1)))
            if state['step'] == 'wait':
                if step == 'wait' and norm == '2':
                    state['step'] = None
                    return reply('Pedido cancelado.')
                if step != 'wait' or norm != '1':
                    return reply('Sem horário livre. Lista de espera? 1 sim / 2 não.')
                state['step'] = 'shift'
                if len(state['shifts']) == 1:
                    norm = '1'
                    step = 'shift'
            if state['step'] == 'shift':
                if step == 'shift' and norm.isdecimal() and 1 <= int(norm) <= len(state['shifts']):
                    self.new_wait(db, dict(cliente_id=client['id'], data=state['data'], pessoas=state['pessoas'], turno=state['shifts'][int(norm)-1]['id']))
                    state['step'] = None
                    return reply('Você entrou na lista de espera.')
                return reply('\n'.join(f"{i}) {s['nome']}" for i, s in enumerate(state['shifts'], 1)))
            if step == 'cancel':
                if norm.isdecimal() and 1 <= int(norm) <= len(state['reservations']):
                    r = self.find(db, 'reservas', state['reservations'][int(norm)-1])
                    if r['status'] not in ('reservada', 'confirmada', 'pendente'):
                        state['step'] = None
                        return reply('Reserva já não pode ser cancelada.')
                    self.cancel(db, r)
                    self.telegram('Cancelada: ' + self.describe(r))
                    state['step'] = None
                    return reply('Cancelada: ' + self.describe(r))
                return reply(state['options'])
        outputs = [m for m in self.store.items(db, 'saida') if m['telefone'] == tel]
        last = outputs[-1] if outputs else None
        if last and not last.get('respondida'):
            if last['tipo'] == 'confirmacao' and norm in ('1', 'sim', 'confirmo', '2', 'cancelar', 'nao'):
                r = self.find(db, 'reservas', last['reserva_id'])
                if r['status'] == 'reservada':
                    if norm in ('1', 'sim', 'confirmo'):
                        r['status'] = 'confirmada'
                        self.store.update(db, 'reservas', r)
                    else:
                        self.cancel(db, r)
                        self.telegram('Cancelada: ' + self.describe(r))
                    last['respondida'] = True
                    self.store.update(db, 'saida', last)
                    state['misses'] = 0
                    return reply(r['status'].capitalize() + ': ' + self.describe(r))
            if last['tipo'] == 'espera' and norm in ('1', 'sim'):
                entry = self.find(db, 'espera', last['espera_id'])
                last['respondida'] = True
                self.store.update(db, 'saida', last)
                try:
                    r = self.allocate(db, entry['inicio'], entry['pessoas'])
                except APIError:
                    return reply('Horário já ocupado.')
                r.update(id=uuid4().hex, cliente_id=entry['cliente_id'], observacao='')
                self.store.insert(db, 'reservas', r)
                self.notify_reservation(db, r, conversation=True)
                entry['status'] = 'atendida'
                self.store.update(db, 'espera', entry)
                state['misses'] = 0
                return reply('Reservado: ' + self.describe(r))
        if any(t in norm for t in ('minha reserva', 'minhas reservas', 'cancelar')):
            state['misses'] = 0
            reservations = [r for r in self.reservation_list(db, {'cliente_id': client['id']}) if r['status'] in ('reservada', 'confirmada', 'pendente') and instant(r['inicio']) > self.now()] if client else []
            if not reservations:
                return reply('Não encontrei reservas futuras.')
            if 'cancelar' in norm and len(reservations) == 1:
                self.cancel(db, reservations[0])
                self.telegram('Cancelada: ' + self.describe(reservations[0]))
                return reply('Cancelada: ' + self.describe(reservations[0]))
            options = '\n'.join(f'{i}) {self.describe(r)}' for i, r in enumerate(reservations, 1))
            if 'cancelar' in norm:
                state.update(step='cancel', reservations=[r['id'] for r in reservations], options=options)
            return reply(options)
        if 'reserva' in norm:
            state.update(step='people' if client else 'name', misses=0)
            return reply('Quantas pessoas?' if client else 'Qual seu nome?')
        stopwords = set('que qual quais como para por com uma uns umas seu sua seus suas meu minha meus minhas tem tenho posso voces voce eles elas nos nosso nossa este esta isso isto dos das pelo pela sao'.split())
        best, score = None, 0
        tokens = set(words(text))
        for faq in self.store.items(db, 'faq'):
            for question in faq['perguntas']:
                meaningful = {w for w in words(question) if len(w) >= 3 and w not in stopwords}
                ratio = len(meaningful & tokens) / len(meaningful) if meaningful else 0
                if ratio >= .6 and ratio > score:
                    best, score = faq['resposta'], ratio
        if best is not None:
            state['misses'] = 0
            return reply(best)
        state['misses'] += 1
        if state['misses'] >= 2:
            human('duas mensagens não compreendidas')
        return reply('Não entendi. Posso chamar um atendente.')
