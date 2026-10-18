"""Archivos de salida: logs CSV, gráficos y mejor solución."""
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from aptitud import APTITUD_MAXIMA, desglose_a_texto, es_solucion  # noqa: E402
from config import resumen_parametros  # noqa: E402
from cromosoma import bits_a_texto, decodificado_a_texto, posicion_avanzar, tabla_individuo  # noqa: E402

# Paleta categórica (orden fijo) y tintas de texto
COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
GRILLA = "#e4e3df"

plt.rcParams.update({
    "axes.edgecolor": GRILLA, "axes.labelcolor": TINTA_SECUNDARIA,
    "xtick.color": TINTA_SECUNDARIA, "ytick.color": TINTA_SECUNDARIA,
    "axes.titlecolor": TINTA, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRILLA, "grid.linewidth": 0.8,
    "font.size": 10, "legend.frameon": False,
})


def _linea_objetivo(ax):
    ax.axhline(APTITUD_MAXIMA, color=TINTA_SECUNDARIA, linestyle="--", linewidth=1)
    ax.annotate(f"Aptitud máxima = {APTITUD_MAXIMA}", xy=(1, APTITUD_MAXIMA), xycoords=("axes fraction", "data"),
                xytext=(-4, 4), textcoords="offset points", ha="right", va="bottom",
                color=TINTA_SECUNDARIA, fontsize=9)


