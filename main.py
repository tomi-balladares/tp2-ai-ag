"""
Ejecuta las corridas del AG definidas en corridas.yaml.

  python main.py                      # todas las corridas
  python main.py --corrida 3          # solo la corrida 3 (se puede repetir: --corrida 1 --corrida 4)
  python main.py --semillas 30        # además repite cada corrida con 30 semillas y
                                      # reporta tasa de éxito y generación promedio
  python main.py --verbose            # imprime cada generación
"""
import argparse
import statistics
import time

import pandas as pd

from algoritmo import ejecutar_ag
from config import ARCHIVO_CORRIDAS, DIRECTORIO_RESULTADOS, cargar_corridas, resumen_parametros
from reportes import conteo_posicion_avanzar, fila_resumen, grafico_comparativo, guardar_corrida
from verificar_fuerza_bruta import soluciones_fuerza_bruta


def estudio_semillas(corridas, k, salida):
    """Repite cada configuración con k semillas (semilla base, base+1, ...)."""
    filas = []
    for p in corridas:
        exitos, gens, tiempos, soluciones = [], [], [], []
        for i in range(k):
            r = ejecutar_ag(p, semilla=p["semilla"] + i)
            exitos.append(r.generacion_convergencia is not None)
            if r.generacion_convergencia is not None:
                gens.append(r.generacion_convergencia)
            tiempos.append(r.tiempo)
            soluciones.append(len(r.soluciones))
        fila = {
            "corrida": p["nombre"],
            "semillas": k,
            "tasa_exito_%": round(100 * sum(exitos) / k, 1),
            "generacion_promedio_55": round(statistics.fmean(gens), 1) if gens else None,
            "generacion_desvio_55": round(statistics.pstdev(gens), 1) if gens else None,
            "soluciones_distintas_promedio": round(statistics.fmean(soluciones), 1),
            "tiempo_promedio_s": round(statistics.fmean(tiempos), 3),
        }
        filas.append(fila)
        print(f"  {p['nombre']:<42} éxito {fila['tasa_exito_%']:5.1f}%  "
              f"gen. prom. {fila['generacion_promedio_55']}")
    df = pd.DataFrame(filas)
    df.to_csv(salida / "resumen_semillas.csv", index=False)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corrida", type=int, action="append",
                        help="número de corrida (1..N) según corridas.yaml; se puede repetir")
    parser.add_argument("--semillas", type=int, default=0,
                        help="repetir cada corrida con K semillas y reportar la tasa de éxito")
    parser.add_argument("--config", default=str(ARCHIVO_CORRIDAS))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    corridas = cargar_corridas(args.config)
    if args.corrida:
        corridas = [corridas[n - 1] for n in args.corrida]
    salida = DIRECTORIO_RESULTADOS
    salida.mkdir(parents=True, exist_ok=True)

    resultados = []
    for p in corridas:
        print(f"\n=== {p['nombre']} ===\n{resumen_parametros(p)}")
        r = ejecutar_ag(p, verbose=args.verbose)
        guardar_corrida(r, salida / p["nombre"])
        resultados.append(r)
        print(f"Mejor aptitud {r.mejor.fitness.values[0]:.0f} | 1ª gen. con 55: {r.generacion_convergencia} | "
              f"generaciones {r.generaciones} | paro: {r.criterio_paro} | soluciones distintas: "
              f"{len(r.soluciones)} | {r.tiempo:.2f} s")

    resumen = pd.DataFrame([fila_resumen(r) for r in resultados])
    resumen.to_csv(salida / "resumen_corridas.csv", index=False)
    grafico_comparativo(resultados, salida / "comparativo_corridas.png")

    # --- Soluciones halladas por el AG (unión de todas las corridas) vs. fuerza bruta ---
    todas = set()
    for r in resultados:
        todas |= set(r.soluciones)
    conteo = conteo_posicion_avanzar(todas, salida / "conteo_posicion_avanzar.csv",
                                     salida / "conteo_posicion_avanzar.png")

    t0 = time.perf_counter()
    disposiciones, soluciones_fb = soluciones_fuerza_bruta()
    tiempo_fb = time.perf_counter() - t0
    conjunto_fb = set(soluciones_fb)
    fuera = len(todas - conjunto_fb)
    disposiciones_ag = {tuple(b for i, b in enumerate(s) if i % 5 >= 3) for s in todas}
    tiempo_ag = sum(r.tiempo for r in resultados)
    exitosas = [r for r in resultados if r.tiempo_convergencia is not None]

    comparacion = [
        "Comparación AG vs. fuerza bruta",
        "================================",
        f"Fuerza bruta: {len(disposiciones)} disposiciones de contenido, {len(soluciones_fb)} soluciones "
        f"completas, {tiempo_fb:.3f} s",
        f"AG ({len(resultados)} corridas): {len(todas)} soluciones distintas "
        f"({100 * len(todas) / len(soluciones_fb):.2f}% de las {len(soluciones_fb)}), "
        f"{len(disposiciones_ag)} de {len(disposiciones)} disposiciones de contenido, "
        f"tiempo total {tiempo_ag:.2f} s",
        f"Soluciones del AG que NO están en la fuerza bruta: {fuera}",
        "Tiempo promedio del AG hasta su primera solución (corridas exitosas): " + (
            f"{statistics.fmean(r.tiempo_convergencia for r in exitosas):.3f} s" if exitosas else "-"),
        "",
        "Posición de la poción para avanzar en las soluciones del AG:",
        conteo.to_string(index=False),
    ]
    (salida / "comparacion_fuerza_bruta.txt").write_text("\n".join(comparacion) + "\n", encoding="utf-8")
    print("\n" + "\n".join(comparacion))

    if args.semillas and args.semillas > 1:
        print(f"\n=== Estudio con {args.semillas} semillas por corrida ===")
        estudio_semillas(corridas, args.semillas, salida)

    print(f"\nResultados en {salida}")


if __name__ == "__main__":
    main()
