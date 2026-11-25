import json
from types import SimpleNamespace

import pytest

from monitoreo.alertas import debe_reentrenar, evaluar, resumen
from src import promover


def lote(periodo, psi=.05, caida=False, ap=.95, tasa=.05, costo=90000., regla=190000.):
    return dict(periodo=periodo, psi_max=psi, caida_ap=caida, ap=ap, alert_rate=tasa,
                cost_per_1000=costo, costo_regla=regla, query_id="q1")


CONTROLES = [lote(n) for n in range(1, 9)]


def test_controles_no_alertan_ni_reentrenan():
    assert evaluar(CONTROLES) == [] and debe_reentrenar(CONTROLES) is None


def test_deriva_con_impacto_reentrena():
    lotes = CONTROLES[:5] + [lote(6, psi=2.63, caida=True, ap=.67, tasa=.62)] + CONTROLES[6:]
    motivo = debe_reentrenar(lotes)
    assert motivo["periodo"] == 6 and motivo["tipo"] == "deriva de datos con impacto"
    assert {e["regla"] for e in evaluar(lotes)} == {"psi", "caida_ap", "tasa_inspeccion"}
    assert resumen({"lotes": lotes})["firma"] == "q1/6/deriva de datos con impacto"


def test_deriva_sin_caida_no_reentrena():
    # Sección 7.1: la deriva de datos sin caída de desempeño no dispara el reentrenamiento.
    lotes = CONTROLES[:5] + [lote(6, psi=2.63)] + CONTROLES[6:]
    assert [e["regla"] for e in evaluar(lotes)] == ["psi"]
    assert debe_reentrenar(lotes) is None


def test_caida_aislada_alerta_pero_dos_seguidas_reentrenan():
    una = CONTROLES[:7] + [lote(8, caida=True, ap=.70)]
    assert debe_reentrenar(una) is None and evaluar(una)[0]["regla"] == "caida_ap"
    dos = CONTROLES[:6] + [lote(7, caida="true", ap=.75), lote(8, caida=True, ap=.70)]
    assert debe_reentrenar(dos)["tipo"] == "caída de AP en 2 lotes seguidos"


def test_costo_sobre_la_regla_en_dos_lotes_alerta():
    lotes = [lote(1, costo=200000.), lote(2, costo=210000.)]
    assert [e["regla"] for e in evaluar(lotes)] == ["costo"]


def test_sin_datos_no_dispara():
    assert resumen({"ultimo_lote": None, "alertas": []})["reentrenar"] is False


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
