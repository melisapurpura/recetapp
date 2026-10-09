#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Une la base histórica con lo scrapeado hoy y escribe data/precios.csv.

Solo biblioteca estándar. Uso:

    python unir.py
    python unir.py --base data/base.csv --hoy data/scrapeado-hoy.csv \
                   --salida data/precios.csv

Reglas:
  - Las dos entradas deben tener exactamente las columnas de COLUMNAS; si no,
    se cancela en lugar de escribir un CSV a medias.
  - Si un producto está en los dos archivos (misma url), gana el de hoy.
  - Si el archivo de hoy no existe, se copia la base tal cual.
  - No se modifica ningún precio: las filas se copian como vienen.
"""

import argparse
import csv
import os
import re
import sys

from scraper import COLUMNAS

BASE = os.path.join("data", "base.csv")
HOY = os.path.join("data", "scrapeado-hoy.csv")
SALIDA = os.path.join("data", "precios.csv")

RE_CONCENTRACION = re.compile(r"(\d+(?:[.,]\d+)?)\s*(MG|MCG|G|UI)")
A_MG = {"MCG": 0.001, "MG": 1.0, "G": 1000.0, "UI": 1.0}


def leer(ruta):
    """Lee un CSV y verifica que traiga las columnas esperadas."""
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        columnas = lector.fieldnames or []
        if columnas != COLUMNAS:
            faltan = [c for c in COLUMNAS if c not in columnas]
            sobran = [c for c in columnas if c not in COLUMNAS]
            raise ValueError(
                "%s no tiene las columnas esperadas.%s%s" % (
                    ruta,
                    " Faltan: %s." % ", ".join(faltan) if faltan else "",
                    " Sobran: %s." % ", ".join(sobran) if sobran else ""))
        return [{c: (fila.get(c) or "").strip() for c in COLUMNAS}
                for fila in lector]


def miligramos(concentracion):
    """'50 MG' -> 50.0, para ordenar por concentración y no por texto."""
    encontrado = RE_CONCENTRACION.search(concentracion.upper())
    if not encontrado:
        return -1.0
    return float(encontrado.group(1).replace(",", ".")) * A_MG[encontrado.group(2)]


def orden(fila):
    try:
        precio_unidad = float(fila["precio_unidad"])
    except ValueError:
        precio_unidad = float("inf")   # las filas sin precio por unidad, al final
    return (fila["principio_activo"], miligramos(fila["concentracion"]),
            precio_unidad, fila["farmacia"])


def unir(base, hoy):
    """Devuelve (filas, reemplazadas). Lo de hoy pisa lo de la base por url."""
    urls_hoy = {fila["url"] for fila in hoy if fila["url"]}
    conservadas = [fila for fila in base if fila["url"] not in urls_hoy]
    reemplazadas = len(base) - len(conservadas)
    return sorted(conservadas + hoy, key=orden), reemplazadas


def escribir(filas, salida):
    carpeta = os.path.dirname(salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    with open(salida, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS,
                                  lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)


def main(argv=None):
    opciones = argparse.ArgumentParser(
        description="Une la base histórica con lo scrapeado hoy en un solo CSV.")
    opciones.add_argument("--base", default=BASE)
    opciones.add_argument("--hoy", default=HOY)
    opciones.add_argument("--salida", default=SALIDA)
    argumentos = opciones.parse_args(argv)

    if not os.path.exists(argumentos.base):
        print("No existe %s; no hay nada que unir." % argumentos.base,
              file=sys.stderr)
        return 1

    try:
        base = leer(argumentos.base)
        if os.path.exists(argumentos.hoy):
            hoy = leer(argumentos.hoy)
        else:
            hoy = []
            print("No existe %s; se usa solo la base." % argumentos.hoy)
    except (ValueError, OSError) as error:
        print(error, file=sys.stderr)
        return 1

    filas, reemplazadas = unir(base, hoy)
    escribir(filas, argumentos.salida)

    print("base: %d filas" % len(base))
    print("hoy:  %d filas (%d reemplazan a la base, %d nuevas)"
          % (len(hoy), reemplazadas, len(hoy) - reemplazadas))
    print("%s: %d filas" % (argumentos.salida, len(filas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
