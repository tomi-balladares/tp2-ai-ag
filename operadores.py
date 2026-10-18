"""
Operadores genéticos según la teoría de la cátedra.

Todos usan el módulo `random` (sembrado por el algoritmo) para que las corridas
sean reproducibles. Los individuos son listas de 35 bits con atributo `fitness`
(DEAP); los operadores de cruza y mutación modifican los individuos in situ.
"""
import random

from deap import tools

from cromosoma import (
    CANTIDAD_BOTELLAS, CONTENIDOS_ENUNCIADO,
    LARGO_CROMOSOMA, codificar,
)

EPSILON = 1e-6


# =============================================================================
# Población inicial
# =============================================================================

def individuo_azar():
    """Cada uno de los 35 bits se sortea con probabilidad 0.5."""
    return [random.randint(0, 1) for _ in range(LARGO_CROMOSOMA)]


def individuo_ad_hoc():
    """Contenidos = permutación de [V,V,V,W,W,A,R]; tamaños = permutación de 0..6.
    Arranca ya cumpliendo C1..C5 y sin genes 111."""
    contenidos = CONTENIDOS_ENUNCIADO[:]
    random.shuffle(contenidos)
    tamanos = random.sample(range(CANTIDAD_BOTELLAS), CANTIDAD_BOTELLAS)
    return codificar(tamanos, contenidos)


GENERADORES_POBLACION = {
    "azar": individuo_azar,
    "ad_hoc": individuo_ad_hoc,
}


# =============================================================================
# Selección: sel(poblacion, k, **parametros) -> lista de k individuos (sin clonar)
# =============================================================================

def _aptitudes(poblacion):
    return [ind.fitness.values[0] for ind in poblacion]


def aptitudes_desplazadas(aptitudes):
    """La aptitud puede ser negativa: se resta el mínimo de la generación y se suma
    epsilon, para que todas sean > 0 y se puedan usar como proporciones."""
    minimo = min(aptitudes)
    return [a - minimo + EPSILON for a in aptitudes]


def seleccion_torneo(poblacion, k, tamano_torneo=3):
    """Torneo: se eligen `tamano_torneo` individuos al azar y gana el de mayor aptitud.
    (Equivale a tools.selTournament de DEAP.)"""
    return tools.selTournament(poblacion, k, tournsize=tamano_torneo)


def seleccion_ranking(poblacion, k, proporcion_ranking=0.5):
    """Ranking: se ordena por aptitud y se toman los mejores (proporción configurable).
    Como esto solo reduce la población, se completan los k lugares copiando a los
    seleccionados en orden de ranking (reemplazo/copias)."""
    ordenada = sorted(poblacion, key=lambda ind: ind.fitness.values[0], reverse=True)
    cantidad_mejores = max(1, int(round(len(poblacion) * proporcion_ranking)))
    mejores = ordenada[:cantidad_mejores]
    return [mejores[i % cantidad_mejores] for i in range(k)]


def _ruleta_indices(pesos, k):
    """Gira la ruleta k veces sobre `pesos` (todos >= 0) y devuelve índices."""
    total = sum(pesos)
    acumulados = []
    acum = 0.0
    for p in pesos:
        acum += p
        acumulados.append(acum)
    indices = []
    for _ in range(k):
        r = random.random() * total
        # búsqueda lineal: la población es chica
        for i, a in enumerate(acumulados):
            if r <= a:
                indices.append(i)
                break
        else:
            indices.append(len(pesos) - 1)
    return indices


def seleccion_ruleta(poblacion, k):
    """Ruleta: probabilidad proporcional a la aptitud desplazada (min + epsilon)."""
    pesos = aptitudes_desplazadas(_aptitudes(poblacion))
    return [poblacion[i] for i in _ruleta_indices(pesos, k)]


