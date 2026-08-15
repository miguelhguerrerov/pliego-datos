"""Cálculo de las tablas agregadas.

    python src/agrega.py

Los agregados se recalculan **enteros** desde `hecho_mes`, no de forma incremental:
es más simple, más robusto, y cuesta segundos. Ver docs/agregados.md §3.

Reglas que se aplican aquí y no en la interfaz, para que no se puedan olvidar:

- Las estadísticas de mercado **excluyen los últimos 4 meses** (invariante 10 y D-009):
  un mes tarda 4 o 5 meses en cerrar y un benchmark sobre datos a medio llenar sale
  sesgado sin que nada lo advierta. El radar, en cambio, usa el dato del día.
- Ninguna estadística se publica con `n < 5` (docs/agregados.md §3).
"""

from __future__ import annotations

import argparse
import datetime as dt
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MESES_SIN_CERRAR = 4      # invariante 10
N_MINIMO = 5              # por debajo no se publica nada
VENTANA_RELACION_ANIOS = 3  # segunda válvula de docs/agregados.md §1


def corte_estadistico(hoy: dt.date | None = None) -> tuple[int, int]:
    """Último (anio, mes) que entra en estadísticas de mercado."""
    hoy = hoy or dt.date.today()
    total = hoy.year * 12 + (hoy.month - 1) - MESES_SIN_CERRAR
    return total // 12, total % 12 + 1


def _antes_del_corte(anio: int, mes: int, corte: tuple[int, int]) -> bool:
    return (anio, mes) <= corte


