#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera vista-previa.png, la imagen que se ve al compartir el enlace.

    python vista_previa.py

Necesita Pillow (`pip install pillow`). Es la única parte del proyecto que usa
una dependencia externa, y solo para regenerar la imagen: el sitio no la
necesita para funcionar.

La imagen no lleva precios a propósito. Los precios cambian todos los días y
una vista previa queda cacheada por mucho tiempo en las redes: si pusiéramos
cifras, terminaríamos anunciando precios viejos.
"""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Falta Pillow: pip install pillow", file=sys.stderr)
    sys.exit(1)

SALIDA = "vista-previa-2.png"

# 1200x630 es la proporción que piden LinkedIn, Facebook y WhatsApp (1.91:1).
ANCHO, ALTO = 1200, 630

FONDO = (8, 6, 15)
PANEL = (24, 18, 40)
MORADO = (195, 160, 255)
MORADO_FUERTE = (123, 77, 255)
TINTA = (240, 236, 250)
TINTA_SUAVE = (201, 192, 221)

NEGRITA = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
NORMAL = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]


def fuente(rutas, tamano):
    for ruta in rutas:
        if os.path.exists(ruta):
            return ImageFont.truetype(ruta, tamano)
    return ImageFont.load_default()


def ancho_de(dibujo, texto, tipo):
    izq, _, der, _ = dibujo.textbbox((0, 0), texto, font=tipo)
    return der - izq


def fuente_que_quepa(dibujo, texto, rutas, tamano, ancho_maximo):
    """Baja el tamaño hasta que el texto quepa: nada se sale del panel."""
    while tamano > 12:
        tipo = fuente(rutas, tamano)
        if ancho_de(dibujo, texto, tipo) <= ancho_maximo:
            return tipo
        tamano -= 2
    return fuente(rutas, 12)


def envolver(dibujo, texto, tipo, ancho_maximo):
    """Parte el texto en líneas que quepan en ancho_maximo."""
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = (actual + " " + palabra).strip()
        if actual and ancho_de(dibujo, prueba, tipo) > ancho_maximo:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    return lineas


def main():
    imagen = Image.new("RGB", (ANCHO, ALTO), FONDO)
    dibujo = ImageDraw.Draw(imagen)

    # Panel con el borde morado, como las tarjetas de la app.
    dibujo.rounded_rectangle([40, 40, ANCHO - 40, ALTO - 40], radius=28,
                             fill=PANEL, outline=(47, 38, 73), width=2)
    dibujo.rounded_rectangle([40, 40, 58, ALTO - 40], radius=28, fill=MORADO_FUERTE)

    izquierda = 100
    util = ANCHO - izquierda - 100

    # Las redes muestran esta imagen a menos de la mitad de su tamaño y la
    # recomprimen: todo va grande y con mucho contraste, o se ve borroso.
    marca = fuente(NEGRITA, 124)
    lema = fuente(NORMAL, 46)
    destacado = fuente(NEGRITA, 40)
    farmacias = fuente(NEGRITA, 36)
    aviso = fuente(NORMAL, 32)

    # "Recet" en morado y "App" en claro, igual que en el encabezado del sitio.
    dibujo.text((izquierda, 72), "Recet", font=marca, fill=MORADO)
    dibujo.text((izquierda + ancho_de(dibujo, "Recet", marca), 72), "App",
                font=marca, fill=TINTA)

    frase_lema = "Compara precios de medicamentos en Colombia."
    lema = fuente_que_quepa(dibujo, frase_lema, NORMAL, 46, util)
    dibujo.text((izquierda, 252), frase_lema, font=lema, fill=TINTA)

    frase = "Mismo principio activo, mejor precio por unidad."
    destacado = fuente_que_quepa(dibujo, frase, NEGRITA, 40, util)
    dibujo.text((izquierda, 332), frase, font=destacado, fill=MORADO)

    dibujo.text((izquierda, 408), "La Rebaja  ·  Locatel  ·  Olímpica",
                font=farmacias, fill=TINTA_SUAVE)

    # El aviso también va en la vista previa: es lo primero que se comparte.
    dibujo.line([izquierda, 476, ANCHO - izquierda, 476],
                fill=(47, 38, 73), width=2)
    texto_aviso = ("RecetApp compara precios; no reemplaza la indicación de "
                   "tu médico o farmacéutico.")
    y = 496
    for linea in envolver(dibujo, texto_aviso, aviso, util):
        dibujo.text((izquierda, y), linea, font=aviso, fill=TINTA_SUAVE)
        y += 40

    imagen.save(SALIDA, "PNG", optimize=True)
    print("%s · %dx%d · %d KB" % (SALIDA, ANCHO, ALTO,
                                  os.path.getsize(SALIDA) // 1024))


if __name__ == "__main__":
    main()
