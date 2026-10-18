"""Carga de la configuración de corridas (corridas.yaml)."""
import copy
from pathlib import Path

import yaml

DIRECTORIO_BASE = Path(__file__).resolve().parent
ARCHIVO_CORRIDAS = DIRECTORIO_BASE / "corridas.yaml"
DIRECTORIO_RESULTADOS = DIRECTORIO_BASE / "resultados"


def _combinar(base, cambios):
    """Combina diccionarios recursivamente (los cambios pisan a la base)."""
    resultado = copy.deepcopy(base)
    for clave, valor in (cambios or {}).items():
        if isinstance(valor, dict) and isinstance(resultado.get(clave), dict):
            resultado[clave] = _combinar(resultado[clave], valor)
        else:
            resultado[clave] = valor
    return resultado


def cargar_corridas(ruta=ARCHIVO_CORRIDAS):
    """Devuelve la lista de corridas con los defaults ya aplicados."""
    with open(ruta, encoding="utf-8") as f:
        datos = yaml.safe_load(f)
    defaults = datos.get("defaults", {})
    return [_combinar(defaults, corrida) for corrida in datos["corridas"]]


def resumen_parametros(p):
    """Texto corto con métodos y parámetros (para títulos de gráficos y resúmenes)."""
    sel = p["seleccion"]
    if sel == "torneo":
        sel += f"({p['tamano_torneo']})"
    elif sel == "ranking":
        sel += f"({p['proporcion_ranking']:.0%})"
    cx = p["cruza"]
    if cx == "multipunto":
        cx += f"({p['puntos_corte']})"
    mut = p["mutacion"]
    if mut == "simple":
        mut += f" {p['prob_mutacion']:.0%}"
    else:
        mut += f" [{p['prob_min']:.0%}-{p['prob_max']:.0%}]"
    texto = (f"Pobl. {p['tamano_poblacion']} ({p['poblacion_inicial']}) | Sel. {sel} | "
             f"Cruza {cx} p={p['prob_cruza']} | Mut. {mut}")
    if p.get("elitismo"):
        texto += f" | Elitismo {p['elitismo']}"
    return texto