def seleccion_control_numero_esperado(poblacion, k):
    """Control sobre número esperado:
      a) esperado_i = aptitud_i / aptitud_promedio (con aptitudes desplazadas a positivas);
         la parte entera de esperado_i es la cantidad de copias directas.
      b) los lugares que faltan se completan con una ruleta sobre las partes decimales.
    """
    desplazadas = aptitudes_desplazadas(_aptitudes(poblacion))
    promedio = sum(desplazadas) / len(desplazadas)
    # Escala k/N por si se pide un k distinto al tamaño de la población (p. ej. con elitismo)
    esperados = [a / promedio * k / len(poblacion) for a in desplazadas]

    # (+1e-6 evita que 1.9999999 por redondeo se cuente como 1 copia)
    enteros = [int(e + 1e-6) for e in esperados]
    seleccionados = []
    for ind, copias in zip(poblacion, enteros):
        seleccionados += [ind] * copias
    seleccionados = seleccionados[:k]

    faltantes = k - len(seleccionados)
    if faltantes > 0:
        decimales = [max(0.0, e - c) for e, c in zip(esperados, enteros)]
        if sum(decimales) <= 0:
            decimales = [1.0] * len(poblacion)
        seleccionados += [poblacion[i] for i in _ruleta_indices(decimales, faltantes)]
    return seleccionados


METODOS_SELECCION = {
    "torneo": seleccion_torneo,
    "ranking": seleccion_ranking,
    "ruleta": seleccion_ruleta,
    "control_numero_esperado": seleccion_control_numero_esperado,
}


# =============================================================================
# Cruzamiento: cx(padre_x, padre_y, **parametros) -> (hijo_a, hijo_b) in situ
# =============================================================================

def _aplicar_mascara(padre_x, padre_y, mascara):
    """Gen i del hijo: padre X si mascara[i] == 1, padre Y si es 0."""
    return [x if m else y for x, y, m in zip(padre_x, padre_y, mascara)]


def _reemplazar(ind, genes):
    ind[:] = genes
    return ind


def cruza_simple(padre_x, padre_y):
    """Un punto de corte al azar (1..n-1); se intercambian las colas."""
    corte = random.randint(1, len(padre_x) - 1)
    hijo_a = padre_x[:corte] + padre_y[corte:]
    hijo_b = padre_y[:corte] + padre_x[corte:]
    return _reemplazar(padre_x, hijo_a), _reemplazar(padre_y, hijo_b)


def cruza_multipunto(padre_x, padre_y, puntos_corte=2):
    """`puntos_corte` cortes distintos; los tramos se alternan entre padres."""
    n = len(padre_x)
    cortes = sorted(random.sample(range(1, n), puntos_corte))
    mascara = []
    de_x = 1
    previo = 0
    for corte in cortes + [n]:
        mascara += [de_x] * (corte - previo)
        de_x = 1 - de_x
        previo = corte
    return cruza_binomial_mascara_complemento(padre_x, padre_y, mascara=mascara)


def mascara_por_texto(texto):
    """'11111 00000 ...' -> lista de 35 bits (ignora espacios)."""
    bits = [int(ch) for ch in str(texto) if ch in "01"]
    if len(bits) != LARGO_CROMOSOMA:
        raise ValueError(f"La máscara debe tener {LARGO_CROMOSOMA} bits, tiene {len(bits)}")
    return bits


def mascara_azar():
    return [random.randint(0, 1) for _ in range(LARGO_CROMOSOMA)]


def cruza_binomial_mascara_complemento(padre_x, padre_y, mascara=None):
    """Máscara fija (configurable): hijo A toma de X donde la máscara es 1 y de Y
    donde es 0; el hijo B usa la máscara complemento. Si no se pasa máscara se
    sortea una por cruza."""
    if mascara is None:
        mascara = mascara_azar()
    elif isinstance(mascara, str):
        mascara = mascara_por_texto(mascara)
    complemento = [1 - m for m in mascara]
    hijo_a = _aplicar_mascara(padre_x, padre_y, mascara)
    hijo_b = _aplicar_mascara(padre_x, padre_y, complemento)
    return _reemplazar(padre_x, hijo_a), _reemplazar(padre_y, hijo_b)


def cruza_binomial_mascara_doble(padre_x, padre_y, mascara_a=None, mascara_b=None):
    """Dos máscaras independientes, una por hijo (cada una se sortea por cruza si
    no se configura una fija)."""
    mascara_a = mascara_por_texto(mascara_a) if isinstance(mascara_a, str) else (mascara_a or mascara_azar())
    mascara_b = mascara_por_texto(mascara_b) if isinstance(mascara_b, str) else (mascara_b or mascara_azar())
    hijo_a = _aplicar_mascara(padre_x, padre_y, mascara_a)
    hijo_b = _aplicar_mascara(padre_x, padre_y, mascara_b)
    return _reemplazar(padre_x, hijo_a), _reemplazar(padre_y, hijo_b)


