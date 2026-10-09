# RecetApp

Web que compara precios de medicamentos entre farmacias de Colombia y muestra
la opción más barata con la misma sustancia activa.

## Reglas del proyecto

Estas reglas son obligatorias. Si algo que te piden las contradice, avísalo
antes de implementarlo.

### Stack

- Sitio **estático**: solo HTML, CSS y JavaScript.
- **Sin frameworks** (no React, Vue, Svelte, Tailwind, jQuery, etc.) y **sin
  paso de build** (no npm, no bundlers, no transpiladores, no preprocesadores).
- Debe funcionar publicado en **GitHub Pages**: rutas relativas, nada de
  servidor propio ni variables de entorno, todo abriéndose desde `index.html`.
- JavaScript moderno del navegador (ES modules nativos si hacen falta); sin
  dependencias instaladas. Si se necesita una librería, se discute primero.

### Idioma y moneda

- Todo el contenido, los textos de la interfaz y los mensajes van en **español
  de Colombia**.
- Los precios se muestran en **pesos colombianos (COP)**, con el formato local
  (por ejemplo `$12.500`).
- El código (nombres de variables, funciones, archivos) puede ir en inglés o
  español, pero sé consistente con lo que ya exista.

### Diseño

- **Mobile first**: se diseña primero para celular y luego se adapta a
  pantallas grandes.
- Objetivos móviles: tocar cómodo (áreas de toque grandes), texto legible sin
  hacer zoom, una sola columna por defecto, sin scroll horizontal.
- CSS escrito en móvil primero, con `min-width` en los media queries para
  ampliar a tablet y escritorio.

### Datos

- Los datos de precios viven en **`data/precios.csv`** y se leen **en el
  navegador** (por ejemplo con `fetch`), no se incrustan en el JavaScript.
- **Nunca inventes precios** ni los edites a mano. Si falta un dato, se deja
  faltante y se indica en la interfaz; no se rellena con estimaciones,
  promedios ni ejemplos inventados presentados como reales.
- Si hacen falta datos para probar, van en un archivo aparte claramente
  marcado como de prueba, nunca mezclados en `data/precios.csv`.
- Las actualizaciones de `data/precios.csv` las hace una persona o un proceso
  de recolección documentado, no una edición improvisada.

### Cómo se muestran los precios

- **Cada precio muestra siempre la farmacia y la fecha** del dato. Un precio
  sin esos dos campos no se muestra.
- **La comparación es por precio por unidad** (tableta, mililitro, gramo,
  según el medicamento), **nunca por caja**. Si solo se conoce el precio de la
  caja, hay que derivar el precio por unidad con la cantidad del empaque; si no
  se puede, ese precio no entra en la comparación.
- La opción más barata se decide por precio por unidad entre productos con la
  **misma sustancia activa** y la misma concentración.

### Aviso siempre visible

Este texto debe estar visible en todo momento en la interfaz (no oculto tras un
clic, un acordeón ni un pie de página al que haya que bajar):

> RecetApp compara precios; no reemplaza la indicación de tu médico o farmacéutico.

- Se copia **tal cual**, sin reformular ni abreviar.
- No des consejo médico ni sugieras cambiar un medicamento por otro: la app
  compara precios de la misma sustancia, nada más.
