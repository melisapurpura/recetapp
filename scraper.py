#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consulta el catálogo público de La Rebaja y guarda los precios en un CSV.

Solo biblioteca estándar. Uso:

    python scraper.py
    python scraper.py --salida data/scrapeado-hoy.csv --espera 1.5

Reglas que respeta (ver CLAUDE.md):
  - Revisa robots.txt antes de consultar y se identifica con un User-Agent propio.
  - Espera ESPERA segundos entre consultas.
  - No inventa datos: si falta la concentración o las unidades, el campo queda
    vacío y precio_unidad se deja vacío en lugar de estimarse.
  - Descarta combinaciones de sustancias y formas líquidas.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import date

FARMACIA = "La Rebaja"
BASE = "https://www.larebajavirtual.com"
RUTA_BUSQUEDA = "/api/catalog_system/pub/products/search"
ROBOTS = BASE + "/robots.txt"

USER_AGENT = (
    "RecetAppBot/0.1 (comparador de precios de medicamentos; "
    "+https://github.com/melisapurpura/recetapp)"
)

ESPERA = 1.5          # segundos entre consultas
TIEMPO_LIMITE = 60    # segundos por consulta
SALIDA = os.path.join("data", "scrapeado-hoy.csv")

TERMINOS = [
    "losartan",
    "acetaminofen",
    "ibuprofeno",
    "atorvastatina",
    "metformina",
    "omeprazol",
    "loratadina",
    "amlodipino",
    "dolex",
    "advil",
]

COLUMNAS = [
    "fecha", "farmacia", "principio_activo", "concentracion", "producto",
    "marca", "presentacion", "unidades", "precio", "precio_lista",
    "precio_unidad", "url",
]

# Un nombre con "+", "/" o "HCT" mezcla sustancias: no es comparable.
MARCAS_COMBINACION = ("+", "/", "HCT")

# Líneas antigripales: siempre llevan varias sustancias (analgésico más
# descongestionante o antihistamínico), pero el catálogo les registra un solo
# "Principio activo" y el nombre no trae "+". Sin esto se colarían a la
# comparación. Si alguna resulta ser de una sola sustancia, quítala de la lista.
NOMBRES_COMBINADOS = ("GRIPA", "GRIPE", "ANTIGRIPAL", "FLU", "SINUS",
                      "DIA Y NOCHE", "NOCHE", "TOS")

# Formas líquidas (y otras no dosificadas en unidades contables).
PALABRAS_LIQUIDAS = (
    "JARABE", "SYRUP", "SUSPENSION", "SUSPENSIÓN", "SOLUCION", "SOLUCIÓN",
    "GOTAS", "ELIXIR", "AMPOLLA", "INYECTABLE", "VIAL", "EMULSION",
    "EMULSIÓN", "JERINGA", "SPRAY", "AEROSOL", "LOCION", "LOCIÓN", "CREMA",
    "UNGUENTO", "UNGÜENTO", "GEL ", "POLVO", "GRANULADO", "SOBRE",
    "ENJUAGUE", "SHAMPOO", "CHAMPU", "CHAMPÚ",
)

# Unidades de medida que no son dosis contables (líquidos, cremas).
UNIDADES_NO_CONTABLES = ("MILILITRO", "ML", "LITRO", "GRAMO", "GR", "G", "ONZA")

RE_CONCENTRACION = re.compile(r"(\d+(?:[.,]\d+)?)\s*(MG|MCG|UI|G)\b")
RE_UNIDADES = re.compile(r"\bX\s*(\d+)\s*([A-ZÁÉÍÓÚÑ]+)?")


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #

def pedir(url, tiempo_limite=TIEMPO_LIMITE):
    """GET con nuestro User-Agent. Devuelve el cuerpo como texto."""
    peticion = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "es-CO,es;q=0.9",
    })
    with urllib.request.urlopen(peticion, timeout=tiempo_limite) as respuesta:
        return respuesta.read().decode("utf-8", "replace")


def robots_permite(ruta):
    """True si robots.txt nos deja consultar `ruta`.

    Si robots.txt no se puede leer, devolvemos False: ante la duda, no se
    consulta.
    """
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(ROBOTS)
    try:
        texto = pedir(ROBOTS, tiempo_limite=30)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as error:
        print("No se pudo leer robots.txt (%s). Se cancela." % error,
              file=sys.stderr)
        return False
    parser.parse(texto.splitlines())
    return parser.can_fetch(USER_AGENT, BASE + ruta)


