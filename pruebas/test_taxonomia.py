"""La taxonomía sale del CPC, y los nombres se comprueban antes de publicarse.

Cada prueba de aquí corresponde a un defecto real de la taxonomía anterior, medido sobre
las 242 categorías que llegaron a producción. Ver docs/decisiones.md D-030.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from taxonomia import (  # noqa: E402
    _clave_normalizada,
    agrupar_items,
    cpc_dominante,
    grupo_de,
    nombre_de_respaldo,
    resolver_nombres,
    validar_nombre,
)


# --- el nivel de agrupación -----------------------------------------------------

def test_la_subclase_agrupa_los_codigos_de_la_misma_familia():
    """Medido contra la fuente: los códigos van de 8 a 12 dígitos y los 5 primeros son
    la subclase CPC. `3526000506` y `352600511` son dos presentaciones de medicamento."""
    assert grupo_de("3526000506") == "35260"
    assert grupo_de("352600511") == "35260"
    assert grupo_de("87141001") == "87141"


def test_un_codigo_inservible_no_inventa_grupo():
    for malo in (None, "", "  ", "AB", "7"):
        assert grupo_de(malo) is None, f"{malo!r} no debería dar grupo"


def test_el_codigo_llega_a_veces_como_numero():
    """Ya pasó con `planning.budget.id` y costó un mes entero de publicación (D-028).
    La fuente no promete el tipo de sus identificadores."""
    assert grupo_de(3526000506) == "35260"


# --- qué compra realmente un proceso --------------------------------------------

def test_el_cpc_del_proceso_es_el_que_concentra_el_monto():
    """Cien líneas de clips no convierten en papelería una compra de computadoras.
    Por número de líneas ganaría el clip; por monto gana lo que se compró."""
    items = (
        [{"ocid": "a", "origen": "award", "cpc": "45281", "cantidad": 5,
          "precio_unitario": 900}]
        + [{"ocid": "a", "origen": "award", "cpc": "38912", "cantidad": 1,
            "precio_unitario": 0.5}] * 100
    )
    assert cpc_dominante(items)["a"][0] == "45281"


def test_manda_lo_adjudicado_sobre_lo_convocado():
    """Los ítems de `award` son los que de verdad se compraron; los de `tender`, lo que
    se pidió. Cuando hay ambos, los de tender ni se miran."""
    items = [
        {"ocid": "a", "origen": "tender", "cpc": "35260", "cantidad": 100,
         "precio_unitario": 100},
        {"ocid": "a", "origen": "award", "cpc": "87141", "cantidad": 1,
         "precio_unitario": 10},
    ]
    assert cpc_dominante(items)["a"][0] == "87141"


def test_un_item_sin_precio_sigue_declarando_que_se_compra():
    """Un ítem sin precio es igualmente una declaración de qué se compra: si fuera el
    único, el proceso se quedaría sin categoría por no traer una cifra."""
    items = [{"ocid": "a", "origen": "award", "cpc": "35260",
              "cantidad": None, "precio_unitario": None}]
    assert cpc_dominante(items)["a"][0] == "35260"


# --- los nombres: el defecto que llegó a producción ------------------------------

def test_se_rechaza_el_razonamiento_del_modelo():
    """El caso literal: la taxonomía anterior publicó una categoría con 4.308 procesos
    llamada «Medicamento antiviral y antibiótico no, es más genérico: Med». Nadie
    miraba la salida del modelo."""
    assert not validar_nombre(
        "Medicamento antiviral y antibiótico no, es más genérico: Med")


def test_se_rechaza_lo_que_no_es_un_nombre():
    malos = [
        "",
        "Es una categoría de medicamentos",
        "el nombre sería Medicamento",
        "Categoría: papelería",
        "Medicamento 500 mg",
        "material de oficina",          # sin mayúscula inicial
        "A",
        "Servicios de mantenimiento y reparación de vehículos automotores diversos",
    ]
    for m in malos:
        assert not validar_nombre(m), f"{m!r} debería rechazarse"


def test_se_aceptan_los_nombres_buenos():
    """La prueba de falso positivo (regla 5): un validador que rechaza todo es tan
    inútil como uno que acepta todo, y además invisible."""
    buenos = [
        "Medicamentos", "Material de oficina", "Mantenimiento de vehículos",
        "Reactivos de laboratorio", "Obra civil", "Uniformes escolares",
    ]
    for b in buenos:
        assert validar_nombre(b), f"{b!r} debería aceptarse"


def test_si_el_modelo_falla_manda_la_descripcion_oficial():
    """Es preferible un nombre largo y burocrático de la fuente a uno inventado que
    nadie ha comprobado."""
    d = Counter({"SERVICIOS DE MANTENIMIENTO Y REPARACION DE VEHICULOS DE MOTOR. "
                 "ESTOS SERVICIOS INCLUYEN": 99})
    n = nombre_de_respaldo(d)
    assert n and len(n) <= 48
    assert "ESTOS SERVICIOS" not in n
    assert n[0].isupper()


def test_dos_categorias_no_pueden_llamarse_igual():
    """Es el defecto original entero: «oficina» quedó repartido en 12 categorías con
    74.209 procesos porque nada impedía que dos grupos recibieran el mismo rótulo."""
    descripciones = {
        "35291": Counter({"REACTIVOS PARA ANALISIS CELULAR": 80}),
        "35440": Counter({"REACTIVOS COMPUESTOS PARA DIAGNOSTICO": 20}),
    }
    nombres = resolver_nombres(descripciones, bautizador=lambda g, d: "Reactivos")
    assert len(set(nombres.values())) == 2, f"nombres repetidos: {nombres}"
    assert "35440" in nombres["35440"], "la desambiguación debe usar el código"


def test_los_duplicados_de_mayuscula_y_plural_cuentan_como_el_mismo_nombre():
    """«Equipo médico», «Equipo Médico» y «Equipos médicos» convivieron en producción.
    Detectarlos no necesita un modelo: es comparación de cadenas."""
    claves = {_clave_normalizada(n) for n in
              ("Equipo médico", "Equipo Médico", "Equipos médicos", "Equipos Medicos")}
    assert len(claves) == 1, f"deberían ser la misma clave: {claves}"


def test_material_y_articulos_de_oficina_no_son_lo_mismo_por_cadena():
    """El límite honesto de la comparación por cadena: no resuelve sinónimos. Por eso la
    taxonomía la define el CPC y no los nombres — si dependiera de los nombres,
    volveríamos a las doce categorías de oficina."""
    assert _clave_normalizada("Material de oficina") != _clave_normalizada("Artículos de oficina")


# --- el conjunto ----------------------------------------------------------------

def test_agrupar_devuelve_categoria_para_cada_proceso_con_items():
    items = [
        {"ocid": "a", "origen": "award", "cpc": "3526000506",
         "descripcion": "Amoxicilina 500 mg", "cantidad": 10, "precio_unitario": 2},
        {"ocid": "b", "origen": "tender", "cpc": "87141001",
         "descripcion": "MANTENIMIENTO DE VEHICULOS", "cantidad": 1, "precio_unitario": 500},
        {"ocid": "c", "origen": "award", "cpc": None,
         "descripcion": "algo sin clasificar", "cantidad": 1, "precio_unitario": 9},
    ]
    descripciones, por_ocid = agrupar_items(items)
    assert por_ocid == {"a": "35260", "b": "87141"}
    assert set(descripciones) == {"35260", "87141"}
    assert "c" not in por_ocid, "un proceso sin CPC no debe recibir categoría inventada"


def test_una_categoria_que_ya_tiene_nombre_lo_conserva():
    """Dos motivos, y el segundo importa más que el coste: renombrar cada noche gastaba
    350 llamadas al modelo por gusto, y hacía que el rótulo de una categoría cambiara
    bajo los pies del usuario entre dos ejecuciones."""
    llamadas = []

    def bautizador(g, d):
        llamadas.append(g)
        return "Inventado"

    nombres = resolver_nombres(
        {"35260": Counter({"MEDICAMENTOS": 5}), "87141": Counter({"MANTENIMIENTO": 3})},
        bautizador=bautizador,
        ya_nombradas={"35260": "Medicamentos"},
    )
    assert llamadas == ["87141"], f"solo debía nombrarse la nueva, y se llamó a {llamadas}"
    assert nombres["35260"] == "Medicamentos"


def test_el_guardia_de_ejecucion_esta_al_final():
    """D-023: añadir funciones con `cat >>` las deja DESPUÉS del guardia, y entonces
    `main()` corre antes de que existan. Importa sin error y falla al ejecutarse — que es
    la peor combinación, porque las pruebas pasan.

    Volvió a pasar hoy, al añadir `referencial_de_items`."""
    from pathlib import Path

    fuente = (Path(__file__).resolve().parents[1] / "src" / "taxonomia.py").read_text(
        encoding="utf-8")
    assert fuente.rstrip().endswith("raise SystemExit(main())"), (
        "hay código después del guardia `if __name__ == '__main__'`: se ejecutaría "
        "main() antes de definirlo (D-023)"
    )


# --- el referencial que el CSV no trae ------------------------------------------

def test_el_referencial_es_la_suma_de_los_totales_de_linea():
    """1.264 de 5.717 procesos convocados de julio salían sin monto, y los 1.264 eran
    subasta inversa: el CSV nunca trae `value_amount` para ese método.

    **Esta prueba nació equivocada.** Exigía cantidad × `precio_unitario`, porque el
    nombre de la columna me hizo creer que era un precio por unidad. Es el total de la
    línea (D-033), así que el referencial es la suma, sin multiplicar. Una prueba que
    fija la semántica equivocada la vuelve más difícil de corregir, no más fácil."""
    from taxonomia import referencial_de_items

    items = [
        {"ocid": "a", "origen": "tender", "cantidad": 10, "precio_unitario": 100},
        {"ocid": "a", "origen": "tender", "cantidad": 2, "precio_unitario": 50},
    ]
    assert referencial_de_items(items) == {"a": 150.0}


def test_el_referencial_no_mezcla_lo_adjudicado():
    """El referencial es lo que se CONVOCA. Sumar lo adjudicado daría una cifra que no es
    ninguna de las dos, y el ratio adjudicado/referencial —que es media tesis del
    producto— quedaría inservible."""
    from taxonomia import referencial_de_items

    items = [
        {"ocid": "a", "origen": "tender", "cantidad": 10, "precio_unitario": 100},
        {"ocid": "a", "origen": "award", "cantidad": 10, "precio_unitario": 80},
    ]
    assert referencial_de_items(items) == {"a": 100.0}


def test_un_item_sin_cifras_no_aporta_un_cero():
    """Un proceso cuyos ítems no declaran precio no debe aparecer con referencial 0: cero
    y «no declarado» son cosas distintas, y una de las dos es mentira."""
    from taxonomia import referencial_de_items

    assert referencial_de_items(
        [{"ocid": "a", "origen": "tender", "cantidad": None, "precio_unitario": None}]
    ) == {}
