"""Snapshot único, contrato de la OBT y partición persistida sin fuga."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import urllib.request
import zipfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'
SEED = 42
BASE = ['product_type', 'air_temperature_k', 'process_temperature_k',
        'rotational_speed_rpm', 'torque_nm', 'tool_wear_min']
TARGET = 'machine_failure'
PROJECT = 'ai4i-mantenimiento'
TABLE = 'PSET2.OBT.OBT_READINGS'
UCI = 'https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip'

def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding='utf-8')

def canonical_hash(df):
    cols = ['reading_id'] + BASE + [TARGET]
    blob = df[cols].sort_values('reading_id').to_csv(index=False, float_format='%.12g').encode()
    return hashlib.sha256(blob).hexdigest()

def validate(df):
    df = df.copy(); df.columns = df.columns.str.lower()
    required = ['reading_id'] + BASE + [TARGET]
    if missing := set(required) - set(df): raise ValueError(f'Faltan columnas OBT: {sorted(missing)}')
    if df.reading_id.isna().any() or df.reading_id.duplicated().any(): raise ValueError('Grano OBT inválido')
    if not df[TARGET].isin([0, 1]).all(): raise ValueError('Target no binario')
    if not df.product_type.dropna().isin(['L', 'M', 'H']).all(): raise ValueError('Tipo no permitido')
    for c in BASE[1:]:
        df[c] = pd.to_numeric(df[c], errors='raise')
        if np.isinf(df[c]).any(): raise ValueError(f'Infinitos en {c}')
    df[TARGET] = df[TARGET].astype(int)
    return df.sort_values('reading_id').reset_index(drop=True)

def snapshot():
    load_dotenv(ROOT / '.env', override=False)
    DATA.mkdir(exist_ok=True); DOCS.mkdir(exist_ok=True)
    path = DATA / 'snapshot.parquet'
    if path.exists():
        df = validate(pd.read_parquet(path))
        meta = json.loads((DOCS/'dataset.json').read_text(encoding='utf-8'))
        if canonical_hash(df) != meta['dataset_sha256']: raise ValueError('Snapshot modificado')
        return df, meta
    source = os.getenv('DATA_SOURCE', 'snowflake')
    if source == 'snowflake':
        import snowflake.connector
        table = os.getenv('SNOWFLAKE_OBT_TABLE', TABLE)
        if not re.fullmatch(r'[A-Za-z_][\w]*\.[A-Za-z_][\w]*\.[A-Za-z_][\w]*', table):
            raise ValueError('Tabla debe ser DATABASE.SCHEMA.TABLE')
        names = ['ACCOUNT','USER','ROLE','WAREHOUSE','DATABASE','PRIVATE_KEY_FILE']
        opts = {x.lower(): os.environ['SNOWFLAKE_'+x] for x in names}
        with snowflake.connector.connect(**opts) as con:
            cur = con.cursor().execute('SELECT * FROM '+table)
            df = pd.DataFrame(cur.fetchall(), columns=[x[0].lower() for x in cur.description])
            query_id = cur.sfqid
        details = {'source': 'snowflake', 'table': table, 'query_id': query_id,
                   'scope': 'OBT real exportada de Snowflake'}
    elif source == 'uci_replay':
        local_zip = os.getenv('UCI_ZIP')
        blob = Path(local_zip).read_bytes() if local_zip else urllib.request.urlopen(UCI, timeout=120).read()
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            raw = z.read(next(n for n in z.namelist() if n.endswith('ai4i2020.csv')))
        df = pd.read_csv(io.BytesIO(raw)).rename(columns={
            'UDI':'reading_id','Type':'product_type','Air temperature [K]':'air_temperature_k',
            'Process temperature [K]':'process_temperature_k','Rotational speed [rpm]':'rotational_speed_rpm',
            'Torque [Nm]':'torque_nm','Tool wear [min]':'tool_wear_min','Machine failure':TARGET})
        df = df[['reading_id']+BASE+[TARGET]].copy()
        df['temperature_delta_k'] = df.process_temperature_k - df.air_temperature_k
        df['power_w'] = df.torque_nm * df.rotational_speed_rpm * 2*np.pi/60
        df['baseline_alert'] = ((df.tool_wear_min >= 200) | (df.torque_nm >= 60)).astype(int)
        df['quality_tier'] = df.product_type.map({'L':'low','M':'medium','H':'high'})
        df['file_sha256'] = hashlib.sha256(raw).hexdigest()
        details = {'source':'uci_replay','table':TABLE, 'source_url': UCI,
                   'csv_sha256':hashlib.sha256(raw).hexdigest(),
                   'scope':'Reconstrucción local del contrato OBT desde UCI oficial; no es exportación Snowflake'}
    else: raise ValueError('DATA_SOURCE debe ser snowflake o uci_replay')
    df = validate(df); df.to_parquet(path, index=False)
    meta = {**details, 'snapshot_utc':datetime.now(timezone.utc).isoformat(),
            'dataset_sha256':canonical_hash(df), 'rows':len(df), 'target_failures':int(df[TARGET].sum())}
    dump(DOCS/'dataset.json', meta)
    return df, meta

def split():
    df, meta = snapshot()
    path = DOCS/'split.json'
    if not path.exists():
        train, test = train_test_split(df.reading_id, test_size=.2, random_state=SEED, stratify=df[TARGET])
        dump(path, {'dataset_sha256':meta['dataset_sha256'], 'seed':SEED,
                    'train_ids':sorted(map(int,train)), 'test_ids':sorted(map(int,test)),
                    'cv':'StratifiedKFold(n_splits=3, shuffle=True, random_state=42)'})
    spec = json.loads(path.read_text(encoding='utf-8'))
    if spec['dataset_sha256'] != meta['dataset_sha256']: raise ValueError('Split de otro dataset')
    a,b = set(spec['train_ids']),set(spec['test_ids'])
    if a & b or a | b != set(df.reading_id): raise ValueError('Split inconsistente')
    return df[df.reading_id.isin(a)].copy(), df[df.reading_id.isin(b)].copy(), meta
