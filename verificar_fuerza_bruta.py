"""
Verificación por fuerza bruta (sin AG) del acertijo de Snape.

1. Enumera las disposiciones de contenido (permutaciones distintas de
   [V,V,V,W,W,A,R]) que cumplen las pistas 1, 2 y 4 (las que solo hablan de contenido).
2. Para cada una enumera las 7! asignaciones de tamaños y se queda con las que
   cumplen la pista 3 (enano y gigante sin veneno; B2 y B6 de distinto tamaño).
3. Confirma que cada solución obtiene aptitud 55 con nuestra función.
4. Recíproca: recorre TODO el espacio reducido (420 disposiciones x 5040 tamaños)
   y confirma que ningún otro individuo llega a 55. Alcanza con ese espacio porque
   un individuo con algún tamaño 111 pierde 10 puntos (no puede llegar a 55), y C1..C5
   obligan a que los tamaños sean una permutación de 0..6 y los contenidos una
   permutación de [V,V,V,W,W,A,R].

Uso: python verificar_fuerza_bruta.py [--sin-reciproca]
"""
import argparse
import time
from collections import Counter
from itertools import permutations

from aptitud import APTITUD_MAXIMA, evaluar
from cromosoma import (
    AVANZAR, CONTENIDOS_ENUNCIADO, TAMANO_ENANO, TAMANO_GIGANTE, VENENO, VINO,
    ABREVIATURAS_CONTENIDO, codificar,
)


def disposiciones_contenido_todas():
    """Las 420 permutaciones distintas del multiconjunto de contenidos."""
    return sorted(set(permutations(CONTENIDOS_ENUNCIADO)))


def cumple_pistas_contenido(c):
    # Pista 1: todo vino tiene veneno inmediatamente a la izquierda.
    if any(x == VINO and (i == 0 or c[i - 1] != VENENO) for i, x in enumerate(c)):
        return False
    # Pista 2: extremos distintos y ninguno es avanzar.
    if c[0] == c[6] or AVANZAR in (c[0], c[6]):
        return False
    # Pista 4: B2 y B6 con el mismo contenido.
    return c[1] == c[5]


def cumple_pista_tamanos(c, t):
    # Pista 3: ni el enano ni el gigante contienen veneno.
    if c[t.index(TAMANO_ENANO)] == VENENO or c[t.index(TAMANO_GIGANTE)] == VENENO:
        return False
    # Pista 4: B2 y B6 de distinto tamaño (siempre vale en una permutación).
    return t[1] != t[5]


def soluciones_fuerza_bruta():
    """Devuelve (disposiciones_validas, soluciones) donde soluciones es una lista
    de tuplas de 35 bits."""
    disposiciones = [c for c in disposiciones_contenido_todas() if cumple_pistas_contenido(c)]
    tamanos_todos = list(permutations(range(7)))
    soluciones = [tuple(codificar(t, c))
                  for c in disposiciones for t in tamanos_todos
                  if cumple_pista_tamanos(c, t)]
    return disposiciones, soluciones


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sin-reciproca", action="store_true",
                        help="no recorrer el espacio reducido completo (más rápido)")
    args = parser.parse_args()

    t0 = time.perf_counter()
    disposiciones, soluciones = soluciones_fuerza_bruta()
    tiempo_enumeracion = time.perf_counter() - t0

    print(f"Disposiciones de contenido válidas: {len(disposiciones)}")
    for c in disposiciones:
        print("   ", " ".join(ABREVIATURAS_CONTENIDO[x] for x in c),
              f"-> avanzar en botella {c.index(AVANZAR) + 1}")
    print(f"Soluciones completas (con tamaños): {len(soluciones)}")
    print(f"Tiempo de enumeración por fuerza bruta: {tiempo_enumeracion:.3f} s")

    posiciones = Counter(c.index(AVANZAR) + 1 for c in disposiciones)
    print("Posición de 'avanzar' por disposición:", dict(sorted(posiciones.items())))

    malas = [s for s in soluciones if evaluar(list(s))[0] != APTITUD_MAXIMA]
    print(f"Soluciones con aptitud 55 según nuestra función: {len(soluciones) - len(malas)}/{len(soluciones)}")

    if not args.sin_reciproca:
        t0 = time.perf_counter()
        conjunto = set(soluciones)
        con_55 = 0
        falsos_positivos = 0
        tamanos_todos = list(permutations(range(7)))
        for c in disposiciones_contenido_todas():
            for t in tamanos_todos:
                bits = codificar(t, c)
                if evaluar(bits)[0] == APTITUD_MAXIMA:
                    con_55 += 1
                    falsos_positivos += tuple(bits) not in conjunto
        print(f"Recíproca: {con_55} individuos con aptitud 55 en las "
              f"{420 * 5040:,} combinaciones; fuera de las soluciones: {falsos_positivos} "
              f"({time.perf_counter() - t0:.1f} s)")


if __name__ == "__main__":
    main()
