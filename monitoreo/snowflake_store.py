"""Snowflake storage for predictions, replay monitoring and alerts."""
import json
import os

import pandas as pd
import snowflake.connector

from src.datos import BASE, TABLE, canonical_hash, validate

TABLES = {'predicciones':('ID_PREDICCION','id_prediccion'),
          'monitoreo':('PERIODO','periodo'), 'alertas':('CLAVE',None)}


def connect():
    keys = ('ACCOUNT','USER','ROLE','WAREHOUSE','DATABASE','PRIVATE_KEY_FILE')
    return snowflake.connector.connect(**{k.lower():os.environ['SNOWFLAKE_'+k] for k in keys})


def read_partition(spec):
    with connect() as connection:
        cursor = connection.cursor().execute(f'SELECT * FROM {TABLE}')
        data = validate(pd.DataFrame(cursor.fetchall(),columns=[c[0] for c in cursor.description]))
        query_id = cursor.sfqid
    digest = canonical_hash(data)
    if digest != spec['dataset_sha256']:
        raise ValueError('La OBT activa cambió respecto del snapshot del modelo')
    train = data[data.reading_id.isin(spec['train_ids'])].sort_values('reading_id').reset_index(drop=True)
    test = data[data.reading_id.isin(spec['test_ids'])].sort_values('reading_id').reset_index(drop=True)
    if len(train) != len(spec['train_ids']) or len(test) != len(spec['test_ids']):
        raise ValueError('Partición incompleta')
    return train,test,{'source':'snowflake','table':TABLE,'query_id':query_id,'dataset_sha256':digest}


def initialize(cursor, names):
    for name in names:
        column,_ = TABLES[name]
        cursor.execute(f'CREATE TABLE IF NOT EXISTS OBT.{name.upper()} ({column} VARCHAR, PAYLOAD VARIANT)')


def write_batch(cursor, name, rows):
    column,key = TABLES[name]
    for start in range(0,len(rows),250):
        batch = rows[start:start+250]
        payload = json.dumps([
            {'id':str(row[key]) if key else f'{row["periodo"]}:{row["variable"]}', 'data':row}
            for row in batch], allow_nan=False)
        cursor.execute(f"""
            MERGE INTO OBT.{name.upper()} t
            USING (SELECT value:id::VARCHAR AS ID, value:data AS DATA
                   FROM TABLE(FLATTEN(INPUT => PARSE_JSON(%s)))) s
            ON t.{column}=s.ID WHEN MATCHED THEN UPDATE SET PAYLOAD=s.DATA
            WHEN NOT MATCHED THEN INSERT ({column},PAYLOAD) VALUES (s.ID,s.DATA)
            """,(payload,))


def save(groups, replace_alerts=False):
    with connect() as connection:
        cur=connection.cursor()
        initialize(cur, groups)
        cur.execute('BEGIN')
        try:
            if replace_alerts:
                cur.execute("DELETE FROM OBT.ALERTAS WHERE PAYLOAD:origen::VARCHAR='replay_pset4'")
            for name, rows in groups.items():
                write_batch(cur,name,rows)
            cur.execute('COMMIT')
        except Exception:
            cur.execute('ROLLBACK')
            raise


def read_rows(*names):
    with connect() as connection:
        cur=connection.cursor()
        return {name:[json.loads(row[0]) for row in cur.execute(
            f'SELECT TO_JSON(PAYLOAD) FROM OBT.{name.upper()} ORDER BY {TABLES[name][0]}'
        )] for name in names if name in TABLES}
