import sqlite3
from pathlib import Path


if __name__ == '__main__':
    db_path = Path('test.db')
else:
    import settings
    db_path = Path(settings.data_path, 'music.db')


def get():
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn