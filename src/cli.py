import argparse
import json
from pathlib import Path
import sqlite3
import tempfile
import zipfile

from .server import Application, make_server
from .storage import Store


def main():
    parser = argparse.ArgumentParser(description="Reservas de mesa para um restaurante")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Iniciar o servidor HTTP")
    serve.add_argument("--porta", type=int, default=8080)
    serve.add_argument("--dados", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    for command, option in (('backup', '--saida'), ('restaurar', '--entrada'), ('raiox', '--acompanhamento')):
        sub = commands.add_parser(command)
        sub.add_argument('--dados', required=True)
        sub.add_argument(option, required=True)
        if command == 'raiox':
            sub.add_argument('--mes', required=True)
    args = parser.parse_args()
    if args.command in ('backup', 'restaurar'):
        directory = Path(args.dados)
        if args.command == 'backup':
            with tempfile.TemporaryDirectory() as temporary:
                snapshot = Path(temporary) / 'reservas.sqlite3'
                with sqlite3.connect(directory / 'reservas.sqlite3') as source, sqlite3.connect(snapshot) as target:
                    source.backup(target)
                with zipfile.ZipFile(args.saida, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.write(snapshot, 'reservas.sqlite3')
                    archive.write(directory / 'restaurante.json', 'restaurante.json')
        else:
            with zipfile.ZipFile(args.entrada) as archive:
                contents = {name: archive.read(name) for name in ('reservas.sqlite3', 'restaurante.json')}
            json.loads(contents['restaurante.json'])
            directory.mkdir(parents=True, exist_ok=True)
            for name, content in contents.items():
                target = directory / name
                temporary = target.with_suffix('.restaurando')
                temporary.write_bytes(content)
                temporary.replace(target)
        return
    app = Application(Store(args.dados))
    if args.command == 'raiox':
        path = Path(args.acompanhamento)
        document = json.loads(path.read_text(encoding='utf-8'))
        with app.store.transaction() as db:
            measured = app.raiox(db, args.mes)['valores']
        previous = [m for m in document['meses'] if m['mes'] < args.mes]
        baseline = max(previous, key=lambda m: m['mes']) if previous else document['base']
        entry = {'mes': args.mes, 'valores': {**baseline['valores'], **measured}, 'obs': 'reserva-restaurante'}
        document['meses'] = sorted([m for m in document['meses'] if m['mes'] != args.mes] + [entry], key=lambda m: m['mes'])
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
        return
    with make_server(app, args.host, args.porta) as server:
        print(f"PORTA={server.server_address[1]}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
