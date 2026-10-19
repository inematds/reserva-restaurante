"""Persistência dos cadastros; cada operação usa sua própria conexão."""
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import sqlite3

ROOT = Path(__file__).resolve().parent.parent


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        config = self.directory / "restaurante.json"
        if not config.exists():
            shutil.copyfile(ROOT / "exemplos/restaurante.json", config)
        self.config = json.loads(config.read_text(encoding="utf-8"))
        self.path = self.directory / "reservas.sqlite3"
        with self.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS metadata (chave TEXT PRIMARY KEY, valor TEXT)")
            db.execute("""CREATE TABLE IF NOT EXISTS cadastros (
                ordem INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL, id TEXT NOT NULL, dados TEXT NOT NULL,
                UNIQUE(tipo, id))""")
            if not db.execute("SELECT 1 FROM metadata WHERE chave='semeado'").fetchone():
                for kind in ("mesas", "turnos", "faq"):
                    for item in self.config.get(kind, []):
                        item = dict(item)
                        if kind == "mesas":
                            item.setdefault("ativa", True)
                        if kind == "turnos":
                            item.setdefault("ativo", True)
                        self.insert(db, kind, item)
                db.execute("INSERT INTO metadata VALUES ('semeado', '1')")

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def items(db, kind):
        return [json.loads(row[0]) for row in db.execute(
            "SELECT dados FROM cadastros WHERE tipo=? ORDER BY ordem", (kind,))]

    @staticmethod
    def insert(db, kind, item):
        db.execute("INSERT INTO cadastros(tipo,id,dados) VALUES (?,?,?)",
                   (kind, item["id"], json.dumps(item, ensure_ascii=False)))

    @staticmethod
    def update(db, kind, item):
        db.execute("UPDATE cadastros SET dados=? WHERE tipo=? AND id=?",
                   (json.dumps(item, ensure_ascii=False), kind, item["id"]))
