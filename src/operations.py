"""Bloqueios, anonimização e indicadores locais do restaurante."""
import calendar
from datetime import datetime, timedelta
import re
from uuid import uuid4
from .booking import ACTIVE, APIError, instant, required


class Operations:
    def operations_dispatch(self, method, path, body, query):
        with self.store.transaction() as db:
            if path == '/api/raiox' and method == 'GET':
                return 200, self.raiox(db, query.get('mes'))
            parts = path.strip('/').split('/')
            identifier = parts[2] if len(parts) == 3 else None
            if identifier is not None:
                self.find(db, 'bloqueios', identifier)
                if method == 'DELETE':
                    db.execute('DELETE FROM cadastros WHERE tipo=? AND id=?', ('bloqueios', identifier))
                    return 204, None
            elif method == 'GET':
                return 200, {'bloqueios': sorted(self.store.items(db, 'bloqueios'), key=lambda b: b['inicio'])}
            elif method == 'POST':
                self.check_room(body.get('salao'))
                if body.get('mesa') is not None:
                    self.find(db, 'mesas', body['mesa'])
                required(body, 'inicio', 'fim', 'motivo')
                if instant(body['inicio']) >= instant(body['fim']):
                    raise APIError(422, 'intervalo_invalido')
                item = {k: body.get(k) for k in ('inicio', 'fim', 'motivo', 'salao', 'mesa')}
                item['id'] = uuid4().hex
                affected = {t['id'] for t in self.store.items(db, 'mesas')
                            if (t['id'] == item['mesa'] if item['mesa'] else
                                not item['salao'] or t['salao'] == item['salao'])}
                conflicts = [r['id'] for r in self.store.items(db, 'reservas') if r['status'] in ACTIVE
                             and r['inicio'] < item['fim'] and r['fim'] > item['inicio']
                             and affected.intersection(r['mesas'])]
                self.store.insert(db, 'bloqueios', item)
                return 201, {'id': item['id'], 'conflitos': conflicts}
        raise APIError(404, 'rota_inexistente')

    def anonymize(self, db, client):
        tel = client['telefone']
        client.update(nome='removido', telefone=None, aniversario=None,
                      consentimento_marketing=False, nao_contatar=True)
        self.store.update(db, 'clientes', client)
        for entry in self.store.items(db, 'espera'):
            if entry['cliente_id'] == client['id']:
                entry['status'] = 'cancelada'
                self.store.update(db, 'espera', entry)
        for reservation in self.store.items(db, 'reservas'):
            if reservation['cliente_id'] == client['id']:
                reservation['observacao'] = ''
                if reservation['status'] in ('reservada', 'confirmada', 'pendente') and instant(reservation['inicio']) > self.now():
                    self.cancel(db, reservation)
                self.store.update(db, 'reservas', reservation)
        for kind in ('mensagens', 'saida', 'humano'):
            for item in self.store.items(db, kind):
                if (not item.get('cliente_id') and tel is not None and item.get('telefone') == tel) or item.get('cliente_id') == client['id']:
                    item.update(telefone=None, cliente_id=client['id'], texto='')
                    if kind == 'saida':
                        item['respondida'] = True
                    if kind == 'humano':
                        item.update(nome='removido', motivo='', status='encerrado')
                    self.store.update(db, kind, item)
        if tel is not None:
            db.execute('DELETE FROM cadastros WHERE tipo=? AND id=?', ('conversas', tel))

    def raiox(self, db, month):
        try:
            if not isinstance(month, str) or not re.fullmatch(r'\d{4}-\d{2}', month):
                raise ValueError()
            first = datetime.strptime(month, '%Y-%m')
        except ValueError:
            raise APIError(422, 'mes_invalido')
        reservations = self.store.items(db, 'reservas')
        monthly = [r for r in reservations if r['inicio'][:7] == month]
        visits = {}
        for r in reservations:
            if r['status'] == 'chegou':
                visits.setdefault(r['cliente_id'], []).append(instant(r['inicio']).date())
        cohort = [sorted(v) for v in visits.values() if min(v).strftime('%Y-%m') == month]
        returning = sum(len(v) > 1 and v[1] <= v[0] + timedelta(days=60) for v in cohort)
        attended = sum(r['status'] == 'chegou' for r in monthly)
        absent = sum(r['status'] == 'no_show' for r in monthly)
        reserved = sum(len(r['mesas']) * (instant(r['fim']) - instant(r['inicio'])).total_seconds() / 60
                       for r in monthly if r['status'] in ACTIVE)
        tables = sum(t['ativa'] for t in self.store.items(db, 'mesas'))
        available = 0
        for day in range(1, calendar.monthrange(first.year, first.month)[1] + 1):
            date = first.replace(day=day)
            if date.strftime('%Y-%m-%d') in self.config.get('feriados', []):
                continue
            weekday = ('seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom')[date.weekday()]
            for shift in self.store.items(db, 'turnos'):
                if shift['ativo'] and weekday in shift['dias']:
                    start, end = (datetime.strptime(shift[k], '%H:%M') for k in ('inicio', 'fim'))
                    available += tables * (end - start).total_seconds() / 60
        def percent(numerator, denominator):
            return round(100 * numerator / denominator, 1) if denominator else 0
        return {'pacote': 'restaurante', 'mes': month, 'valores': {
            'clientes_novos_mes': len(cohort), 'retorno_atual_pct': percent(returning, len(cohort)),
            'reservas_atendidas_mes': attended, 'no_show_pct': percent(absent, attended + absent),
            'ocupacao_pct': percent(reserved, available)}}
