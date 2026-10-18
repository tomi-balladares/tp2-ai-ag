"""
Bucle evolutivo propio (no se usa eaSimple porque necesitamos mutación
adaptativa, criterios de paro combinados y logueo por generación).

Ciclo por generación:
  1. Evaluar la población y registrar estadísticas.
  2. Guardar en el "salón de la fama" toda solución distinta con aptitud 55.
  3. Calcular ProbM (puede depender de la generación o de la convergencia).
  4. Verificar los criterios de paro.
  5. Elitismo (opcional): copiar los mejores sin cambios.
  6. Selección -> cruza (con probabilidad prob_cruza) -> mutación.
"""
import random
import statistics
import time
from dataclasses import dataclass, field

from deap import base, creator, tools

from aptitud import APTITUD_MAXIMA, evaluar
from cromosoma import bits_a_texto, decodificado_a_texto
from operadores import (
    GENERADORES_POBLACION, METODOS_CRUZA, METODOS_SELECCION,
    ProbabilidadMutacion, mutar,
)


def crear_tipos():
    """Tipos de DEAP: individuo = lista de bits, aptitud a maximizar."""
    if not hasattr(creator, "FitnessMax"):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMax)


crear_tipos()


@dataclass
class ResultadoCorrida:
    parametros: dict
    semilla: int
    registros: list = field(default_factory=list)   # una fila (dict) por generación
    mejor: list = None                               # mejor individuo de toda la corrida
    soluciones: dict = field(default_factory=dict)  # tupla de bits -> generación en que apareció
    criterio_paro: str = ""
    generaciones: int = 0
    generacion_convergencia: int = None              # primera generación con aptitud 55
    tiempo: float = 0.0
    tiempo_convergencia: float = None                # segundos hasta la primera solución


def _parametros_seleccion(p):
    if p["seleccion"] == "torneo":
        return {"tamano_torneo": p["tamano_torneo"]}
    if p["seleccion"] == "ranking":
        return {"proporcion_ranking": p["proporcion_ranking"]}
    return {}


def _parametros_cruza(p):
    if p["cruza"] == "multipunto":
        return {"puntos_corte": p["puntos_corte"]}
    if p["cruza"] == "binomial_mascara_complemento":
        return {"mascara": p.get("mascara")}
    if p["cruza"] == "binomial_mascara_doble":
        return {"mascara_a": p.get("mascara_a"), "mascara_b": p.get("mascara_b")}
    return {}


def _verificar_paro(paro, generacion, maxima, promedio, transcurrido):
    """Devuelve el nombre del criterio que corta la corrida, o None."""
    if paro.get("parar_en_aptitud_maxima") and maxima >= APTITUD_MAXIMA:
        return "aptitud_maxima"
    if paro.get("promedio_objetivo") is not None and \
            abs(promedio - paro["promedio_objetivo"]) <= paro.get("tolerancia_promedio", 0.0):
        return "promedio_objetivo"
    if paro.get("tiempo_maximo") is not None and transcurrido >= paro["tiempo_maximo"]:
        return "tiempo_maximo"
    if generacion >= paro["max_generaciones"]:
        return "max_generaciones"
    return None


def ejecutar_ag(parametros, semilla=None, verbose=False):
    """Ejecuta una corrida completa con los parámetros dados (ver corridas.yaml)."""
    p = parametros
    semilla = p.get("semilla") if semilla is None else semilla
    random.seed(semilla)

    generar = GENERADORES_POBLACION[p["poblacion_inicial"]]
    seleccionar = METODOS_SELECCION[p["seleccion"]]
    cruzar = METODOS_CRUZA[p["cruza"]]
    params_sel = _parametros_seleccion(p)
    params_cx = _parametros_cruza(p)
    paro = p["paro"]
    n = p["tamano_poblacion"]
    n_elite = p.get("elitismo", 0) or 0

    prob_mut = ProbabilidadMutacion(
        metodo=p["mutacion"], prob_mutacion=p["prob_mutacion"],
        prob_min=p["prob_min"], prob_max=p["prob_max"], ventana=p["ventana"],
        tolerancia_estancamiento=p["tolerancia_estancamiento"],
        max_generaciones=paro["max_generaciones"],
    )

    resultado = ResultadoCorrida(parametros=p, semilla=semilla)
    salon_fama = tools.HallOfFame(1)

    inicio = time.perf_counter()
    poblacion = [creator.Individual(generar()) for _ in range(n)]
    for ind in poblacion:
        ind.fitness.values = evaluar(ind)

    generacion = 0
    while True:
        aptitudes = [ind.fitness.values[0] for ind in poblacion]
        maxima, minima = max(aptitudes), min(aptitudes)
        promedio = statistics.fmean(aptitudes)
        desvio = statistics.pstdev(aptitudes)
        salon_fama.update(poblacion)
        mejor_gen = max(poblacion, key=lambda ind: ind.fitness.values[0])

        for ind in poblacion:
            if ind.fitness.values[0] >= APTITUD_MAXIMA:
                resultado.soluciones.setdefault(tuple(ind), generacion)
        if maxima >= APTITUD_MAXIMA and resultado.generacion_convergencia is None:
            resultado.generacion_convergencia = generacion
            resultado.tiempo_convergencia = time.perf_counter() - inicio

        # ProbM con la que se va a generar la próxima generación
        prob_actual = prob_mut.calcular(generacion, promedio, maxima)

        resultado.registros.append({
            "generacion": generacion,
            "aptitud_max": maxima,
            "aptitud_min": minima,
            "aptitud_promedio": round(promedio, 4),
            "desvio": round(desvio, 4),
            "prob_mutacion_actual": round(prob_actual, 4),
            "mejor_individuo_bits": bits_a_texto(mejor_gen),
            "mejor_individuo_decodificado": decodificado_a_texto(mejor_gen),
        })
        if verbose:
            print(f"gen {generacion:4d} | max {maxima:4.0f} | prom {promedio:7.2f} | "
                  f"min {minima:4.0f} | ProbM {prob_actual:.3f}")

        criterio = _verificar_paro(paro, generacion, maxima, promedio, time.perf_counter() - inicio)
        if criterio:
            resultado.criterio_paro = criterio
            break

        # --- Elitismo ---
        elite = []
        for original in tools.selBest(poblacion, n_elite):
            copia = creator.Individual(original)
            copia.fitness.values = original.fitness.values
            elite.append(copia)

        # --- Selección (se clonan los elegidos porque cruza y mutación modifican in situ) ---
        hijos = [creator.Individual(ind) for ind in seleccionar(poblacion, n - n_elite, **params_sel)]

        # --- Cruzamiento: parejas consecutivas, con probabilidad prob_cruza ---
        for i in range(0, len(hijos) - 1, 2):
            if random.random() <= p["prob_cruza"]:
                cruzar(hijos[i], hijos[i + 1], **params_cx)

        # --- Mutación ---
        for ind in hijos:
            mutar(ind, prob_actual)

        for ind in hijos:
            ind.fitness.values = evaluar(ind)

        poblacion = elite + hijos
        generacion += 1

    resultado.tiempo = time.perf_counter() - inicio
    resultado.generaciones = generacion
    resultado.mejor = salon_fama[0]
    return resultado
