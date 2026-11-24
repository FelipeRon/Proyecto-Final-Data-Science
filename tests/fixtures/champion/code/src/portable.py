"""Respaldo de tracking y modelos y restauración reubicable del registro."""
import argparse
import json
import sqlite3
import zipfile
from pathlib import Path
from .datos import ROOT, DOCS

def pack():
    art=ROOT/'artifacts';db=art/'mlflow.db'
    if not db.exists():raise RuntimeError('El backup empaquetado requiere backend SQLite local')
    backup=art/'backup.db'
    with sqlite3.connect(db) as source,sqlite3.connect(backup) as target:source.backup(target)
    dest=DOCS/'mlflow_snapshot.zip'
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.write(backup,'artifacts/mlflow.db')
        for path in (art/'mlruns').rglob('*'):
            if path.is_file():z.write(path,path.relative_to(ROOT).as_posix())
        for name in ['snapshot.parquet']:
            z.write(ROOT/'data'/name,'data/'+name)
        z.writestr('manifest.json',json.dumps({'old_root':str(ROOT),'old_uri':ROOT.as_uri(),
            'scope':'tracking SQLite y modelos reales de la corrida local; snapshot UCI replay'}))
    print(f'Backup {dest.stat().st_size/1024**2:.1f} MiB')

def restore():
    db=ROOT/'artifacts'/'mlflow.db'
    if db.exists():raise RuntimeError('Ya existe artifacts/mlflow.db; no se sobrescribe tracking existente')
    with zipfile.ZipFile(DOCS/'mlflow_snapshot.zip') as z:
        manifest=json.loads(z.read('manifest.json'))
        for name in z.namelist():
            if name=='manifest.json':continue
            path=(ROOT/name).resolve()
            if not path.is_relative_to(ROOT):raise ValueError('Ruta no segura')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(name))
    replacements=[(manifest['old_uri'],ROOT.as_uri()),(manifest['old_root'],str(ROOT)),
                  (manifest['old_root'].replace('\\','/'),ROOT.as_posix())]
    with sqlite3.connect(db) as con:
        for table,col in [('experiments','artifact_location'),('runs','artifact_uri'),
                          ('model_versions','source'),('model_versions','storage_location')]:
            for a,b in replacements:
                con.execute(f'UPDATE {table} SET {col}=replace({col},?,?)',(a,b))
    print('Tracking, datos y aliases restaurados. Ejecutar python -m src.experimentos verify')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['pack','restore']);args=p.parse_args()
    {'pack':pack,'restore':restore}[args.action]()
