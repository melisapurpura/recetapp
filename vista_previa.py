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

SALIDA = "vista-previa.png"

# 1200x630 es la proporción que piden LinkedIn, Facebook y WhatsApp (1.91:1).
ANCHO, ALTO = 1200, 630

FONDO = (8, 6, 15)
PANEL = (24, 18, 40)
MORADO = (195, 160, 255)
MORADO_FUERTE = (123, 77, 255)
TINTA = (240, 236, 250)
TINTA_SUAVE = (169, 159, 198)

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


def main():
    imagen = Image.new("RGB", (ANCHO, ALTO), FONDO)
    dibujo = ImageDraw.Draw(imagen)

    # Panel con el borde morado, como las tarjetas de la app.
    dibujo.rounded_rectangle([48, 48, ANCHO - 48, ALTO - 48], radius=28,
                             fill=PANEL, outline=(47, 38, 73), width=2)
    dibujo.rounded_rectangle([48, 48, 62, ALTO - 48], radius=28, fill=MORADO_FUERTE)

    marca_recet = fuente(NEGRITA, 104)
    marca_app = fuente(NEGRITA, 104)
    lema = fuente(NORMAL, 40)
    destacado = None  # se calcula abajo, cuando ya hay con qué medir
    farmacias = fuente(NORMAL, 32)
    aviso = fuente(NORMAL, 25)

    x, y = 110, 108

    # "Recet" en morado y "App" en claro, igual que en el encabezado del sitio.
    dibujo.text((x, y), "Recet", font=marca_recet, fill=MORADO)
    x_app = x + ancho_de(dibujo, "Recet", marca_recet)
    dibujo.text((x_app, y), "App", font=marca_app, fill=TINTA)

    dibujo.text((110, 248),
                "Compara precios de medicamentos\nentre farmacias de Colombia.",
                font=lema, fill=TINTA, spacing=14)

    frase = "El mismo principio activo, al mejor precio por unidad."
    destacado = fuente_que_quepa(dibujo, frase, NEGRITA, 38, ANCHO - 110 - 110)
    dibujo.text((110, 372), frase, font=destacado, fill=MORADO)

    dibujo.text((110, 432), "La Rebaja  ·  Locatel  ·  Olímpica",
                font=farmacias, fill=TINTA_SUAVE)

    # El aviso también va en la vista previa: es lo primero que se comparte.
    dibujo.line([110, 500, ANCHO - 110, 500], fill=(47, 38, 73), width=2)
    texto_aviso = ("RecetApp compara precios; no reemplaza la indicación de "
                   "tu médico o farmacéutico.")
    aviso = fuente_que_quepa(dibujo, texto_aviso, NORMAL, 25, ANCHO - 110 - 110)
    dibujo.text((110, 522), texto_aviso, font=aviso, fill=TINTA_SUAVE)

    imagen.save(SALIDA, "PNG", optimize=True)
    print("%s · %dx%d · %d KB" % (SALIDA, ANCHO, ALTO,
                                  os.path.getsize(SALIDA) // 1024))


if __name__ == "__main__":
    main()
