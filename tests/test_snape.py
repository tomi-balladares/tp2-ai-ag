import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algoritmo import ejecutar_ag  # noqa: E402  (también crea los tipos de DEAP)
from aptitud import APTITUD_MAXIMA, desglose, evaluar  # noqa: E402
from config import cargar_corridas  # noqa: E402
from cromosoma import (  # noqa: E402
    AVANZAR, LARGO_CROMOSOMA, RETROCEDER, TAMANO_INVALIDO, VENENO, VINO,
    codificar, decodificar, posicion_avanzar,
)
from deap import creator  # noqa: E402
from operadores import (  # noqa: E402
    ProbabilidadMutacion, cruza_binomial_azar, cruza_binomial_mascara_complemento,
    cruza_binomial_mascara_doble, cruza_multipunto, cruza_simple, individuo_ad_hoc,
    mascara_por_texto, mutar, seleccion_control_numero_esperado, seleccion_ruleta,
)
from verificar_fuerza_bruta import soluciones_fuerza_bruta  # noqa: E402

V, W, A, R = VENENO, VINO, AVANZAR, RETROCEDER

# Solución conocida: contenidos R V W A V V W; enano en B1 (R) y gigante en B4 (A).
CONTENIDOS_OK = [R, V, W, A, V, V, W]
TAMANOS_OK = [0, 1, 2, 6, 3, 4, 5]


@pytest.fixture
def solucion():
    return codificar(TAMANOS_OK, CONTENIDOS_OK)


# --- Cromosoma ---------------------------------------------------------------

def test_decodificacion_ida_y_vuelta():
    random.seed(0)
    for _ in range(200):
        bits = [random.randint(0, 1) for _ in range(LARGO_CROMOSOMA)]
        assert codificar(*decodificar(bits)) == bits


def test_codificacion_bloques(solucion):
    # B1: tamaño 000, contenido 11 (retroceder)
    assert solucion[:5] == [0, 0, 0, 1, 1]
    # B4: tamaño 110 (gigante), contenido 10 (avanzar)
    assert solucion[15:20] == [1, 1, 0, 1, 0]
    assert posicion_avanzar(solucion) == [4]


# --- Aptitud -----------------------------------------------------------------

def test_solucion_conocida_da_55(solucion):
    assert evaluar(solucion) == (APTITUD_MAXIMA,)
    d = desglose(solucion)
    assert all(d["condiciones"].values())
    assert not any(d["restricciones"].values())


def test_tamano_111_resta_10(solucion):
    tamanos = TAMANOS_OK[:]
    tamanos[2] = TAMANO_INVALIDO  # B3 pasa de tamaño 3 a 111
    ind = codificar(tamanos, CONTENIDOS_OK)
    d = desglose(ind)
    assert d["tamanos_invalidos"] == 1
    # Sigue cumpliendo todas las condiciones (los tamaños siguen sin repetirse)
    assert all(d["condiciones"].values()) and not any(d["restricciones"].values())
    assert evaluar(ind)[0] == APTITUD_MAXIMA - 10


def test_dos_tamanos_111_restan_10_cada_uno():
    tamanos = TAMANOS_OK[:]
    tamanos[2] = tamanos[4] = TAMANO_INVALIDO
    d = desglose(codificar(tamanos, CONTENIDOS_OK))
    assert d["tamanos_invalidos"] == 2
    assert not d["condiciones"]["C1"]  # dos 111 = tamaño repetido
    assert d["aptitud"] == 50 - 20


def test_vino_en_botella_1():
    d = desglose(codificar(TAMANOS_OK, [W, V, W, A, V, V, R]))
    assert d["restricciones"]["R1"]
    assert not d["condiciones"]["C6"]


def test_sin_vinos_no_cumple_c6():
    d = desglose(codificar(TAMANOS_OK, [R, V, V, A, V, V, R]))
    assert not d["condiciones"]["C6"]


def test_sin_enano_no_cumple_c8():
    d = desglose(codificar([1, 2, 3, 6, 4, 5, 5], CONTENIDOS_OK))
    assert not d["condiciones"]["C8"]
    assert not d["restricciones"]["R6"]


def test_todas_las_soluciones_de_fuerza_bruta_dan_55():
    disposiciones, soluciones = soluciones_fuerza_bruta()
    assert len(disposiciones) == 8
    assert len(soluciones) == 11520
    assert {c.index(AVANZAR) + 1 for c in disposiciones} == {3, 4, 5}
    assert all(evaluar(list(s))[0] == 55 for s in soluciones[::97])


# --- Cruza -------------------------------------------------------------------

def _padres():
    return [0] * LARGO_CROMOSOMA, [1] * LARGO_CROMOSOMA


def test_cruza_simple_un_punto():
    random.seed(1)
    x, y = _padres()
    a, b = cruza_simple(x, y)
    assert len(a) == len(b) == LARGO_CROMOSOMA
    corte = a.index(1)
    assert a == [0] * corte + [1] * (LARGO_CROMOSOMA - corte)
    assert b == [1 - g for g in a]


@pytest.mark.parametrize("puntos", [2, 3, 5])
def test_cruza_multipunto(puntos):
    random.seed(2)
    x, y = _padres()
    a, b = cruza_multipunto(x, y, puntos_corte=puntos)
    assert len(a) == len(b) == LARGO_CROMOSOMA
    cambios = sum(a[i] != a[i + 1] for i in range(LARGO_CROMOSOMA - 1))
    assert cambios == puntos
    assert b == [1 - g for g in a]


