

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
