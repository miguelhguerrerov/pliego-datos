"""Las reglas de negocio que viven en el cálculo de agregados.

Están aquí y no en la interfaz para que no se puedan olvidar: excluir los meses sin
cerrar y no publicar con muestra insuficiente son invariantes del producto, no
decisiones de presentación.
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agrega import MESES_SIN_CERRAR, N_MINIMO, calcular, corte_estadistico  # noqa: E402
from ingesta import _dentro_de_ventana, a_hecho_mes  # noqa: E402


def hecho(anio, mes, comp, prov, metodo, n=1, ref=None, adj=None):
    return (anio, mes, comp, prov, metodo, n, ref, adj)


# --- ventana de análisis --------------------------------------------------------

def test_corte_excluye_los_ultimos_cuatro_meses():
    """Un mes tarda 4 o 5 meses en cerrar. Julio de 2026 estaba al 59% en agosto:
    un benchmark calculado sobre él saldría sesgado. Ver docs/decisiones.md D-009."""
    anio, mes = corte_estadistico(dt.date(2026, 8, 14))
    assert (anio, mes) == (2026, 4)
    assert MESES_SIN_CERRAR == 4


def test_proceso_resumen_solo_guarda_la_ventana_del_radar():
    hoy = dt.date(2026, 8, 14)
    assert _dentro_de_ventana(2026, 8, hoy) is True
    assert _dentro_de_ventana(2025, 9, hoy) is True     # 23 meses atrás
    assert _dentro_de_ventana(2024, 8, hoy) is False    # 24 meses: fuera
    assert _dentro_de_ventana(2015, 1, hoy) is False


# --- hecho_mes ------------------------------------------------------------------

def _fila_resumen(**valores):
    """Una tupla de resumen construida DESDE COLUMNAS_RESUMEN, por nombre.

    Construirla a mano con posiciones fijas es exactamente el fallo D-046: al quitar
    `categoria_id` de la tupla real, este fixture siguió probando el layout viejo y
    la prueba paso a fallar por el motivo equivocado. Por nombre, no puede."""
    from ingesta import COLUMNAS_RESUMEN
    return tuple(valores.get(c) for c in COLUMNAS_RESUMEN)


def test_hecho_mes_colapsa_al_grano_minimo():
    """Sin ocid ni objeto: es lo que permite guardar once años sin romper los 500 MB."""
    filas = [
        _fila_resumen(ocid="a", anio=2024, mes=2, estado="cerrado", metodo="Menor Cuantia",
                      comprador_ruc="C1", proveedor_ruc="P1", referencial=100, adjudicado=90),
        _fila_resumen(ocid="b", anio=2024, mes=2, estado="cerrado", metodo="Menor Cuantia",
                      comprador_ruc="C1", proveedor_ruc="P1", referencial=200, adjudicado=180),
        _fila_resumen(ocid="c", anio=2024, mes=2, estado="cerrado", metodo="Licitacion",
                      comprador_ruc="C1", proveedor_ruc="P2", referencial=500, adjudicado=400),
    ]
    hechos = a_hecho_mes(filas, 2024, 2)
    assert len(hechos) == 2
    por_metodo = {h[4]: h for h in hechos}
    assert por_metodo["Menor Cuantia"][5] == 2      # dos procesos agrupados
    assert por_metodo["Menor Cuantia"][6] == 300    # referencial sumado
    assert por_metodo["Menor Cuantia"][7] == 270    # adjudicado sumado


# --- agregados ------------------------------------------------------------------

def test_contrapartes_es_la_tesis_del_producto():
    """Crecer es diversificar compradores: la métrica tiene que contar entidades
    distintas, no procesos. Ver docs/propuesta-valor.md §1."""
    hechos = [
        hecho(2024, 1, "C1", "P1", "m", adj=100),
        hecho(2024, 2, "C2", "P1", "m", adj=100),
        hecho(2024, 3, "C2", "P1", "m", adj=100),   # mismo comprador, no suma contraparte
    ]
    r = {(f[0], f[2]): f for f in calcular(hechos)["entidad_ano"]}
    proveedor = r[("P1", "proveedor")]
    assert proveedor[3] == 300      # monto
    assert proveedor[5] == 2        # dos compradores distintos, no tres procesos


def test_no_se_publica_estadistica_con_muestra_insuficiente():
    """Una mediana sobre tres observaciones es peor que no tener mediana."""
    pocos = [hecho(2024, 1, "C", "P", "Licitacion", ref=100, adj=90) for _ in range(N_MINIMO - 1)]
    assert calcular(pocos)["baja_metodo"] == []

    suficientes = [hecho(2024, 1, "C", "P", "Licitacion", ref=100, adj=90) for _ in range(N_MINIMO)]
    assert len(calcular(suficientes)["baja_metodo"]) == 1


def test_la_baja_excluye_los_meses_sin_cerrar():
    """Meses recientes no entran aunque tengan datos: están a medio llenar."""
    reciente = (dt.date.today().year, dt.date.today().month)
    hechos = [hecho(reciente[0], reciente[1], "C", "P", "Licitacion", ref=100, adj=50)
              for _ in range(20)]
    assert calcular(hechos)["baja_metodo"] == []


def test_la_baja_descarta_ratios_imposibles():
    """Adjudicar por encima del 150% del referencial es error de captura en la fuente."""
    validos = [hecho(2023, 1, "C", "P", "Licitacion", ref=100, adj=90) for _ in range(10)]
    basura = [hecho(2023, 1, "C", "P", "Licitacion", ref=1, adj=99999) for _ in range(10)]
    r = calcular(validos + basura)["baja_metodo"]
    assert len(r) == 1
    assert r[0][2] == 10            # solo los válidos entraron
    assert r[0][3] == 0.9


def test_relacion_alimenta_compradores_huerfanos():
    hechos = [
        hecho(2024, 1, "C1", "P1", "m", n=2, adj=500),
        hecho(2024, 5, "C1", "P1", "m", n=1, adj=300),
        hecho(2024, 1, "C2", "P1", "m", n=1, adj=100),
    ]
    r = {(f[0], f[1]): f for f in calcular(hechos)["relacion"]}
    assert r[("C1", "P1")][3] == 800
    assert r[("C1", "P1")][4] == 3
    assert ("C2", "P1") in r


# --- tabla entidad --------------------------------------------------------------

def test_nombre_canonico_por_moda_no_por_el_ultimo():
    """Los registros antiguos tienen mas erratas: el mas frecuente es mejor criterio.
    Ver docs/decisiones.md D-017."""
    from agrega import construir_entidad

    entidad_ano = [("1791240502001", 2024, "proveedor", 250000, 5, 3)]
    nombres = [
        ("1791240502001", "CEDIMED CIA LTDA", 2),
        ("1791240502001", "CEDIMED CIA. LTDA.", 9),
    ]
    fila = construir_entidad(entidad_ano, nombres)[0]
    assert fila[1] == "CEDIMED CIA. LTDA."


def test_entidad_marca_persona_natural_para_enmascarar():
    """El RUC de persona natural contiene la cedula: la marca decide el
    enmascaramiento. Ver docs/legal.md §1."""
    from agrega import construir_entidad

    filas = {f[0]: f for f in construir_entidad(
        [("1104567890001", 2024, "proveedor", 50000, 2, 1),
         ("1791240502001", 2024, "proveedor", 50000, 2, 1)],
        [])}
    assert filas["1104567890001"][3] is True    # persona natural
    assert filas["1791240502001"][3] is False   # sociedad


def test_tramo_situa_el_segmento_objetivo():
    from agrega import tramo_de

    assert tramo_de(3_000) == "<5K"
    assert tramo_de(250_000) == "100-500K"      # segmento objetivo
    assert tramo_de(1_500_000) == "500K-2M"     # segmento objetivo
    assert tramo_de(50_000_000) == ">10M"


# --- estructura del modulo de clasificacion -------------------------------------

def test_clasifica_expone_sus_funciones():
    """El bloque if __name__ tiene que ser lo ULTIMO del archivo.

    Anadir funciones al final con un append las deja despues del guard: Python
    ejecuta main() antes de definirlas y falla con NameError en produccion, no al
    importar. Paso con fusionar() y asignar_pendientes(). Ver docs/decisiones.md D-023.
    """
    import clasifica

    for nombre in ("construir_taxonomia", "escribir", "fusionar", "asignar_pendientes"):
        assert hasattr(clasifica, nombre), f"clasifica.{nombre} no es alcanzable"

    fuente = Path(clasifica.__file__).read_text(encoding="utf-8")
    assert fuente.rstrip().endswith("raise SystemExit(main())"), (
        "el guard if __name__ no es lo ultimo del archivo: las funciones definidas "
        "despues no existiran cuando main() las llame"
    )


def test_el_tramo_usa_el_ultimo_anio_completo():
    """El anio en curso va a medias: clasificar con el subestima el tamano.

    PLASTILIMPIO facturo 7,28 M en 2025 y aparecia como '500K-2M' por sus 824 mil de
    2026 hasta agosto. El segmento objetivo pasaba de 5.928 empresas a 2.694.
    Ver docs/decisiones.md D-027.
    """
    import datetime as dt

    from agrega import construir_entidad

    en_curso = dt.date.today().year
    filas = {f[0]: f for f in construir_entidad([
        ("1791240502001", en_curso - 1, "proveedor", 7_280_000, 1586, 676),
        ("1791240502001", en_curso,     "proveedor",   824_000,  182, 148),
    ], [])}
    assert filas["1791240502001"][7] == "2-10M", (
        "el tramo debe salir del ultimo anio completo, no del que va a medias"
    )


def test_proveedor_solo_del_anio_en_curso_no_se_queda_sin_tramo():
    """Un proveedor nuevo no tiene anio completo: se usa el que hay, que es mejor que
    dejarlo sin clasificar y fuera de todo segmento."""
    import datetime as dt

    from agrega import construir_entidad

    filas = construir_entidad(
        [("0925051385001", dt.date.today().year, "proveedor", 300_000, 12, 4)], [])
    assert filas[0][7] == "100-500K"


def test_las_filas_de_entidad_calzan_con_sus_columnas():
    """`construir_entidad` devuelve tuplas y `main()` las carga contra una lista de
    nombres de columna escrita aparte. Si una crece y la otra no, el desajuste solo
    aparece al cargar en produccion — y con suerte, porque una tupla mas corta encaja
    igual si las columnas sobrantes admiten nulos."""
    import datetime as dt
    import re
    from pathlib import Path

    from agrega import construir_entidad

    fuente = (Path(__file__).resolve().parents[1] / "src" / "agrega.py").read_text(
        encoding="utf-8")
    bloque = re.search(r'"entidad": \[(.*?)\],\n\s*\}', fuente, re.S)
    assert bloque, "no se encontro la lista de columnas de entidad en agrega.py"
    columnas = re.findall(r'"(\w+)"', bloque.group(1))

    filas = construir_entidad(
        [("0991284214001", dt.date.today().year - 1, "proveedor", 500_000, 20, 8)], [])
    assert len(filas[0]) == len(columnas), (
        f"construir_entidad devuelve {len(filas[0])} valores y se cargan "
        f"{len(columnas)} columnas: {columnas}"
    )


def test_las_cifras_de_cabecera_salen_del_anio_completo():
    """La ficha y el buscador leen estas cifras de `entidad`, no de una vista: el
    calculo al vuelo costaba 0,85 s por ficha y expiraba al ordenar."""
    import datetime as dt

    from agrega import construir_entidad

    completo = dt.date.today().year - 1
    fila = construir_entidad([
        ("1791240502001", completo,     "proveedor", 7_280_000, 1586, 676),
        ("1791240502001", completo + 1, "proveedor",   824_000,  182, 148),
        ("1791240502001", completo - 3, "proveedor", 3_000_000,  900, 400),
    ], [])[0]

    assert fila[7] == "2-10M"          # tramo
    assert fila[8] == completo         # anio_base: el ultimo COMPLETO
    assert float(fila[9]) == 7_280_000  # monto_base, no el del anio a medias
    assert fila[11] == 676             # compradores_base
    assert fila[12] is True            # activo
    assert float(fila[13]) == 11_104_000  # monto_total: los tres anios
    assert fila[15] == completo - 3    # primer_anio
    assert fila[17] == 3               # anios_activo


def test_un_proveedor_nuevo_no_desactiva_a_todos_los_demas():
    """La cohorte de comparación es el último año CERRADO del conjunto. Si se calcula
    después de meter a los proveedores que solo tienen el año en curso, basta uno que
    empezara este año para llevarla a 2026 — y entonces nadie es «activo» y el puesto en
    el tramo desaparece de las 6.539 fichas que lo tenían.

    Las 53 pruebas pasaron con el defecto dentro: ninguna tenía dos proveedores."""
    import datetime as dt

    from agrega import construir_entidad

    en_curso = dt.date.today().year
    filas = {f[0]: f for f in construir_entidad([
        ("0991284214001", en_curso - 1, "proveedor", 20_000_000, 72, 50),
        ("0999999999001", en_curso,     "proveedor",    150_000,  4,  2),   # entró este año
    ], [])}

    assert filas["0991284214001"][12] is True, (
        "un proveedor que empezó este año movió la cohorte al año en curso y dejó "
        "inactivo a quien sí facturó el último año completo"
    )
    assert filas["0999999999001"][12] is False, (
        "el proveedor nuevo no tiene año completo: no puede contar como activo en la "
        "cohorte del último año cerrado"
    )
