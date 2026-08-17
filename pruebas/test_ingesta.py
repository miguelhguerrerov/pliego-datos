

# --- D-037: proceso_resumen perdia el 14% de los procesos en silencio ------------

def test_el_mes_de_la_fila_es_el_del_archivo():
    """El fallo más caro de los encontrados hasta ahora, y lo destapó un cliente
    preguntando por qué TELCONET mostraba 3 contratos teniendo 724.

    `anio`/`mes` se tomaban de `date`, que es la **última actualización** del proceso, no
    su publicación. El archivo de 2025-04 trae 28.098 filas y 4.060 llevan fecha de otro
    mes. Esas se guardaban bajo su mes futuro y **desaparecían al procesar ese mes**,
    porque `reemplazar` borra por partición y no estaban en ese archivo.

    Resultado: 14% de los procesos perdidos, sin un solo error. Y sistemáticamente los
    que MÁS se habían actualizado — es decir, los adjudicados y contratados, que son
    justo los que importan.

    `hecho_mes` nunca lo sufrió porque agrupa por el mes del archivo, y por eso las dos
    tablas discrepaban: 188.198 procesos contra 156.918."""
    from ingesta import a_proceso_resumen
    from normaliza import MesNormalizado

    m = MesNormalizado(2025, 4, tablas={
        "releases": [
            {"ocid": "a", "date": "2025-04-10T00:00:00", "tag": '["tender"]', "buyer_id": ""},
            # Misma tanda, fecha del futuro: es un proceso que se actualizó después.
            {"ocid": "b", "date": "2026-05-20T00:00:00", "tag": '["award"]', "buyer_id": ""},
        ],
        "tender": [], "planning": [], "awards": [], "suppliers": [],
    })
    filas = a_proceso_resumen(m)
    assert len(filas) == 2
    for f in filas:
        assert (f[2], f[3]) == (2025, 4), (
            f"la fila {f[0]} se guarda bajo {f[2]}-{f[3]:02d} en vez del mes del archivo; "
            f"al procesar ese mes desaparecerá"
        )
    # Y la fecha real se conserva: es lo que se muestra y lo que ordena el radar.
    assert str(filas[1][1]) == "2026-05-20"


# --- D-038: la ventana solo se aplicaba en un sentido ---------------------------

def test_la_poda_calcula_bien_el_limite_de_la_ventana():
    """`_dentro_de_ventana` impedía CARGAR un mes viejo, pero nada borraba los que
    envejecían dentro de la tabla. Con 24 meses no se notó porque el backfill los cargó
    todos de golpe; al bajar a 12, sin poda la tabla se queda igual y el cambio no sirve.

    Una ventana que solo se aplica en un sentido no es una ventana.

    Aquí se comprueba la aritmética del límite, que es donde se rompen estas cuentas: en
    enero hay que cruzar al año anterior."""
    import datetime as dt

    from ingesta import VENTANA_RESUMEN_MESES, _dentro_de_ventana

    hoy = dt.date(2026, 8, 16)
    # El mes en curso y los 11 anteriores entran; el doce se queda fuera.
    assert _dentro_de_ventana(2026, 8, hoy)
    assert _dentro_de_ventana(2025, 9, hoy)
    assert not _dentro_de_ventana(2025, 8, hoy)
    assert VENTANA_RESUMEN_MESES == 12

    # Y cruzando el año, que es donde estas cuentas se rompen.
    enero = dt.date(2026, 1, 10)
    assert _dentro_de_ventana(2025, 2, enero)
    assert not _dentro_de_ventana(2025, 1, enero)


# --- D-040: los criterios de calificación venían en el CSV y nadie los leía -------

def test_se_leen_los_criterios_de_calificacion():
    """Al comparar nuestra ficha con la del portal oficial, la nuestra cuadraba en todo
    lo que mostraba y se dejaba fuera lo que **ya venía en la fuente**.

    `eligibilityCriteria` le dice al oferente que el precio no decide solo, y es el
    complemento directo del benchmark: uno dice a qué precio se adjudica, el otro cuánto
    pesa el precio. Estaba en el CSV desde el primer día."""
    from ingesta import COLUMNAS_RESUMEN, a_proceso_resumen
    from normaliza import MesNormalizado

    m = MesNormalizado(2026, 7, tablas={
        "releases": [{"ocid": "a", "date": "2026-07-13T00:00:00", "tag": '["tender"]',
                      "buyer_id": "EC-RUC-1560002480001-29112"}],
        "tender": [{"ocid": "a", "awardCriteria": "ratedCriteria",
                    "eligibilityCriteria": "Oferta Económica,Participación Ecuatoriana",
                    "mainProcurementCategory": "works", "numberOfTenderers": "2"}],
        "planning": [], "awards": [], "suppliers": [],
    })
    fila = a_proceso_resumen(m)[0]
    assert len(fila) == len(COLUMNAS_RESUMEN), (
        f"{len(fila)} valores contra {len(COLUMNAS_RESUMEN)} columnas"
    )
    d = dict(zip(COLUMNAS_RESUMEN, fila))
    assert d["criterio"] == "ratedCriteria"
    assert "Participación Ecuatoriana" in d["criterios"]
    assert d["tipo_compra"] == "works"
    assert d["n_oferentes"] == 2


def test_un_numero_de_oferentes_vacio_no_revienta():
    """La fuente deja el campo en blanco a menudo. Un `int('')` tumbaría el mes entero."""
    from ingesta import COLUMNAS_RESUMEN, a_proceso_resumen
    from normaliza import MesNormalizado

    m = MesNormalizado(2026, 7, tablas={
        "releases": [{"ocid": "a", "date": "2026-07-13T00:00:00", "tag": '["tender"]', "buyer_id": ""}],
        "tender": [{"ocid": "a", "numberOfTenderers": "", "awardCriteria": ""}],
        "planning": [], "awards": [], "suppliers": [],
    })
    d = dict(zip(COLUMNAS_RESUMEN, a_proceso_resumen(m)[0]))
    assert d["n_oferentes"] is None and d["criterio"] is None