def cruza_binomial_azar(padre_x, padre_y):
    """Para cada gen de cada hijo se sortea R: si R <= 0.5 el gen viene del padre X,
    si no del padre Y. Los sorteos de los dos hijos son independientes."""
    hijo_a = [x if random.random() <= 0.5 else y for x, y in zip(padre_x, padre_y)]
    hijo_b = [x if random.random() <= 0.5 else y for x, y in zip(padre_x, padre_y)]
    return _reemplazar(padre_x, hijo_a), _reemplazar(padre_y, hijo_b)


METODOS_CRUZA = {
    "simple": cruza_simple,
    "multipunto": cruza_multipunto,
    "binomial_mascara_complemento": cruza_binomial_mascara_complemento,
    "binomial_mascara_doble": cruza_binomial_mascara_doble,
    "binomial_azar": cruza_binomial_azar,
}


# =============================================================================
# Mutación
# =============================================================================

def mutar(individuo, prob_mutacion):
    """Mutación de la teoría: se sortea RandomM; si RandomM <= ProbM se invierte
    UN bit elegido al azar. Devuelve True si mutó."""
    if random.random() <= prob_mutacion:
        i = random.randrange(len(individuo))
        individuo[i] = 1 - individuo[i]
        return True
    return False


class ProbabilidadMutacion:
    """Calcula ProbM para cada generación según el método configurado.

    - simple:  ProbM = prob_mutacion (constante).
    - adaptativa_convergencia:
          cercania       = clip(promedio / maximo, 0, 1)        (0 si maximo <= 0)
          estancamiento  = min(1, generaciones_sin_mejora / ventana)
          ProbM = prob_min + (prob_max - prob_min) * max(cercania, estancamiento)
        donde "generaciones_sin_mejora" cuenta generaciones seguidas en que el
        promedio no mejoró más de `tolerancia_estancamiento` respecto del mejor
        promedio visto. Cuando la población converge (promedio ≈ máximo) o se
        estanca, sube la mutación para recuperar diversidad.
    - adaptativa_temperatura_ascendente:
          ProbM = prob_min + (prob_max - prob_min) * g / G
    - adaptativa_temperatura_descendente:
          ProbM = prob_max - (prob_max - prob_min) * g / G
      con g = generación actual y G = máximo de generaciones.
    """

    METODOS = ("simple", "adaptativa_convergencia",
               "adaptativa_temperatura_ascendente", "adaptativa_temperatura_descendente")

    def __init__(self, metodo="simple", prob_mutacion=0.01, prob_min=0.01, prob_max=0.30,
                 ventana=10, tolerancia_estancamiento=0.1, max_generaciones=100):
        if metodo not in self.METODOS:
            raise ValueError(f"Método de mutación desconocido: {metodo}")
        self.metodo = metodo
        self.prob_mutacion = prob_mutacion
        self.prob_min = prob_min
        self.prob_max = prob_max
        self.ventana = ventana
        self.tolerancia = tolerancia_estancamiento
        self.max_generaciones = max(1, max_generaciones)
        self._mejor_promedio = None
        self._sin_mejora = 0

    def calcular(self, generacion, aptitud_promedio, aptitud_maxima):
        if self.metodo == "simple":
            return self.prob_mutacion

        if self.metodo == "adaptativa_convergencia":
            if self._mejor_promedio is None or aptitud_promedio > self._mejor_promedio + self.tolerancia:
                self._mejor_promedio = aptitud_promedio
                self._sin_mejora = 0
            else:
                self._sin_mejora += 1
            cercania = min(1.0, max(0.0, aptitud_promedio / aptitud_maxima)) if aptitud_maxima > 0 else 0.0
            estancamiento = min(1.0, self._sin_mejora / self.ventana)
            return self.prob_min + (self.prob_max - self.prob_min) * max(cercania, estancamiento)

        fraccion = min(1.0, generacion / self.max_generaciones)
        if self.metodo == "adaptativa_temperatura_ascendente":
            return self.prob_min + (self.prob_max - self.prob_min) * fraccion
        return self.prob_max - (self.prob_max - self.prob_min) * fraccion
