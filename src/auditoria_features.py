"""Additional EDA and prediction-time contract checks on Snowflake training data."""
import numpy as np
import pandas as pd
from scipy.stats import norm

from src.datos import BASE, DOCS, TARGET, dump, split
from src.pipeline import PhysicalFeatures


def run():
    train, _, meta = split()
    frame = PhysicalFeatures().transform(train)
    frame[TARGET] = train[TARGET].to_numpy()
    groups = frame.groupby('product_type', dropna=False)[TARGET].agg(rows='size', failures='sum')
    groups['rate'] = groups.failures / groups.rows
    z = norm.ppf(.975)
    n, rate = groups.rows, groups.rate
    divisor = 1 + z**2/n
    center = (rate + z**2/(2*n))/divisor
    radius = z*np.sqrt(rate*(1-rate)/n + z**2/(4*n**2))/divisor
    groups['wilson_low'], groups['wilson_high'] = center-radius, center+radius
    groups.to_csv(DOCS/'eda_falla_por_tipo.csv')
    quantiles = frame.groupby(TARGET)[BASE[1:]+['temperature_delta_k','power_w']].quantile([.1,.5,.9])
    quantiles.to_csv(DOCS/'eda_cuantiles_por_clase.csv')
    return {'source':meta['source'],'query_id':meta.get('query_id'),'train_rows':len(train),
            'groups':groups.reset_index().to_dict(orient='records')}


def contract():
    train, _, meta = split()
    transform = PhysicalFeatures()
    expected = transform.transform(train[BASE])
    mutated = train.assign(machine_failure=1-train[TARGET], reading_id=-1,
                           TWF=1, HDF=1, PWF=1, OSF=1, RNF=1, baseline_alert=1,
                           quality_tier='unknown', file_sha256='irrelevant', product_id='irrelevant')
    pd.testing.assert_frame_equal(expected, transform.transform(mutated))
    pd.testing.assert_frame_equal(expected.iloc[[0]], transform.transform(train[BASE].iloc[[0]]))
    np.testing.assert_allclose(expected.temperature_delta_k, train.process_temperature_k-train.air_temperature_k)
    np.testing.assert_allclose(expected.power_w, train.torque_nm*train.rotational_speed_rpm*2*np.pi/60)
    contract_columns = [
        {'feature': name, 'unit': unit, 'missing':int(train[name].isna().sum()),
         'invalid':int(invalid.sum())}
        for name, unit, invalid in [
            ('product_type','L / M / H',~train.product_type.isin(['L','M','H'])),
            *((name, unit, ~np.isfinite(train[name]) | (train[name] < 0 if name=='tool_wear_min' else train[name] <= 0))
              for name, unit in zip(BASE[1:], ['K','K','rpm','Nm','min']))
        ]
    ]
    assert all(row['invalid']==0 for row in contract_columns)
    result={'source':meta['source'],'dataset_sha256':meta['dataset_sha256'],'train_rows':len(train),
            'inputs':contract_columns,'invariant_to_target_and_audit_columns':True,
            'single_reading_equivalent_to_batch':True,'derived_from_current_reading':True}
    dump(DOCS/'contrato_inferencia.json',result)
    return result
