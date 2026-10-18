"""
Cromosoma del acertijo de las pociones de Snape.

El cromosoma es una lista de 35 bits: 7 bloques de 5 bits, uno por botella
(botella 1 a 7, de izquierda a derecha). Cada bloque es [t2 t1 t0 c1 c0]:

  - Tamaño (3 bits, t2 t1 t0):  000 = tamaño 1 (enano) ... 110 = tamaño 7 (gigante).
                                111 = combinación INVÁLIDA (no representa ningún frasco).
  - Contenido (2 bits, c1 c0):  00 = veneno, 01 = vino de ortiga,
                                10 = avanzar, 11 = retroceder.
"""

# --- Dimensiones del cromosoma ---
CANTIDAD_BOTELLAS = 7
BITS_TAMANO = 3
BITS_CONTENIDO = 2
BITS_POR_BOTELLA = BITS_TAMANO + BITS_CONTENIDO        # 5
LARGO_CROMOSOMA = CANTIDAD_BOTELLAS * BITS_POR_BOTELLA  # 35

# --- Códigos de tamaño (valor entero de los 3 bits) ---
TAMANO_ENANO = 0      # 000 -> tamaño 1
TAMANO_GIGANTE = 6    # 110 -> tamaño 7
TAMANO_INVALIDO = 7   # 111 -> no existe

# --- Códigos de contenido (valor entero de los 2 bits) ---
VENENO = 0
VINO = 1
AVANZAR = 2
RETROCEDER = 3

NOMBRES_CONTENIDO = {
    VENENO: "veneno",
    VINO: "vino de ortiga",
    AVANZAR: "avanzar",
    RETROCEDER: "retroceder",
}
ABREVIATURAS_CONTENIDO = {VENENO: "V", VINO: "W", AVANZAR: "A", RETROCEDER: "R"}

# Multiconjunto de contenidos que exige el enunciado (3 V, 2 W, 1 A, 1 R).
CONTENIDOS_ENUNCIADO = [VENENO, VENENO, VENENO, VINO, VINO, AVANZAR, RETROCEDER]


def _bits_a_entero(bits):
    valor = 0
    for b in bits:
        valor = (valor << 1) | int(b)
    return valor


def _entero_a_bits(valor, cantidad_bits):
    return [(valor >> i) & 1 for i in reversed(range(cantidad_bits))]


def decodificar(individuo):
    """Devuelve (tamanos, contenidos): dos listas de 7 enteros.

    tamanos[i] es el código 0..7 de la botella i+1 (7 = inválido);
    contenidos[i] es el código 0..3 de la botella i+1.
    """
    if len(individuo) != LARGO_CROMOSOMA:
        raise ValueError(f"El cromosoma debe tener {LARGO_CROMOSOMA} bits, tiene {len(individuo)}")
    tamanos, contenidos = [], []
    for i in range(CANTIDAD_BOTELLAS):
        bloque = individuo[i * BITS_POR_BOTELLA:(i + 1) * BITS_POR_BOTELLA]
        tamanos.append(_bits_a_entero(bloque[:BITS_TAMANO]))
        contenidos.append(_bits_a_entero(bloque[BITS_TAMANO:]))
    return tamanos, contenidos


def codificar(tamanos, contenidos):
    """Inversa de decodificar(): arma la lista de 35 bits."""
    if len(tamanos) != CANTIDAD_BOTELLAS or len(contenidos) != CANTIDAD_BOTELLAS:
        raise ValueError("Se esperan 7 tamaños y 7 contenidos")
    bits = []
    for t, c in zip(tamanos, contenidos):
        bits += _entero_a_bits(t, BITS_TAMANO) + _entero_a_bits(c, BITS_CONTENIDO)
    return bits


def nombre_tamano(codigo):
    if codigo == TAMANO_INVALIDO:
        return "INVÁLIDO (111)"
    etiqueta = f"{codigo + 1}"
    if codigo == TAMANO_ENANO:
        etiqueta += " (enano)"
    elif codigo == TAMANO_GIGANTE:
        etiqueta += " (gigante)"
    return etiqueta


def bits_a_texto(individuo):
    """'00010 01100 ...' (bloques de 5 bits separados por espacio)."""
    s = "".join(str(int(b)) for b in individuo)
    return " ".join(s[i:i + BITS_POR_BOTELLA] for i in range(0, len(s), BITS_POR_BOTELLA))


def decodificado_a_texto(individuo):
    """Representación compacta: 'B1:t3/V B2:t5/W ...'."""
    tamanos, contenidos = decodificar(individuo)
    partes = []
    for i, (t, c) in enumerate(zip(tamanos, contenidos), start=1):
        t_txt = "X" if t == TAMANO_INVALIDO else str(t + 1)
        partes.append(f"B{i}:t{t_txt}/{ABREVIATURAS_CONTENIDO[c]}")
    return " ".join(partes)


def tabla_individuo(individuo):
    """Tabla de texto Botella | Tamaño | Contenido."""
    tamanos, contenidos = decodificar(individuo)
    filas = [f"{'Botella':<8}| {'Tamaño':<15}| Contenido", "-" * 42]
    for i, (t, c) in enumerate(zip(tamanos, contenidos), start=1):
        filas.append(f"{i:<8}| {nombre_tamano(t):<15}| {NOMBRES_CONTENIDO[c]}")
    return "\n".join(filas)


def imprimir_individuo(individuo):
    print(tabla_individuo(individuo))


def posicion_avanzar(individuo):
    """Posiciones (1..7) de las botellas con la poción para avanzar."""
    _, contenidos = decodificar(individuo)
    return [i + 1 for i, c in enumerate(contenidos) if c == AVANZAR]
