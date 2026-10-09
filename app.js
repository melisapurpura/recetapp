/* RecetApp · lee data/precios.csv en el navegador y compara por precio por unidad.
   Sin frameworks ni build: JavaScript del navegador, nada más.
   Los precios se muestran tal como vienen del CSV; aquí nunca se estiman. */

(function () {
  'use strict';

  var RUTA_CSV = 'data/precios.csv';

  var COLUMNAS = ['fecha', 'farmacia', 'principio_activo', 'concentracion',
    'producto', 'marca', 'presentacion', 'unidades', 'precio', 'precio_lista',
    'precio_unidad', 'url'];

  var A_MG = { MCG: 0.001, MG: 1, G: 1000, UI: 1 };
  var RE_CONCENTRACION = /(\d+(?:[.,]\d+)?)\s*(MG|MCG|G|UI)/i;
  var RE_DIACRITICOS = /[̀-ͯ]/g;

  var pesos = new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', maximumFractionDigits: 0
  });
  var pesosConCentavos = new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP',
    minimumFractionDigits: 2, maximumFractionDigits: 2
  });
  var fechaLarga = new Intl.DateTimeFormat('es-CO', {
    day: 'numeric', month: 'long', year: 'numeric'
  });
  var fechaCorta = new Intl.DateTimeFormat('es-CO', {
    day: 'numeric', month: 'short', year: 'numeric'
  });
  var porcentaje = new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: 0, maximumFractionDigits: 1
  });

  var campo = document.getElementById('consulta');
  var formulario = document.getElementById('formulario');
  var estado = document.getElementById('estado');
  var resultados = document.getElementById('resultados');
  var sugerencias = document.getElementById('sugerencias');
  var chips = document.getElementById('chips');
  var fechaDatos = document.getElementById('fecha-datos');
  var fuente = document.getElementById('fuente');

  var filas = [];
  // Por grupo (principio activo + concentración), la fila más barata por
  // unidad de todo el CSV, no solo de la búsqueda actual.
  var masBaratos = Object.create(null);
  var contadorPaneles = 0;

  // ------------------------------------------------------------------ CSV

  /* Parser carácter por carácter: respeta campos entre comillas, comas dentro
     de comillas y comillas escapadas (""). Tolera \r\n y \n. */
  function parsearCSV(texto) {
    var lineas = [];
    var fila = [];
    var valor = '';
    var enComillas = false;

    for (var i = 0; i < texto.length; i++) {
      var c = texto.charAt(i);

      if (enComillas) {
        if (c === '"') {
          if (texto.charAt(i + 1) === '"') { valor += '"'; i++; }
          else { enComillas = false; }
        } else {
          valor += c;
        }
        continue;
      }

      if (c === '"') { enComillas = true; }
      else if (c === ',') { fila.push(valor); valor = ''; }
      else if (c === '\n') { fila.push(valor); valor = ''; lineas.push(fila); fila = []; }
      else if (c !== '\r') { valor += c; }
    }

    if (valor !== '' || fila.length) { fila.push(valor); lineas.push(fila); }
    return lineas;
  }

  function numero(texto) {
    if (!texto) { return null; }
    var n = parseFloat(String(texto).replace(',', '.'));
    return isNaN(n) ? null : n;
  }

  /* Tildes y mayúsculas fuera: 'acetaminofén' y 'ACETAMINOFEN' son lo mismo. */
  function normalizar(texto) {
    return String(texto || '')
      .normalize('NFD')
      .replace(RE_DIACRITICOS, '')
      .toLowerCase()
      .replace(/\s+/g, ' ')
      .trim();
  }

  /* '125 MCG' -> 0.125, para ordenar por concentración y no por texto:
     como cadena, '100 MG' quedaría antes de '50 MG'. */
  function miligramos(concentracion) {
    var hallado = RE_CONCENTRACION.exec(concentracion || '');
    if (!hallado) { return -1; }
    return parseFloat(hallado[1].replace(',', '.')) * A_MG[hallado[2].toUpperCase()];
  }

  function aFilas(lineas) {
    if (!lineas.length) { throw new Error('El CSV está vacío.'); }

    var encabezado = lineas[0].map(function (c) { return c.trim(); });
    var faltan = COLUMNAS.filter(function (c) { return encabezado.indexOf(c) === -1; });
    if (faltan.length) {
      throw new Error('El CSV no trae estas columnas: ' + faltan.join(', ') + '.');
    }

    var indice = {};
    COLUMNAS.forEach(function (c) { indice[c] = encabezado.indexOf(c); });

    var resultado = [];
    lineas.slice(1).forEach(function (linea) {
      if (!linea.length || (linea.length === 1 && linea[0].trim() === '')) { return; }

      var fila = {};
      COLUMNAS.forEach(function (c) {
        fila[c] = (linea[indice[c]] || '').trim();
      });

      fila.precioNum = numero(fila.precio);
      fila.unidadesNum = numero(fila.unidades);
      fila.precioUnidadNum = numero(fila.precio_unidad);
      fila.mg = miligramos(fila.concentracion);
      fila.buscable = normalizar([fila.producto, fila.marca,
        fila.principio_activo, fila.concentracion].join(' '));
      fila.comparable = !!(fila.principio_activo && fila.concentracion &&
        fila.precioUnidadNum !== null);

      resultado.push(fila);
    });
    return resultado;
  }

  function claveGrupo(fila) {
    return normalizar(fila.principio_activo) + '|' + normalizar(fila.concentracion);
  }

  /* Índice de la opción más barata por unidad de cada grupo. Se calcula sobre
     todo el CSV: la alternativa barata sirve aunque no esté en la búsqueda. */
  function indexarMasBaratos() {
    masBaratos = Object.create(null);
    filas.forEach(function (fila) {
      if (!fila.comparable) { return; }
      var clave = claveGrupo(fila);
      var actual = masBaratos[clave];
      if (!actual) {
        masBaratos[clave] = { fila: fila, cuantas: 1 };
        return;
      }
      actual.cuantas += 1;
      if (fila.precioUnidadNum < actual.fila.precioUnidadNum) { actual.fila = fila; }
    });
  }

  // --------------------------------------------------------------- formatos

  /* 'YYYY-MM-DD' -> Date local. Con new Date('2026-10-08') el navegador
     interpreta UTC y en Colombia (UTC-5) mostraría el día anterior. */
  function aFecha(iso) {
    var partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    if (!partes) { return null; }
    return new Date(+partes[1], +partes[2] - 1, +partes[3]);
  }

  function formatear(formato, iso) {
    var fecha = aFecha(iso);
    return fecha ? formato.format(fecha) : iso;
  }

  /* El precio por unidad casi nunca es redondo: $470 se ve mejor sin decimales
     y $188,20 los necesita. Dos decimales solo cuando aportan. */
  function pesosUnidad(valor) {
    return Number.isInteger(valor) ? pesos.format(valor) : pesosConCentavos.format(valor);
  }

  function plural(n, singular, varias) {
    return n + ' ' + (n === 1 ? singular : varias);
  }

  // ------------------------------------------------------------------- DOM

  function nodo(etiqueta, clase, texto) {
    var elemento = document.createElement(etiqueta);
    if (clase) { elemento.className = clase; }
    if (texto !== undefined && texto !== null) { elemento.textContent = texto; }
    return elemento;
  }

  function bloquePrecio(rotulo, valor, clase) {
    var bloque = nodo('div', 'precios__bloque');
    bloque.appendChild(nodo('span', 'precios__rotulo', rotulo));
    bloque.appendChild(nodo('span', 'precios__valor' + (clase ? ' ' + clase : ''), valor));
    return bloque;
  }

  function razonSinComparar(fila) {
    var faltan = [];
    if (!fila.principio_activo) { faltan.push('el catálogo no publica el principio activo'); }
    if (!fila.concentracion) { faltan.push('no publica la concentración'); }
    if (fila.precioUnidadNum === null) { faltan.push('no publica cuántas unidades trae el empaque'); }
    return 'No entra a la comparación: ' + faltan.join('; ') + '.';
  }

  /* «Misma sustancia, más barato»: qué producto del mismo principio activo y
     concentración cuesta menos por unidad, y cuánto se ahorra. */
  function contenidoComparacion(fila) {
    var panel = nodo('div', 'comparacion__cuerpo');
    panel.appendChild(nodo('h5', 'comparacion__titulo', 'Misma sustancia, más barato'));

    if (!fila.comparable) {
      panel.appendChild(nodo('p', 'comparacion__nota',
        'No se puede comparar: ' + razonSinComparar(fila)
          .replace('No entra a la comparación: ', '')));
      return panel;
    }

    var grupo = masBaratos[claveGrupo(fila)];
    var barato = grupo.fila;
    var etiquetaGrupo = fila.principio_activo + ' · ' + fila.concentracion;

    if (barato.precioUnidadNum >= fila.precioUnidadNum) {
      panel.appendChild(nodo('p', 'comparacion__nota', grupo.cuantas === 1
        ? 'Es la única opción de ' + etiquetaGrupo + ' en nuestros datos.'
        : 'Ya es la más barata por unidad: ninguna de las ' + grupo.cuantas +
          ' opciones de ' + etiquetaGrupo + ' cuesta menos por unidad.'));
      return panel;
    }

    var ahorroPorUnidad = fila.precioUnidadNum - barato.precioUnidadNum;
    var ahorroRelativo = ahorroPorUnidad / fila.precioUnidadNum * 100;

    panel.appendChild(nodo('p', 'comparacion__ahorro',
      'Ahorras ' + porcentaje.format(ahorroRelativo) + ' % por unidad'));

    if (fila.unidadesNum) {
      panel.appendChild(nodo('p', 'comparacion__detalle',
        pesos.format(ahorroPorUnidad * fila.unidadesNum) + ' menos por las mismas ' +
        fila.unidadesNum + ' unidades.'));
    }

    var alternativa = nodo('div', 'comparacion__opcion');
    alternativa.appendChild(nodo('p', 'comparacion__producto', barato.producto));
    alternativa.appendChild(nodo('p', 'comparacion__marca',
      [barato.marca, barato.farmacia].filter(Boolean).join(' · ')));
    alternativa.appendChild(nodo('p', 'comparacion__precio',
      pesosUnidad(barato.precioUnidadNum) + ' por unidad' +
      (barato.precioNum === null ? '' : ' · ' + pesos.format(barato.precioNum) +
        ' el empaque' + (barato.unidadesNum ? ' de ' + barato.unidadesNum + ' unidades' : ''))));
    alternativa.appendChild(nodo('p', 'comparacion__fecha',
      'Precio del ' + formatear(fechaCorta, barato.fecha) + ' en ' + barato.farmacia));

    if (barato.url) {
      var enlace = nodo('a', 'comparacion__enlace',
        'Ver en ' + barato.farmacia + ' ↗');
      enlace.href = barato.url;
      enlace.target = '_blank';
      enlace.rel = 'noopener noreferrer';
      alternativa.appendChild(enlace);
    }

    panel.appendChild(alternativa);
    return panel;
  }

  function tarjeta(fila, esBarata) {
    var articulo = nodo('article', 'tarjeta' + (esBarata ? ' tarjeta--barata' : ''));

    if (esBarata) {
      articulo.appendChild(nodo('p', 'tarjeta__insignia', 'Más barato por unidad'));
    }

    // Farmacia y fecha van siempre: es regla del proyecto.
    articulo.appendChild(nodo('h4', 'tarjeta__farmacia', fila.farmacia));
    articulo.appendChild(nodo('p', 'tarjeta__fecha',
      'Precio del ' + formatear(fechaCorta, fila.fecha)));

    articulo.appendChild(nodo('p', 'tarjeta__producto', fila.producto));
    if (fila.marca) {
      articulo.appendChild(nodo('p', 'tarjeta__marca', fila.marca));
    }

    if (fila.unidadesNum) {
      articulo.appendChild(nodo('p', 'tarjeta__unidades',
        plural(fila.unidadesNum, 'unidad por empaque', 'unidades por empaque')));
    }
    if (fila.presentacion) {
      var presentacion = nodo('p', 'tarjeta__presentacion', fila.presentacion);
      presentacion.title = fila.presentacion;
      articulo.appendChild(presentacion);
    }

    var precios = nodo('div', 'precios');
    precios.appendChild(bloquePrecio('Precio',
      fila.precioNum === null ? 'sin dato' : pesos.format(fila.precioNum)));

    if (fila.precioUnidadNum !== null) {
      precios.appendChild(bloquePrecio('Por unidad',
        pesosUnidad(fila.precioUnidadNum), 'precios__valor--unidad'));
    } else {
      precios.appendChild(nodo('span', 'precios__faltante', 'Sin precio por unidad'));
    }
    articulo.appendChild(precios);

    if (!fila.comparable) {
      articulo.appendChild(nodo('p', 'tarjeta__nota', razonSinComparar(fila)));
    }

    if (fila.url) {
      var enlace = nodo('a', 'tarjeta__enlace', 'Ver en ' + fila.farmacia + ' ↗');
      enlace.href = fila.url;
      enlace.target = '_blank';
      enlace.rel = 'noopener noreferrer';
      articulo.appendChild(enlace);
    }

    // Toque en la tarjeta: abre «Misma sustancia, más barato». El botón vive
    // dentro del artículo, así que el clic burbujea y un solo listener basta;
    // los clics en los enlaces no cuentan como toque en la tarjeta.
    contadorPaneles += 1;
    var idPanel = 'comparacion-' + contadorPaneles;

    var boton = nodo('button', 'tarjeta__comparar', 'Misma sustancia, más barato');
    boton.type = 'button';
    boton.setAttribute('aria-expanded', 'false');
    boton.setAttribute('aria-controls', idPanel);
    articulo.appendChild(boton);

    var panel = nodo('div', 'comparacion');
    panel.id = idPanel;
    panel.hidden = true;
    articulo.appendChild(panel);

    articulo.addEventListener('click', function (evento) {
      if (evento.target.closest('a')) { return; }

      var abierto = !panel.hidden;
      if (!abierto && !panel.firstChild) {
        panel.appendChild(contenidoComparacion(fila));
      }
      panel.hidden = abierto;
      boton.setAttribute('aria-expanded', abierto ? 'false' : 'true');
      articulo.classList.toggle('tarjeta--abierta', !abierto);
    });

    return articulo;
  }

  function seccionGrupo(grupo) {
    var seccion = nodo('section', 'grupo');
    seccion.appendChild(nodo('h3', 'grupo__titulo',
      grupo.principio_activo + ' · ' + grupo.concentracion));

    var masBarato = grupo.filas[0].precioUnidadNum;
    seccion.appendChild(nodo('p', 'grupo__resumen',
      plural(grupo.filas.length, 'opción', 'opciones') +
      ' · desde ' + pesosUnidad(masBarato) + ' por unidad'));

    var contenedor = nodo('div', 'tarjetas');
    grupo.filas.forEach(function (fila) {
      // Si hay empate en el mínimo, se resaltan todas las empatadas.
      contenedor.appendChild(tarjeta(fila, fila.precioUnidadNum === masBarato));
    });
    seccion.appendChild(contenedor);
    return seccion;
  }

  function seccionSinDatos(sinDatos) {
    var seccion = nodo('section', 'grupo grupo--sin-datos');
    seccion.appendChild(nodo('h3', 'grupo__titulo', 'Sin datos para comparar'));
    seccion.appendChild(nodo('p', 'grupo__resumen',
      plural(sinDatos.length, 'producto', 'productos') +
      ' que el catálogo publica sin los datos necesarios para calcular el ' +
      'precio por unidad. Aparecen para que sepas que existen; no se estima nada.'));

    var contenedor = nodo('div', 'tarjetas');
    sinDatos.forEach(function (fila) {
      contenedor.appendChild(tarjeta(fila, false));
    });
    seccion.appendChild(contenedor);
    return seccion;
  }

  // ------------------------------------------------------------- búsqueda

  function coincide(fila, palabras) {
    return palabras.every(function (palabra) {
      return fila.buscable.indexOf(palabra) !== -1;
    });
  }

  function agrupar(encontradas) {
    var mapa = Object.create(null);
    var orden = [];

    encontradas.forEach(function (fila) {
      var clave = claveGrupo(fila);
      if (!mapa[clave]) {
        mapa[clave] = {
          principio_activo: fila.principio_activo,
          concentracion: fila.concentracion,
          mg: fila.mg,
          filas: []
        };
        orden.push(mapa[clave]);
      }
      mapa[clave].filas.push(fila);
    });

    orden.forEach(function (grupo) {
      grupo.filas.sort(function (a, b) {
        return a.precioUnidadNum - b.precioUnidadNum;
      });
    });

    orden.sort(function (a, b) {
      var porPrincipio = normalizar(a.principio_activo)
        .localeCompare(normalizar(b.principio_activo), 'es-CO');
      return porPrincipio !== 0 ? porPrincipio : a.mg - b.mg;
    });

    return orden;
  }

  /* Para la portada: los grupos donde más se ahorra cambiando de marca.
     Se exigen dos marcas distintas, si no estaríamos comparando dos empaques
     del mismo laboratorio y eso no es cambiar de marca. */
  function gruposConMasAhorro(cuantos) {
    var comparables = filas.filter(function (fila) { return fila.comparable; });

    return agrupar(comparables)
      .map(function (grupo) {
        var marcas = [];
        grupo.filas.forEach(function (fila) {
          var marca = normalizar(fila.marca);
          if (marca && marcas.indexOf(marca) === -1) { marcas.push(marca); }
        });
        var barata = grupo.filas[0];
        var cara = grupo.filas[grupo.filas.length - 1];
        return {
          grupo: grupo,
          marcas: marcas.length,
          barata: barata,
          cara: cara,
          veces: barata.precioUnidadNum ? cara.precioUnidadNum / barata.precioUnidadNum : 0
        };
      })
      .filter(function (d) { return d.marcas > 1 && d.veces > 1; })
      .sort(function (a, b) { return b.veces - a.veces; })
      .slice(0, cuantos);
  }

  function seccionDestacada(destacado) {
    var grupo = destacado.grupo;
    var seccion = nodo('section', 'grupo');

    var titulo = nodo('h3', 'grupo__titulo');
    titulo.appendChild(document.createTextNode(
      grupo.principio_activo + ' · ' + grupo.concentracion + ' '));
    titulo.appendChild(nodo('span', 'destacado__veces',
      porcentaje.format(destacado.veces) + 'x de diferencia'));
    seccion.appendChild(titulo);

    seccion.appendChild(nodo('p', 'grupo__resumen',
      'De ' + pesosUnidad(destacado.barata.precioUnidadNum) + ' a ' +
      pesosUnidad(destacado.cara.precioUnidadNum) + ' por unidad, entre ' +
      plural(destacado.marcas, 'marca', 'marcas') + '.'));

    var contenedor = nodo('div', 'tarjetas');
    contenedor.appendChild(tarjeta(destacado.barata, true));
    contenedor.appendChild(tarjeta(destacado.cara, false));
    seccion.appendChild(contenedor);

    if (grupo.filas.length > 2) {
      var boton = nodo('button', 'destacado__mas',
        'Ver las ' + grupo.filas.length + ' opciones de ' +
        grupo.principio_activo + ' ' + grupo.concentracion + ' →');
      boton.type = 'button';
      boton.addEventListener('click', function () {
        campo.value = grupo.principio_activo + ' ' + grupo.concentracion;
        buscar(campo.value);
        window.scrollTo(0, 0);
      });
      seccion.appendChild(boton);
    }

    return seccion;
  }

  function pintarPortada() {
    var destacados = gruposConMasAhorro(5);
    if (!destacados.length) { return; }

    var portada = nodo('section', 'destacados');
    portada.appendChild(nodo('h2', 'destacados__titulo', 'Mayores ahorros de hoy'));
    portada.appendChild(nodo('p', 'destacados__bajada',
      'Mismo principio activo y misma concentración, muy distinto precio por ' +
      'unidad. Toca una tarjeta para ver la alternativa más barata.'));
    destacados.forEach(function (destacado) {
      portada.appendChild(seccionDestacada(destacado));
    });
    resultados.appendChild(portada);
  }

  function buscar(consulta) {
    resultados.textContent = '';

    var palabras = normalizar(consulta).split(' ').filter(Boolean);

    if (!palabras.length) {
      sugerencias.hidden = false;
      estado.textContent = 'Busca tu medicamento por nombre, marca o principio ' +
        'activo, o mira dónde hay más diferencia de precio hoy.';
      pintarPortada();
      return;
    }

    sugerencias.hidden = true;

    var encontradas = filas.filter(function (fila) { return coincide(fila, palabras); });

    if (!encontradas.length) {
      estado.textContent = 'No encontramos «' + consulta.trim() + '» entre los ' +
        filas.length + ' precios cargados. Prueba con el principio activo, ' +
        'por ejemplo «ibuprofeno».';
      return;
    }

    var comparables = encontradas.filter(function (fila) { return fila.comparable; });
    var sinDatos = encontradas.filter(function (fila) { return !fila.comparable; });
    var grupos = agrupar(comparables);

    estado.textContent = grupos.length
      ? plural(encontradas.length, 'precio encontrado', 'precios encontrados') +
        ' en ' + plural(grupos.length, 'grupo', 'grupos') +
        ' de principio activo y concentración.'
      : plural(encontradas.length, 'precio encontrado', 'precios encontrados') +
        ', pero sin los datos que hacen falta para comparar por unidad.';

    var fragmento = document.createDocumentFragment();
    grupos.forEach(function (grupo) { fragmento.appendChild(seccionGrupo(grupo)); });
    if (sinDatos.length) { fragmento.appendChild(seccionSinDatos(sinDatos)); }
    resultados.appendChild(fragmento);
  }

  // ----------------------------------------------------------------- chips

  function pintarChips() {
    var principios = [];
    filas.forEach(function (fila) {
      if (fila.principio_activo && principios.indexOf(fila.principio_activo) === -1) {
        principios.push(fila.principio_activo);
      }
    });
    principios.sort(function (a, b) { return a.localeCompare(b, 'es-CO'); });

    principios.forEach(function (principio) {
      var boton = nodo('button', 'chip', principio);
      boton.type = 'button';
      boton.addEventListener('click', function () {
        campo.value = principio;
        buscar(principio);
        campo.focus();
      });
      chips.appendChild(boton);
    });
  }

  // ----------------------------------------------------------------- carga

  function mostrarError(mensaje, conAyudaServidor) {
    estado.className = 'estado estado--error';
    estado.textContent = mensaje;
    if (conAyudaServidor) {
      estado.appendChild(nodo('span', null,
        ' Para verlo en tu computador, levanta un servidor en la carpeta del ' +
        'proyecto con '));
      estado.appendChild(nodo('code', null, 'python -m http.server 8000'));
      estado.appendChild(nodo('span', null, ' y abre http://localhost:8000.'));
    }
  }

  function arrancar(texto) {
    filas = aFilas(parsearCSV(texto));
    if (!filas.length) { throw new Error('El CSV no tiene filas de precios.'); }
    indexarMasBaratos();

    var fechas = filas.map(function (fila) { return fila.fecha; })
      .filter(Boolean).sort();
    var farmacias = [];
    filas.forEach(function (fila) {
      if (fila.farmacia && farmacias.indexOf(fila.farmacia) === -1) {
        farmacias.push(fila.farmacia);
      }
    });
    farmacias.sort(function (a, b) { return a.localeCompare(b, 'es-CO'); });

    fechaDatos.textContent = 'Precios consultados el ' +
      formatear(fechaLarga, fechas[fechas.length - 1]) + '.';
    fechaDatos.hidden = false;

    fuente.textContent = filas.length + ' precios de ' +
      plural(farmacias.length, 'farmacia', 'farmacias') + ': ' +
      farmacias.join(', ') + '.';

    pintarChips();
    buscar(campo.value);

    campo.addEventListener('input', function () { buscar(campo.value); });
  }

  // Enter no debe recargar la página: el filtrado es en vivo.
  formulario.addEventListener('submit', function (evento) {
    evento.preventDefault();
    campo.blur();
  });

  // 'no-cache' revalida con el servidor en cada carga: si el CSV no cambió
  // responde 304 y no cuesta nada, pero quien ya visitó el sitio no se queda
  // con precios viejos en caché.
  fetch(RUTA_CSV, { cache: 'no-cache' })
    .then(function (respuesta) {
      if (!respuesta.ok) {
        throw new Error('el servidor respondió ' + respuesta.status +
          ' al pedir ' + RUTA_CSV + '.');
      }
      return respuesta.text();
    })
    .then(arrancar)
    .catch(function (error) {
      // file:, data: y cualquier cosa que no sea http(s): el navegador no deja
      // leer el CSV y hace falta un servidor.
      var esArchivoLocal = location.protocol !== 'http:' && location.protocol !== 'https:';
      mostrarError(esArchivoLocal
        ? 'No se pudieron leer los precios porque la página se abrió como ' +
          'archivo local y el navegador bloquea la lectura de ' + RUTA_CSV + '.'
        : 'No se pudieron leer los precios: ' + error.message,
        esArchivoLocal);
      console.error('RecetApp:', error);
    });
}());
