from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from api.esquemas import Reading
from src.datos import BASE


def test_serving_schema_accepts_all_fixed_snapshot_features():
    sample = pd.read_csv(Path(__file__).parent / 'fixtures' / 'holdout.csv')
    assert list(Reading.model_fields) == BASE
    for row in sample[BASE].to_dict(orient='records'):
        assert Reading.model_validate(row).model_dump() == row


@pytest.mark.parametrize('extra', ['machine_failure', 'reading_id', 'TWF', 'baseline_alert'])
def test_serving_schema_rejects_label_and_audit_fields(extra):
    row = {'product_type':'L', 'air_temperature_k':300., 'process_temperature_k':310.,
           'rotational_speed_rpm':1500., 'torque_nm':40., 'tool_wear_min':0., extra:1}
    with pytest.raises(ValidationError, match=extra):
        Reading.model_validate(row)
