# Acertijo de las pociones de Snape con Algoritmos Genéticos

TP2 de Inteligencia Artificial (UTN FRBA, Ing. en Sistemas, 2026) — Grupo 13.
Implementación en Python + DEAP del diseño aprobado en la entrega parcial.

## Cómo correr

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python verificar_fuerza_bruta.py        # enumeración sin AG (≈25 s con la verificación recíproca)
python -m pytest -q tests               # tests
python main.py                          # todas las corridas de corridas.yaml
python main.py --corrida 4 --verbose    # una corrida, mostrando cada generación
python main.py --semillas 30            # además repite cada corrida con 30 semillas
```

## Módulos

| Archivo | Contenido |
|---|---|
| `cromosoma.py` | Constantes (35 bits = 7 bloques `[t2 t1 t0 c1 c0]`), `decodificar` / `codificar`, impresión de individuos. |
| `aptitud.py` | `evaluar(individuo) -> (aptitud,)` y `desglose(individuo)` con las condiciones C1–C11 (+5), las restricciones R1–R9 (−3) y los genes de tamaño 111 (−10). Cada una está documentada con su número de pista. |
| `operadores.py` | Población inicial, selección, cruza y mutación (ver tabla siguiente). |
| `algoritmo.py` | Bucle evolutivo propio: logueo por generación, mutación adaptativa, elitismo, criterios de paro combinados y salón de la fama con todas las soluciones de aptitud 55. |
| `config.py` + `corridas.yaml` | Parámetros por defecto y definición de las corridas (semilla fija). |
| `reportes.py` | CSV, gráficos y `mejor_solucion.txt`. |
| `main.py` | Ejecuta las corridas y genera las salidas globales. |
| `verificar_fuerza_bruta.py` | Enumera todas las soluciones por permutaciones y las valida con nuestra función de aptitud. |
| `tests/` | Tests con pytest. |

## Mapeo a la teoría

| Teoría | Nombre en `corridas.yaml` | Implementación |
|---|---|---|
| Población inicial al azar | `poblacion_inicial: azar` | Cada bit con p = 0,5. |
| Población inicial ad hoc | `ad_hoc` | Contenidos = permutación de [V,V,V,W,W,A,R], tamaños = permutación de 0..6. |
| Selección por torneo | `seleccion: torneo` | `tools.selTournament` de DEAP (`tamano_torneo`). |
| Selección por ranking | `ranking` | Se ordena por aptitud, se toma el `proporcion_ranking` mejor y se copia hasta completar la población. |
| Selección por ruleta | `ruleta` | Aptitudes desplazadas: `a − min + ε` (la aptitud puede ser negativa). |
| Control sobre número esperado | `control_numero_esperado` | `esperado = a / promedio` (aptitudes desplazadas); la parte entera son copias directas y el resto se completa con ruleta sobre las partes decimales. |
| Cruza simple | `cruza: simple` | Un punto de corte. |
| Cruza multipunto | `multipunto` | `puntos_corte` cortes, tramos alternados. |
| Binomial con máscara complemento | `binomial_mascara_complemento` | Máscara fija `mascara` (1 = padre X); el hijo B usa el complemento. |
| Binomial con máscara doble | `binomial_mascara_doble` | Dos máscaras independientes (`mascara_a`, `mascara_b`; `null` = se sortea cada vez). |
| Binomial al azar | `binomial_azar` | Por gen: R ≤ 0,5 → padre X, si no padre Y (sorteos independientes para cada hijo). |
| Mutación simple | `mutacion: simple` | Por individuo: si RandomM ≤ ProbM se invierte UN bit al azar. |
| Mutación adaptativa por convergencia | `adaptativa_convergencia` | `ProbM = pmin + (pmax − pmin) · max(cercanía, estancamiento)`, con `cercanía = clip(promedio / máximo, 0, 1)` y `estancamiento = min(1, gens_sin_mejora_del_promedio / ventana)`. |
| Mutación por temperatura ascendente | `adaptativa_temperatura_ascendente` | `ProbM = pmin + (pmax − pmin) · g / G` |
| Mutación por temperatura descendente | `adaptativa_temperatura_descendente` | `ProbM = pmax − (pmax − pmin) · g / G` |
| Elitismo | `elitismo: N` | Los N mejores pasan sin cambios (0 = desactivado). |
| Criterios de paro | `paro:` | Máximo de generaciones, aptitud máxima ≥ 55 (`parar_en_aptitud_maxima`), promedio ≈ valor (`promedio_objetivo` ± `tolerancia_promedio`) y tiempo máximo. Se registra cuál cortó la corrida. |

## Salidas (`resultados/`)

Por corrida (`resultados/<nombre_corrida>/`): `log.csv` (una fila por generación), `grafico_aptitud.png`,
`mejor_solucion.txt` (tabla, desglose, si resuelve y en qué botella está la poción para avanzar) y
`soluciones_55.csv` (todas las soluciones distintas con aptitud 55 y la generación en que aparecieron).

Globales: `resumen_corridas.csv`, `comparativo_corridas.png`, `conteo_posicion_avanzar.csv/.png`,
`comparacion_fuerza_bruta.txt` y, con `--semillas K`, `resumen_semillas.csv` (tasa de éxito y generación promedio
en que se alcanza 55).

## Validación por fuerza bruta

8 disposiciones de contenido válidas, 11.520 soluciones completas (8 × 4·3 ubicaciones para enano y
gigante × 5! para el resto de los tamaños); la poción para avanzar solo puede estar en las botellas 3, 4 o 5.
Las 11.520 obtienen aptitud 55 y, recorriendo las 420 × 5040 combinaciones de contenidos y tamaños, ningún otro
individuo llega a 55 (un gen 111 resta 10, así que no hace falta recorrer el resto del espacio de 2³⁵).