def buscar(termino):
    """Consulta el catálogo por término y devuelve la lista de productos."""
    url = BASE + RUTA_BUSQUEDA + "?" + urllib.parse.urlencode({
        "ft": termino, "_from": 0, "_to": 49,
    })
    return json.loads(pedir(url))


# --------------------------------------------------------------------------- #
# Lectura de campos
# --------------------------------------------------------------------------- #

def especificacion(producto, campo):
    """Devuelve el primer valor de una especificación (vienen como listas)."""
    valor = producto.get(campo)
    if isinstance(valor, list):
        valor = valor[0] if valor else None
    if valor is None:
        return ""
    return str(valor).strip()


def principios_activos(producto):
    """Lista de sustancias. El campo trae una lista cuyos elementos pueden
    venir con varias sustancias separadas por coma."""
    bruto = producto.get("Principio activo") or []
    if not isinstance(bruto, list):
        bruto = [bruto]
    sustancias = []
    for entrada in bruto:
        for parte in str(entrada).split(","):
            parte = parte.strip().upper()
            if parte and parte not in sustancias:
                sustancias.append(parte)
    return sustancias


def concentracion_del_nombre(nombre):
    """'LOSARTAN POTASICO 50 MG (GENFAR)' -> '50 MG'. Vacío si no aparece."""
    encontrado = RE_CONCENTRACION.search(nombre.upper())
    if not encontrado:
        return ""
    cantidad = encontrado.group(1).replace(",", ".")
    if cantidad.endswith(".0"):
        cantidad = cantidad[:-2]
    return "%s %s" % (cantidad, encontrado.group(2))


def unidades_y_presentacion(producto, nombre):
    """Devuelve (unidades, presentacion, unidad_de_medida).

    El orden importa. Las unidades reales del empaque están en las
    especificaciones ('Cantidadunidadesmedida', 'Presentacionunidadmedida');
    el nombre solo se usa como último recurso, porque a veces trae la cantidad
    de OTRA presentación del mismo producto (p. ej. 'ADVIL GRIPA X 72' cuando
    ese SKU es el blíster de 4).
    """
    presentacion = (especificacion(producto, "Presentacionunidadmedida")
                    or especificacion(producto, "PresentacionProducto")
                    or especificacion(producto, "Presentacion"))
    unidad = (especificacion(producto, "Unidadmedida")
              or especificacion(producto, "Contenido"))

    unidades = ""
    cantidad = (especificacion(producto, "Cantidadunidadesmedida")
                or especificacion(producto, "ML_UnidadesPorEnvase"))
    try:
        numero = float(cantidad.replace(",", "."))
    except ValueError:
        numero = 0.0
    if numero > 0:
        unidades = int(numero) if numero.is_integer() else numero

    if unidades == "":
        for texto in (presentacion, nombre):
            encontrado = RE_UNIDADES.search(texto.upper())
            if encontrado:
                unidades = int(encontrado.group(1))
                if not unidad and encontrado.group(2):
                    unidad = encontrado.group(2)
                break

    # 'UND X 1 UND' no dice cuántas dosis trae el empaque (típico de los
    # paquetes de promoción): es un dato desconocido, no un empaque de una
    # sola unidad.
    if unidades == 1 and unidad.upper() in ("UND", "UNIDAD", "UN", ""):
        unidades = ""

    return unidades, presentacion, unidad.upper()


def oferta(item):
    """commertialOffer del primer vendedor, o None."""
    vendedores = item.get("sellers") or []
    if not vendedores:
        return None
    return vendedores[0].get("commertialOffer")


def numero(valor):
    """Precio como int si es entero, float si no, '' si no sirve."""
    if valor is None:
        return ""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return ""
    if valor <= 0:
        return ""
    return int(valor) if valor.is_integer() else round(valor, 2)


# --------------------------------------------------------------------------- #
# Filtros
# --------------------------------------------------------------------------- #

def es_combinacion(nombre, sustancias):
    if len(sustancias) > 1:
        return True
    nombre = nombre.upper()
    if any(marca in nombre for marca in MARCAS_COMBINACION):
        return True
    return any(palabra in nombre for palabra in NOMBRES_COMBINADOS)


def es_liquido(nombre, unidad):
    nombre = " " + nombre.upper() + " "
    if any(palabra in nombre for palabra in PALABRAS_LIQUIDAS):
        return True
    return unidad.upper() in UNIDADES_NO_CONTABLES


# --------------------------------------------------------------------------- #
# Armado de filas
# --------------------------------------------------------------------------- #

