# RecetApp

Compara precios de medicamentos entre farmacias de Colombia y muestra la opción
más barata con la misma sustancia activa.

> RecetApp compara precios; no reemplaza la indicación de tu médico o farmacéutico.

## Qué hace

Buscas un medicamento por su sustancia activa (o por el nombre comercial que
conoces) y RecetApp te muestra, para esa misma sustancia y concentración, los
precios registrados en distintas farmacias, ordenados de más barato a más caro.

Detalles que importan al comparar:

- **La comparación es por precio por unidad** (tableta, mililitro, gramo), no
  por caja: una caja más barata puede salir más costosa por tableta.
- **Cada precio muestra la farmacia y la fecha** en que se registró, para que
  sepas qué tan vigente es el dato.
- Los precios están en **pesos colombianos (COP)**.

## Estado

Primera versión funcionando: buscador, agrupación por principio activo y
concentración, tarjetas ordenadas por precio por unidad con la más barata
resaltada, y la sección «Misma sustancia, más barato» al tocar una tarjeta.

Los datos se recogen con dos scripts de Python (biblioteca estándar, sin
dependencias): `scraper.py` consulta el catálogo público de La Rebaja y
`unir.py` une esa consulta con `data/base.csv` para producir
`data/precios.csv`, que es lo que lee la web.

## Cómo está hecho

Sitio **estático**: HTML, CSS y JavaScript, sin frameworks y sin paso de build.
Se publica tal cual en GitHub Pages. Los precios se leen en el navegador desde
`data/precios.csv`.

Está diseñado **primero para celular**, que es desde donde se consulta un precio
estando en la farmacia.

Las reglas completas (stack, datos, diseño, cómo se muestran los precios) están
en [CLAUDE.md](CLAUDE.md).

## Correr el proyecto localmente

No hay nada que instalar ni compilar, pero **no basta con abrir `index.html` con
doble clic**: el navegador bloquea la lectura de `data/precios.csv` desde
`file://`. Hay que levantar un servidor local desde la carpeta del proyecto.

Con Python:

```bash
python -m http.server 8000
```

Luego abre `http://localhost:8000` en el navegador.

Para probar la vista móvil, usa las herramientas de desarrollo del navegador
(F12 → modo dispositivo) o entra desde el celular a la IP de tu computador en la
misma red.

## Los datos

Todos los precios viven en `data/precios.csv`. Reglas de oro:

- **Los precios no se inventan ni se editan a mano.** Si un dato falta, se deja
  faltante y la interfaz lo indica; no se rellena con estimaciones ni promedios.
- Un precio sin farmacia y sin fecha no se muestra.
- Si solo se conoce el precio de la caja, se deriva el precio por unidad usando
  la cantidad del empaque. Si no se puede derivar, ese precio queda fuera de la
  comparación.
- Los datos de prueba van en un archivo aparte, marcado como tal, nunca
  mezclados en `data/precios.csv`.

## Alcance

RecetApp **solo compara precios** entre productos con la misma sustancia activa
y la misma concentración. No da consejo médico, no sugiere cambiar un
medicamento por otro, no recomienda dosis y no reemplaza lo que te indique tu
médico o tu farmacéutico.

## El sitio publicado

https://melisapurpura.github.io/recetapp/

Se publica con GitHub Pages desde la rama `main`, carpeta raíz: cada push a
`main` actualiza el sitio. No hay paso de build que ejecutar.

### Al cambiar `styles.css` o `app.js`

Súbele uno al `?v=` con que `index.html` los enlaza. GitHub Pages cachea los
archivos diez minutos; sin eso, un navegador puede quedarse con el HTML nuevo y
el CSS viejo durante ese rato.

## Vista previa al compartir

`vista-previa-2.png` (1200×630) es la imagen que muestran LinkedIn, WhatsApp y
compañía. Las redes la pintan a menos de la mitad de su tamaño y la
recomprimen, así que todo el texto va grande: nada por debajo de 32 px se lee.
(`vista-previa.png`, la primera versión, se queda un tiempo porque LinkedIn
cachea las tarjetas cerca de una semana y puede seguir pidiéndola.) Se genera con `python vista_previa.py` —lo único que necesita Pillow,
y solo para regenerarla— y se enlaza desde las etiquetas Open Graph de
`index.html` con url absoluta.

No lleva precios a propósito: las redes cachean la vista previa por mucho
tiempo y terminaría anunciando precios viejos.

Si la cambias, **renombra el archivo** (`vista-previa-2.png`) y actualiza
`og:image` y `twitter:image`. No uses `?v=`: algunos rastreadores se atoran con
la cadena de consulta. Después pasa el enlace por
https://www.linkedin.com/post-inspector/ para que LinkedIn relea los
metadatos; su caché dura cerca de una semana.
