"""
Función de aptitud del acertijo (diseño de la entrega parcial).

La aptitud arranca en 0 y:
  +5 por cada condición cumplida (C1..C11, máximo 55),
  -3 por cada restricción violada (R1..R9),
  -10 por cada botella cuyo gen de tamaño vale 111.

Es una función pura: no depende de estado global ni modifica al individuo.
"""
from cromosoma import (
    CANTIDAD_BOTELLAS, TAMANO_ENANO, TAMANO_GIGANTE, TAMANO_INVALIDO,
    VENENO, VINO, AVANZAR, RETROCEDER, decodificar,
)

PUNTOS_CONDICION = 5
PUNTOS_RESTRICCION = -3
PUNTOS_TAMANO_INVALIDO = -10

DESCRIPCION_CONDICIONES = {
    "C1": "No se repiten tamaños entre las botellas (Pista 3)",
    "C2": "Exactamente 3 venenos (enunciado)",
    "C3": "Exactamente 2 vinos de ortiga (enunciado)",
    "C4": "Exactamente 1 poción para avanzar (enunciado)",
    "C5": "Exactamente 1 poción para retroceder (enunciado)",
    "C6": "Todo vino tiene veneno inmediatamente a su izquierda (Pista 1)",
    "C7": "Contenido(B1) != Contenido(B7) (Pista 2)",
    "C8": "La botella de tamaño 1 (enano) no contiene veneno (Pista 3)",
    "C9": "La botella de tamaño 7 (gigante) no contiene veneno (Pista 3)",
    "C10": "Contenido(B2) == Contenido(B6) (Pista 4)",
    "C11": "Tamaño(B2) != Tamaño(B6) (Pista 4)",
}

DESCRIPCION_RESTRICCIONES = {
    "R1": "B1 contiene vino (no puede tener veneno a su izquierda) (Pista 1)",
    "R2": "Algún vino tiene a su izquierda algo que no es veneno (Pista 1)",
    "R3": "B1 es la poción para avanzar (Pista 2)",
    "R4": "B7 es la poción para avanzar (Pista 2)",
    "R5": "Contenido(B1) == Contenido(B7) (Pista 2)",
    "R6": "Alguna botella de tamaño 000 (enano) contiene veneno (Pista 3)",
    "R7": "Alguna botella de tamaño 110 (gigante) contiene veneno (Pista 3)",
    "R8": "Contenido(B2) != Contenido(B6) (Pista 4)",
    "R9": "Tamaño(B2) == Tamaño(B6) (Pista 4)",
}

APTITUD_MAXIMA = PUNTOS_CONDICION * len(DESCRIPCION_CONDICIONES)  # 55


def desglose(individuo):
    """Evalúa todas las condiciones y restricciones.

    Devuelve un dict con:
      condiciones:   {"C1": bool, ...}  True = cumplida
      restricciones: {"R1": bool, ...}  True = violada
      tamanos_invalidos: cantidad de genes de tamaño 111
      aptitud: valor numérico resultante
    """
    tamanos, contenidos = decodificar(individuo)
    b1, b2, b6, b7 = 0, 1, 5, 6  # índices (base 0) de las botellas 1, 2, 6 y 7

    posiciones_vino = [i for i, c in enumerate(contenidos) if c == VINO]
    enanos = [i for i, t in enumerate(tamanos) if t == TAMANO_ENANO]
    gigantes = [i for i, t in enumerate(tamanos) if t == TAMANO_GIGANTE]

    # Pista 1: el vino necesita veneno inmediatamente a la izquierda.
    # Un vino en B1 no tiene botella a su izquierda, así que no la cumple.
    vino_con_veneno_izq = [i > 0 and contenidos[i - 1] == VENENO for i in posiciones_vino]

    condiciones = {
        # C1 (Pista 3: "todas tenemos tamaños diferentes")
        "C1": len(set(tamanos)) == CANTIDAD_BOTELLAS,
        # C2..C5 (cantidades que da el enunciado)
        "C2": contenidos.count(VENENO) == 3,
        "C3": contenidos.count(VINO) == 2,
        "C4": contenidos.count(AVANZAR) == 1,
        "C5": contenidos.count(RETROCEDER) == 1,
        # C6 (Pista 1): se evalúa una sola vez; sin vinos no se cumple.
        "C6": len(posiciones_vino) > 0 and all(vino_con_veneno_izq),
        # C7 (Pista 2: los extremos son diferentes)
        "C7": contenidos[b1] != contenidos[b7],
        # C8 y C9 (Pista 3: ni el enano ni el gigante tienen veneno).
        # Si no existe botella con ese tamaño, la condición no se cumple.
        "C8": len(enanos) > 0 and all(contenidos[i] != VENENO for i in enanos),
        "C9": len(gigantes) > 0 and all(contenidos[i] != VENENO for i in gigantes),
        # C10 y C11 (Pista 4: B2 y B6 "gemelas" en contenido, distintas a la vista)
        "C10": contenidos[b2] == contenidos[b6],
        "C11": tamanos[b2] != tamanos[b6],
    }

    restricciones = {
        # R1, R2 (Pista 1). R2 mira los vinos de B2..B7; el vino en B1 lo penaliza R1.
        "R1": contenidos[b1] == VINO,
        "R2": any(i > 0 and contenidos[i - 1] != VENENO for i in posiciones_vino),
        # R3, R4, R5 (Pista 2)
        "R3": contenidos[b1] == AVANZAR,
        "R4": contenidos[b7] == AVANZAR,
        "R5": contenidos[b1] == contenidos[b7],
        # R6, R7 (Pista 3)
        "R6": any(contenidos[i] == VENENO for i in enanos),
        "R7": any(contenidos[i] == VENENO for i in gigantes),
        # R8, R9 (Pista 4)
        "R8": contenidos[b2] != contenidos[b6],
        "R9": tamanos[b2] == tamanos[b6],
    }

    # Combinación inválida: -10 por cada gen de tamaño 111.
    tamanos_invalidos = tamanos.count(TAMANO_INVALIDO)

    aptitud = (PUNTOS_CONDICION * sum(condiciones.values())
               + PUNTOS_RESTRICCION * sum(restricciones.values())
               + PUNTOS_TAMANO_INVALIDO * tamanos_invalidos)

    return {
        "condiciones": condiciones,
        "restricciones": restricciones,
        "tamanos_invalidos": tamanos_invalidos,
        "aptitud": aptitud,
    }


def evaluar(individuo):
    """Función de aptitud para DEAP: devuelve una tupla (aptitud,)."""
    return (desglose(individuo)["aptitud"],)


def es_solucion(individuo):
    return evaluar(individuo)[0] >= APTITUD_MAXIMA


def desglose_a_texto(individuo):
    d = desglose(individuo)
    lineas = ["Condiciones (+5 c/u):"]
    for clave, ok in d["condiciones"].items():
        lineas.append(f"  [{'X' if ok else ' '}] {clave:<4}{DESCRIPCION_CONDICIONES[clave]}")
    lineas.append("Restricciones violadas (-3 c/u):")
    for clave, violada in d["restricciones"].items():
        lineas.append(f"  [{'X' if violada else ' '}] {clave:<4}{DESCRIPCION_RESTRICCIONES[clave]}")
    lineas.append(f"Genes de tamaño inválidos (111, -10 c/u): {d['tamanos_invalidos']}")
    cumplidas = sum(d["condiciones"].values())
    violadas = sum(d["restricciones"].values())
    lineas.append(f"Aptitud = 5*{cumplidas} - 3*{violadas} - 10*{d['tamanos_invalidos']} = {d['aptitud']}")
    return "\n".join(lineas)