def test_cruza_mascara_complemento_respeta_mascara():
    mascara = mascara_por_texto("11111 00000 11111 00000 11111 00000 11111")
    random.seed(3)
    x = [random.randint(0, 1) for _ in range(LARGO_CROMOSOMA)]
    y = [random.randint(0, 1) for _ in range(LARGO_CROMOSOMA)]
    x0, y0 = x[:], y[:]
    a, b = cruza_binomial_mascara_complemento(x, y, mascara=mascara)
    assert len(a) == len(b) == LARGO_CROMOSOMA
    for i, m in enumerate(mascara):
        assert a[i] == (x0[i] if m else y0[i])
        assert b[i] == (y0[i] if m else x0[i])


def test_cruza_mascara_doble_con_mascaras_fijas():
    ma = "10" * 17 + "1"
    mb = "0" * 35
    x, y = _padres()
    a, b = cruza_binomial_mascara_doble(x, y, mascara_a=ma, mascara_b=mb)
    assert a == [0 if m == "1" else 1 for m in ma]  # 1 -> padre X (ceros)
    assert b == [1] * LARGO_CROMOSOMA               # todo del padre Y


def test_cruza_binomial_azar_genes_de_los_padres():
    random.seed(4)
    x = [random.randint(0, 1) for _ in range(LARGO_CROMOSOMA)]
    y = [random.randint(0, 1) for _ in range(LARGO_CROMOSOMA)]
    x0, y0 = x[:], y[:]
    a, b = cruza_binomial_azar(x, y)
    for hijo in (a, b):
        assert len(hijo) == LARGO_CROMOSOMA
        assert all(g in (gx, gy) for g, gx, gy in zip(hijo, x0, y0))
    # Con padres complementarios, ~la mitad de los genes viene de cada uno.
    random.seed(5)
    a, _ = cruza_binomial_azar(*_padres())
    assert 8 <= sum(a) <= 27


# --- Selección ---------------------------------------------------------------

def _poblacion(aptitudes):
    pob = []
    for i, apt in enumerate(aptitudes):
        ind = creator.Individual([i % 2] * LARGO_CROMOSOMA)
        ind.fitness.values = (apt,)
        ind.id = i
        pob.append(ind)
    return pob


def test_ruleta_con_aptitudes_negativas():
    random.seed(6)
    pob = _poblacion([-70, -40, -10, 20, 55])
    elegidos = seleccion_ruleta(pob, 5000)
    conteo = [sum(e.id == i for e in elegidos) for i in range(5)]
    assert len(elegidos) == 5000
    # El peor (desplazado a ~0) prácticamente no se elige y el orden se respeta.
    assert conteo[0] < 5
    assert conteo[1] < conteo[2] < conteo[3] < conteo[4]


def test_control_numero_esperado():
    random.seed(7)
    pob = _poblacion([-10, 0, 10, 20, 30])  # desplazadas ~ 0,10,20,30,40 -> esperados 0,.5,1,1.5,2
    elegidos = seleccion_control_numero_esperado(pob, 5)
    ids = [e.id for e in elegidos]
    assert len(ids) == 5
    assert ids.count(4) >= 2 and ids.count(3) >= 1 and ids.count(2) >= 1
    assert 0 not in ids


# --- Mutación ----------------------------------------------------------------

def test_mutacion_invierte_un_solo_bit():
    random.seed(8)
    ind = [0] * LARGO_CROMOSOMA
    assert mutar(ind, 1.0)
    assert sum(ind) == 1
    assert not mutar(ind, 0.0)


def test_mutacion_temperatura():
    asc = ProbabilidadMutacion("adaptativa_temperatura_ascendente", prob_min=0.01, prob_max=0.3,
                               max_generaciones=100)
    desc = ProbabilidadMutacion("adaptativa_temperatura_descendente", prob_min=0.01, prob_max=0.3,
                                max_generaciones=100)
    assert asc.calcular(0, 0, 0) == pytest.approx(0.01)
    assert asc.calcular(100, 0, 0) == pytest.approx(0.3)
    assert desc.calcular(0, 0, 0) == pytest.approx(0.3)
    assert desc.calcular(50, 0, 0) == pytest.approx(0.155)


def test_mutacion_convergencia_sube_al_estancarse():
    m = ProbabilidadMutacion("adaptativa_convergencia", prob_min=0.01, prob_max=0.3, ventana=5)
    primera = m.calcular(0, 0, 40)
    for g in range(1, 6):
        ultima = m.calcular(g, 0, 40)
    assert primera == pytest.approx(0.01)
    assert ultima == pytest.approx(0.3)


# --- Población inicial y bucle -----------------------------------------------

def test_individuo_ad_hoc_cumple_c1_a_c5():
    random.seed(9)
    for _ in range(50):
        d = desglose(individuo_ad_hoc())
        assert all(d["condiciones"][c] for c in ("C1", "C2", "C3", "C4", "C5"))
        assert d["tamanos_invalidos"] == 0


def test_corrida_reproducible_con_semilla():
    p = cargar_corridas()[0]
    p["paro"]["max_generaciones"] = 15
    r1 = ejecutar_ag(p, semilla=123)
    r2 = ejecutar_ag(p, semilla=123)
    assert [f["aptitud_promedio"] for f in r1.registros] == [f["aptitud_promedio"] for f in r2.registros]
    assert len(r1.registros) == r1.generaciones + 1
