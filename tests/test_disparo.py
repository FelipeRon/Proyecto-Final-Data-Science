import json
from types import SimpleNamespace

import pytest

from monitoreo.disparo import evaluar
from src import promover


ESTADO = {"ultimo_lote": {"periodo": 8, "psi_max": .06, "query_id": "q1"},
          "alertas": [{"periodo": 6, "variable": "torque_nm", "psi": 2.633, "query_id": "q1"}]}


def test_alerta_supera_umbral():
    resultado = evaluar(ESTADO, .25)
    assert resultado["supera_umbral"] and resultado["periodo"] == 6
    assert resultado["variable"] == "torque_nm" and resultado["firma"] == "q1/6/torque_nm"


def test_controles_no_disparan():
    resultado = evaluar({"ultimo_lote": ESTADO["ultimo_lote"], "alertas": []}, .25)
    assert not resultado["supera_umbral"] and resultado["psi_max"] == pytest.approx(.06)


def test_sin_datos_no_dispara():
    assert evaluar({"ultimo_lote": None, "alertas": []})["supera_umbral"] is False


class Registro:
    def __init__(self, champion="1", candidato="3"):
        self.alias = {promover.CHAMPION: champion, promover.CANDIDATE: candidato}
        self.tags = {}

    def get_model_version_by_alias(self, name, alias):
        return SimpleNamespace(version=self.alias[alias])

    def set_registered_model_alias(self, name, alias, version):
        self.alias[alias] = version

    def set_model_version_tag(self, name, version, key, value):
        self.tags[key] = value


@pytest.fixture
def ciclo(tmp_path):
    def escribir(califica):
        path = tmp_path / "reentrenamiento.json"
        path.write_text(json.dumps({"version": "3", "califica": califica, "disparador": "PSI"}))
        return path
    return escribir


def test_promueve_y_guarda_rollback(ciclo, tmp_path):
    client = Registro()
    salida = tmp_path / "aprobacion.json"
    resultado = promover.decidir("promover", "3", "Ana", "ok", client, ciclo(True), salida)
    assert client.alias[promover.CHAMPION] == "3" and resultado["champion_anterior"] == "1"
    assert client.tags["aprobacion"] == "promover" and salida.exists()


def test_rechazo_conserva_champion(ciclo, tmp_path):
    client = Registro()
    promover.decidir("rechazar", "3", "Ana", "", client, ciclo(True), tmp_path / "a.json")
    assert client.alias[promover.CHAMPION] == "1" and client.tags["aprobacion"] == "rechazar"


def test_no_promueve_candidato_que_no_califica(ciclo, tmp_path):
    client = Registro()
    with pytest.raises(SystemExit):
        promover.decidir("promover", "3", "Ana", "", client, ciclo(False), tmp_path / "a.json")
    assert client.alias[promover.CHAMPION] == "1" and not client.tags


def test_version_distinta_al_ciclo(ciclo, tmp_path):
    with pytest.raises(SystemExit):
        promover.decidir("promover", "2", "Ana", "", Registro(), ciclo(True), tmp_path / "a.json")