def guardar_corrida(resultado, directorio):
    directorio.mkdir(parents=True, exist_ok=True)
    p = resultado.parametros
    df = pd.DataFrame(resultado.registros)
    df.to_csv(directorio / "log.csv", index=False)

    # --- Gráfico de aptitud ---
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for col, etiqueta, color in (("aptitud_max", "Máxima", COLORES[0]),
                                 ("aptitud_promedio", "Promedio", COLORES[1]),
                                 ("aptitud_min", "Mínima", COLORES[2])):
        ax.plot(df["generacion"], df[col], label=etiqueta, color=color, linewidth=2)
    _linea_objetivo(ax)
    ax.set_xlabel("Generación")
    ax.set_ylabel("Aptitud")
    parametros_txt = resumen_parametros(p).replace(" | Cruza", "\nCruza")
    ax.set_title(f"{p['nombre']} (semilla {resultado.semilla})\n{parametros_txt}", fontsize=10, loc="left")
    ax.legend(loc="lower right", ncol=3)
    fig.tight_layout()
    fig.savefig(directorio / "grafico_aptitud.png", dpi=130)
    plt.close(fig)

    # --- Mejor solución ---
    mejor = resultado.mejor
    resuelve = es_solucion(mejor)
    lineas = [
        f"Corrida: {p['nombre']}",
        f"Descripción: {p.get('descripcion', '')}",
        f"Parámetros: {resumen_parametros(p)}",
        f"Semilla: {resultado.semilla}",
        f"Generaciones: {resultado.generaciones} | Criterio de paro: {resultado.criterio_paro} | "
        f"Tiempo: {resultado.tiempo:.2f} s",
        f"Primera generación con aptitud {APTITUD_MAXIMA}: {resultado.generacion_convergencia}",
        "",
        f"Mejor individuo (aptitud {mejor.fitness.values[0]:.0f}):",
        bits_a_texto(mejor),
        "",
        tabla_individuo(mejor),
        "",
        desglose_a_texto(mejor),
        "",
        f"¿Resuelve el acertijo? {'SÍ' if resuelve else 'NO'}",
    ]
    posiciones = posicion_avanzar(mejor)
    if len(posiciones) == 1:
        lineas.append(f"La botella para avanzar es la N°{posiciones[0]}")
    else:
        lineas.append(f"El individuo tiene {len(posiciones)} botellas de avanzar: {posiciones}")
    lineas += ["", f"Soluciones distintas con aptitud {APTITUD_MAXIMA} encontradas: {len(resultado.soluciones)}"]
    (directorio / "mejor_solucion.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    # --- Salón de la fama: todas las soluciones distintas con aptitud 55 ---
    filas = [{
        "bits": bits_a_texto(bits),
        "decodificado": decodificado_a_texto(bits),
        "posicion_avanzar": posicion_avanzar(bits)[0],
        "generacion_hallada": gen,
    } for bits, gen in sorted(resultado.soluciones.items(), key=lambda kv: kv[1])]
    pd.DataFrame(filas, columns=["bits", "decodificado", "posicion_avanzar", "generacion_hallada"]) \
        .to_csv(directorio / "soluciones_55.csv", index=False)


def fila_resumen(resultado):
    p = resultado.parametros
    return {
        "corrida": p["nombre"],
        "descripcion": p.get("descripcion", ""),
        "semilla": resultado.semilla,
        "poblacion": p["tamano_poblacion"],
        "poblacion_inicial": p["poblacion_inicial"],
        "seleccion": p["seleccion"] + (f"({p['tamano_torneo']})" if p["seleccion"] == "torneo" else ""),
        "cruza": p["cruza"],
        "prob_cruza": p["prob_cruza"],
        "mutacion": p["mutacion"],
        "prob_mutacion": p["prob_mutacion"] if p["mutacion"] == "simple" else f"{p['prob_min']}-{p['prob_max']}",
        "elitismo": p.get("elitismo", 0),
        "mejor_aptitud": resultado.mejor.fitness.values[0],
        "generacion_convergencia": resultado.generacion_convergencia,
        "generaciones": resultado.generaciones,
        "aptitud_promedio_final": resultado.registros[-1]["aptitud_promedio"],
        "criterio_paro": resultado.criterio_paro,
        "tiempo_s": round(resultado.tiempo, 3),
        "tiempo_hasta_55_s": None if resultado.tiempo_convergencia is None else round(resultado.tiempo_convergencia, 3),
        "soluciones_distintas": len(resultado.soluciones),
        "posicion_avanzar_mejor": ",".join(map(str, posicion_avanzar(resultado.mejor))),
    }


def grafico_comparativo(resultados, ruta):
    """Aptitud máxima y promedio de todas las corridas superpuestas (dos paneles, mismo eje X)."""
    fig, (ax_max, ax_prom) = plt.subplots(2, 1, figsize=(11, 9), sharex=True)
    for i, r in enumerate(resultados):
        df = pd.DataFrame(r.registros)
        color = COLORES[i % len(COLORES)]
        estilo = "-" if i < len(COLORES) else "--"  # a partir de la 9ª se repite color con línea punteada
        etiqueta = r.parametros["nombre"]
        ax_max.plot(df["generacion"], df["aptitud_max"], color=color, linestyle=estilo, linewidth=1.6, label=etiqueta)
        ax_prom.plot(df["generacion"], df["aptitud_promedio"], color=color, linestyle=estilo, linewidth=1.6)
    for ax, titulo in ((ax_max, "Aptitud máxima por generación"), (ax_prom, "Aptitud promedio por generación")):
        _linea_objetivo(ax)
        ax.set_ylabel("Aptitud")
        ax.set_title(titulo, loc="left", fontsize=11)
    ax_prom.set_xlabel("Generación")
    fig.legend(loc="lower center", ncol=3, fontsize=8.5, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(ruta, dpi=130)
    plt.close(fig)


def conteo_posicion_avanzar(soluciones, ruta_csv, ruta_png):
    """Cuántas soluciones distintas tienen la poción de avanzar en cada posición."""
    conteo = Counter(posicion_avanzar(list(s))[0] for s in soluciones)
    df = pd.DataFrame({"posicion_avanzar": list(range(1, 8)),
                       "soluciones": [conteo.get(i, 0) for i in range(1, 8)]})
    df.to_csv(ruta_csv, index=False)

    fig, ax = plt.subplots(figsize=(7, 4))
    barras = ax.bar(df["posicion_avanzar"], df["soluciones"], color=COLORES[0], width=0.6)
    ax.bar_label(barras, color=TINTA_SECUNDARIA, fontsize=9)
    ax.set_xticks(range(1, 8), [f"B{i}" for i in range(1, 8)])
    ax.set_xlabel("Botella con la poción para avanzar")
    ax.set_ylabel("Soluciones distintas halladas por el AG")
    ax.set_title("Posición de la poción para avanzar (todas las corridas)", loc="left", fontsize=11)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=130)
    plt.close(fig)
    return df
