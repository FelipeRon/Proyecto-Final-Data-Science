from math import pi

import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from src.datos import BASE
from src.pipeline import PhysicalFeatures, make_pipeline


@pytest.fixture
def readings():
    return pd.DataFrame([
        ['L', 300., 310., 1500., 30., 10.],
        ['M', 300., 312., 1400., 45., 30.],
        ['H', 301., 310., 1300., 65., 100.],
        ['L', 302., 311., 1250., 70., 200.],
    ], columns=BASE)


def test_derived_units(readings):
    projected = PhysicalFeatures().transform(readings)
    assert projected.iloc[0].temperature_delta_k == 10
    assert projected.iloc[0].power_w == pytest.approx(30 * 1500 * 2 * pi / 60)


def test_labels_and_identifiers_do_not_change_inputs(readings):
    clean = PhysicalFeatures().transform(readings)
    noisy = readings.assign(machine_failure=1, reading_id=99, TWF=1)
    pd.testing.assert_frame_equal(clean, PhysicalFeatures().transform(noisy))


def test_one_reading_matches_batch_using_test_model(readings):
    pipeline = make_pipeline(LogisticRegression()).fit(readings,[0,0,1,1])
    assert pipeline.predict_proba(readings.iloc[[0]])[0] == pytest.approx(pipeline.predict_proba(readings)[0])
