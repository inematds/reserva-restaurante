import argparse

from .server import Application, make_server
from .storage import Store


def main():
    parser = argparse.ArgumentParser(description="Reservas de mesa para um restaurante")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Iniciar o servidor HTTP")
    serve.add_argument("--porta", type=int, default=8080)
    serve.add_argument("--dados", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    app = Application(Store(args.dados))
    with make_server(app, args.host, args.porta) as server:
        print(f"PORTA={server.server_address[1]}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