def filas_del_producto(producto, hoy, descartes):
    """Convierte un producto del catálogo en 0..n filas del CSV."""
    nombre = (producto.get("productName") or "").strip()
    if not nombre:
        descartes["sin nombre"] += 1
        return []

    sustancias = principios_activos(producto)
    if es_combinacion(nombre, sustancias):
        descartes["combinación de sustancias"] += 1
        return []

    unidades, presentacion, unidad = unidades_y_presentacion(producto, nombre)
    if es_liquido(nombre, unidad):
        descartes["forma líquida"] += 1
        return []

    filas = []
    for item in producto.get("items") or []:
        datos = oferta(item)
        if not datos:
            descartes["sin vendedor"] += 1
            continue
        if not datos.get("IsAvailable"):
            descartes["sin disponibilidad"] += 1
            continue

        precio = numero(datos.get("Price"))
        if precio == "":
            descartes["sin precio"] += 1
            continue

        # Precio por unidad: solo si sabemos cuántas unidades trae el empaque.
        # Nunca se estima.
        precio_unidad = round(precio / unidades, 2) if unidades else ""

        filas.append({
            "fecha": hoy,
            "farmacia": FARMACIA,
            "principio_activo": sustancias[0] if sustancias else "",
            "concentracion": concentracion_del_nombre(nombre),
            "producto": nombre,
            "marca": (producto.get("brand") or "").strip(),
            "presentacion": presentacion,
            "unidades": unidades,
            "precio": precio,
            "precio_lista": numero(datos.get("ListPrice")),
            "precio_unidad": precio_unidad,
            "url": (producto.get("link") or "").strip(),
        })
    return filas


def recolectar(terminos, espera):
    """Consulta cada término y devuelve las filas, sin repetir productos."""
    hoy = date.today().isoformat()
    descartes = {clave: 0 for clave in (
        "sin nombre", "combinación de sustancias", "forma líquida",
        "sin vendedor", "sin disponibilidad", "sin precio", "repetido")}
    filas = []
    vistos = set()

    for indice, termino in enumerate(terminos):
        if indice:
            time.sleep(espera)
        try:
            productos = buscar(termino)
        except (urllib.error.URLError, urllib.error.HTTPError,
                json.JSONDecodeError, OSError) as error:
            print("  %-14s error: %s" % (termino, error), file=sys.stderr)
            continue

        nuevas = 0
        for producto in productos:
            for fila in filas_del_producto(producto, hoy, descartes):
                clave = (fila["producto"], fila["presentacion"], fila["url"])
                if clave in vistos:
                    descartes["repetido"] += 1
                    continue
                vistos.add(clave)
                filas.append(fila)
                nuevas += 1
        print("  %-14s %2d productos -> %2d filas" % (termino, len(productos), nuevas))

    return filas, descartes


def guardar(filas, salida):
    carpeta = os.path.dirname(salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    with open(salida, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS,
                                  lineterminator="\n")
        escritor.writeheader()
        for fila in sorted(filas, key=lambda f: (f["principio_activo"],
                                                 f["concentracion"],
                                                 f["precio_unidad"] or 0)):
            escritor.writerow(fila)


def main(argv=None):
    opciones = argparse.ArgumentParser(
        description="Consulta precios de medicamentos en el catálogo público "
                    "de La Rebaja y los guarda en un CSV.")
    opciones.add_argument("--salida", default=SALIDA,
                          help="ruta del CSV (por defecto %s)" % SALIDA)
    opciones.add_argument("--espera", type=float, default=ESPERA,
                          help="segundos entre consultas (por defecto %.1f)" % ESPERA)
    opciones.add_argument("--terminos", nargs="+", default=TERMINOS,
                          help="términos a buscar")
    argumentos = opciones.parse_args(argv)

    print("Revisando %s ..." % ROBOTS)
    if not robots_permite(RUTA_BUSQUEDA):
        print("robots.txt no permite consultar %s. No se consulta nada."
              % RUTA_BUSQUEDA, file=sys.stderr)
        return 1
    print("robots.txt permite %s\n" % RUTA_BUSQUEDA)
    time.sleep(argumentos.espera)

    filas, descartes = recolectar(argumentos.terminos, argumentos.espera)

    if not filas:
        print("\nNo se obtuvo ninguna fila; no se escribe el CSV.",
              file=sys.stderr)
        return 1

    guardar(filas, argumentos.salida)
    print("\n%d filas en %s" % (len(filas), argumentos.salida))
    print("Descartados: " + ", ".join(
        "%s %d" % (clave, valor) for clave, valor in descartes.items() if valor))
    sin_unidad = sum(1 for fila in filas if fila["precio_unidad"] == "")
    if sin_unidad:
        print("%d filas sin precio por unidad (no se conocen las unidades "
              "del empaque; no se estima)." % sin_unidad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
