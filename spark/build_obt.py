"""Gold -> OBT. Local Parquet mode exercises the same joins without cloud credentials."""
import argparse, json, os
from pathlib import Path
from pyspark.sql import SparkSession, functions as F

FEATURES=['product_type','air_temperature_k','process_temperature_k',
          'rotational_speed_rpm','torque_nm','tool_wear_min','temperature_delta_k','power_w']

def build(fact, dim):
    if dim.filter(F.col('product_type').isNull()).count() or dim.groupBy('product_type').count().filter('count > 1').count():
        raise ValueError('Dimension key not unique/non-null')
    n=fact.count()
    if fact.filter(F.col('reading_id').isNull()).count() or fact.select('reading_id').distinct().count()!=n:
        raise ValueError('Fact grain violated')
    joined=fact.join(dim,'product_type','left')
    if joined.count()!=n or joined.select('reading_id').distinct().count()!=n or joined.filter(F.col('quality_tier').isNull()).count():
        raise ValueError('Join fanout or orphan')
    # Failure modes are target-derived; identifiers and baseline are audit only.
    return joined.select('reading_id', *FEATURES, 'quality_tier', 'machine_failure',
                         'baseline_alert','file_sha256'), n

def main():
    p=argparse.ArgumentParser(); p.add_argument('--local',action='store_true'); p.add_argument('--path',default='/app/artifacts'); a=p.parse_args()
    spark=SparkSession.builder.appName('ai4i-obt').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    options={}
    if a.local:
        fact=spark.read.parquet(a.path+'/fct_reading.parquet'); dim=spark.read.parquet(a.path+'/dim_product_type.parquet')
    else:
        from cryptography.hazmat.primitives import serialization
        key=serialization.load_pem_private_key(Path(os.environ['SNOWFLAKE_PRIVATE_KEY_FILE']).read_bytes(),password=None)
        options=dict(sfURL=os.environ['SNOWFLAKE_ACCOUNT']+'.snowflakecomputing.com',
          sfUser=os.environ['SNOWFLAKE_USER'], sfRole=os.environ['SNOWFLAKE_ROLE'],
          sfWarehouse=os.environ['SNOWFLAKE_WAREHOUSE'], sfDatabase=os.environ['SNOWFLAKE_DATABASE'],
          sfSchema='GOLD', pem_private_key=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode().replace('-----BEGIN PRIVATE KEY-----','').replace('-----END PRIVATE KEY-----','').replace('\n',''))
        def read(table):
            df=spark.read.format('net.snowflake.spark.snowflake').options(**options).option('dbtable',table).load()
            return df.toDF(*[c.lower() for c in df.columns])
        fact,dim=read('FCT_READING'),read('DIM_PRODUCT_TYPE')
    obt,n=build(fact,dim)
    if a.local:
        obt.write.mode('overwrite').parquet(a.path+'/obt.parquet')
        saved=spark.read.parquet(a.path+'/obt.parquet')
    else:
        options['sfSchema']='OBT'
        obt.write.format('net.snowflake.spark.snowflake').options(**options).option('dbtable','OBT_READINGS').mode('overwrite').save()
        saved=spark.read.format('net.snowflake.spark.snowflake').options(**options).option('dbtable','OBT_READINGS').load()
    saved=saved.toDF(*[c.lower() for c in saved.columns])
    if saved.count()!=n or saved.select('reading_id').distinct().count()!=n:
        raise ValueError('Persisted OBT grain mismatch')
    if saved.agg(F.sum('machine_failure')).first()[0] != fact.agg(F.sum('machine_failure')).first()[0]:
        raise ValueError('Persisted target count mismatch')
    print(json.dumps({'fact_rows':n,'obt_rows':saved.count(),'unique_ids':n,'join_validated':True}))
    spark.stop()
if __name__=='__main__': main()