def calcular(hechos: list[tuple]) -> dict[str, list[tuple]]:
    """Recibe filas de hecho_mes y devuelve las tablas agregadas listas para cargar.

    hechos: (anio, mes, comprador_ruc, proveedor_ruc, metodo, n_procesos,
             referencial, adjudicado)
    """
    corte = corte_estadistico()
    anio_min_relacion = corte[0] - VENTANA_RELACION_ANIOS + 1

    monto_ent: dict[tuple, float] = defaultdict(float)
    proc_ent: dict[tuple, int] = defaultdict(int)
    contrapartes: dict[tuple, set] = defaultdict(set)
    relacion: dict[tuple, list] = defaultdict(lambda: [0.0, 0])
    ratios: dict[tuple, list] = defaultdict(list)

    for anio, mes, comprador, proveedor, metodo, n, ref, adj in hechos:
        adj = float(adj or 0)
        n = int(n or 0)

        if comprador:
            monto_ent[(comprador, anio, "comprador")] += adj
            proc_ent[(comprador, anio, "comprador")] += n
            if proveedor:
                contrapartes[(comprador, anio, "comprador")].add(proveedor)
        if proveedor:
            monto_ent[(proveedor, anio, "proveedor")] += adj
            proc_ent[(proveedor, anio, "proveedor")] += n
            if comprador:
                contrapartes[(proveedor, anio, "proveedor")].add(comprador)

        if comprador and proveedor and anio >= anio_min_relacion:
            r = relacion[(comprador, proveedor, anio)]
            r[0] += adj
            r[1] += n

        # El ratio de baja solo tiene sentido con ambas cifras y sobre meses cerrados.
        if metodo and ref and adj and _antes_del_corte(anio, mes, corte):
            cociente = adj / float(ref)
            if 0 < cociente <= 1.5:      # por encima es error de captura en la fuente
                ratios[(metodo, anio)].append(cociente)

    salida: dict[str, list[tuple]] = {}

    salida["entidad_ano"] = [
        (ruc, anio, rol, round(monto_ent[(ruc, anio, rol)], 2),
         proc_ent[(ruc, anio, rol)], len(contrapartes[(ruc, anio, rol)]))
        for (ruc, anio, rol) in monto_ent
    ]

    salida["relacion"] = [
        (c, p, a, round(v[0], 2), v[1]) for (c, p, a), v in relacion.items()
    ]

    baja = []
    for (metodo, anio), valores in ratios.items():
        if len(valores) < N_MINIMO:
            continue          # no se publica nada con muestra insuficiente
        valores.sort()
        baja.append((
            metodo, anio, len(valores),
            round(statistics.median(valores), 4),
            round(valores[len(valores) // 4], 4),
            round(valores[3 * len(valores) // 4], 4),
        ))
    salida["baja_metodo"] = baja

    return salida


TRAMOS = (
    ("<5K", 0, 5_000), ("5-25K", 5_000, 25_000), ("25-100K", 25_000, 100_000),
    ("100-500K", 100_000, 500_000), ("500K-2M", 500_000, 2_000_000),
    ("2-10M", 2_000_000, 10_000_000), (">10M", 10_000_000, float("inf")),
)


def tramo_de(monto: float) -> str:
    """El tramo del ultimo anio con actividad. El segmento objetivo es 100K-2M:
    6.697 empresas, el 40,2% del monto. Ver docs/decisiones.md D-004."""
    for etiqueta, bajo, alto in TRAMOS:
        if bajo <= monto < alto:
            return etiqueta
    return ">10M"


def construir_entidad(entidad_ano: list[tuple], nombres: list[tuple]) -> list[tuple]:
    """Arma la tabla entidad a partir de los agregados y las grafias vistas.

    - nombre por MODA, no por el ultimo visto (los registros antiguos tienen mas erratas)
    - tipo segun aparezca como comprador, proveedor o ambos
    - persona natural y provincia derivados del propio RUC
    - tramo y cifras de cabecera sobre el ultimo anio COMPLETO de cada uno

    **Las cifras de cabecera viven aqui y no en una vista.** La primera version las
    calculaba en `v_proveedor` con ventanas sobre las 264.276 filas de `entidad_ano`:
    salia a 0,85 s por ficha, y ordenar por monto —lo que necesita el buscador— daba
    directamente «canceling statement due to statement timeout». Precalcularlas cuesta
    unos 2 MB del presupuesto de 460 y las deja indexables. Es la misma regla de siempre:
    los agregados se calculan una vez y la aplicacion los lee.
    """
    from entidades import es_entidad_publica, es_persona_natural, provincia_de_ruc

    mejor: dict[str, tuple[int, str]] = {}
    for ruc, nombre, n in nombres:
        if ruc not in mejor or n > mejor[ruc][0]:
            mejor[ruc] = (n, nombre)

    # El anio en curso va a medias: clasificar el tamano de una empresa con el la
    # subestima. PLASTILIMPIO facturo 7,28 M en 2025 y aparecia como "500K-2M" por sus
    # 824 mil de 2026; el segmento objetivo pasaba de 5.928 empresas a 2.694. Ver D-027.
    anio_en_curso = dt.date.today().year

    roles: dict[str, set] = {}
    base: dict[str, tuple] = {}        # ultimo anio completo de cada uno
    respaldo: dict[str, tuple] = {}    # solo si no tiene ningun anio completo
    historico: dict[str, list] = {}    # [monto, procesos, primer_anio, ultimo, n_anios]
    for ruc, anio, rol, monto, n_proc, n_contra in entidad_ano:
        roles.setdefault(ruc, set()).add(rol)
        if rol != "proveedor":
            continue

        h = historico.setdefault(ruc, [0.0, 0, anio, anio, 0])
        h[0] += float(monto)
        h[1] += int(n_proc or 0)
        h[2] = min(h[2], anio)
        h[3] = max(h[3], anio)
        h[4] += 1

        fila = (anio, float(monto), int(n_proc or 0), int(n_contra or 0))
        destino = base if anio < anio_en_curso else respaldo
        if ruc not in destino or anio > destino[ruc][0]:
            destino[ruc] = fila
    # La cohorte de comparacion del buscador y de la ficha: el ultimo anio CERRADO del
    # conjunto. Quien no llega a el sigue teniendo cifras, pero marcadas como viejas.
    #
    # Se calcula ANTES de mezclar `respaldo`. Calcularlo despues lo llevaba al anio en
    # curso —basta un proveedor que empezara este anio— y entonces nadie era «activo»:
    # el puesto en el tramo desaparecia de las 6.539 fichas que lo tenian.
    anio_cohorte = max((b[0] for b in base.values()), default=anio_en_curso - 1)

    for ruc, fila in respaldo.items():
        base.setdefault(ruc, fila)     # proveedor nuevo: no hay anio completo todavia

    filas = []
    for ruc, rs in roles.items():
        tipo = "ambos" if len(rs) > 1 else next(iter(rs))
        es_prov = tipo in ("proveedor", "ambos")
        anio_b, monto_b, proc_b, comp_b = base.get(ruc, (None, 0.0, 0, 0))
        h = historico.get(ruc)
        filas.append((
            ruc,
            mejor.get(ruc, (0, ruc))[1],
            tipo,
            es_persona_natural(ruc),
            es_entidad_publica(ruc),
            provincia_de_ruc(ruc),
            None,                                        # canton: falta en la fuente CSV
            tramo_de(monto_b) if es_prov else None,
            anio_b,
            round(monto_b, 2) if es_prov else None,
            proc_b if es_prov else None,
            comp_b if es_prov else None,
            anio_b == anio_cohorte if es_prov else None,
            round(h[0], 2) if h else None,
            h[1] if h else None,
            h[2] if h else None,
            h[3] if h else None,
            h[4] if h else None,
        ))
    return filas


def main() -> int:
    p = argparse.ArgumentParser(description="Recalcula las tablas agregadas")
    p.add_argument("--seco", action="store_true", help="calcula y muestra, sin escribir")
    args = p.parse_args()

    from carga import conexion, reemplazar, verificar_presupuesto

    with conexion() as con:
        with con.cursor() as cur:
            cur.execute("""
                select anio, mes, comprador_ruc, proveedor_ruc, metodo,
                       n_procesos, referencial, adjudicado
                from hecho_mes
            """)
            hechos = cur.fetchall()
        print(f"hechos leídos: {len(hechos):,}")

        with con.cursor() as cur:
            cur.execute("select ruc, nombre, n from entidad_nombre")
            nombres = cur.fetchall()
        print(f"grafias de entidad: {len(nombres):,}")

        tablas = calcular(hechos)
        tablas["entidad"] = construir_entidad(tablas["entidad_ano"], nombres)
        corte = corte_estadistico()
        print(f"corte estadístico: hasta {corte[0]}-{corte[1]:02d} "
              f"(se excluyen los últimos {MESES_SIN_CERRAR} meses)")
        for nombre, filas in tablas.items():
            print(f"  {nombre:<14} {len(filas):>8,} filas")

        if args.seco:
            for metodo, anio, n, med, p25, p75 in sorted(tablas["baja_metodo"], key=lambda r: -r[2])[:8]:
                print(f"    {anio} {metodo[:38]:<38} mediana {med}  n={n:,}")
            return 0

        columnas = {
            "entidad_ano": ["ruc", "anio", "rol", "monto", "n_procesos", "n_contrapartes"],
            "relacion": ["comprador_ruc", "proveedor_ruc", "anio", "monto", "n_procesos"],
            "baja_metodo": ["metodo", "anio", "n", "ratio_mediana", "ratio_p25", "ratio_p75"],
            "entidad": ["ruc", "nombre", "tipo", "es_persona_natural", "es_publica",
                        "provincia", "canton", "tramo",
                        "anio_base", "monto_base", "procesos_base", "compradores_base",
                        "activo", "monto_total", "procesos_total", "primer_anio",
                        "ultimo_anio", "anios_activo"],
        }
        # entidad primero: las demas no la referencian, pero el orden hace el log legible.
        for nombre, filas in tablas.items():
            reemplazar(con, nombre, columnas[nombre], filas)
        con.commit()

        mb = verificar_presupuesto(con)
        print(f"base: {mb} MB de 460 presupuestados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
