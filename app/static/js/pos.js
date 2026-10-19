(function () {
    const carrito = [];
    const formato = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' });

    const cuerpo = document.getElementById('cuerpo-carrito');
    const tabla = document.getElementById('tabla-carrito');
    const vacio = document.getElementById('carrito-vacio');
    const totalEl = document.getElementById('total-carrito');
    const botonConfirmar = document.getElementById('boton-confirmar');
    const itemsJson = document.getElementById('items_json');
    const formPedido = document.getElementById('form-pedido');

    const avisoFaltantes = document.getElementById('aviso-faltantes');
    const listaFaltantes = document.getElementById('lista-faltantes');
    const botonQuitarFaltantes = document.getElementById('boton-quitar-faltantes');
    const botonRevisarFaltantes = document.getElementById('boton-revisar-faltantes');

    const modalVariante = document.getElementById('modal-variante');
    const modalVarianteProducto = document.getElementById('modal-variante-producto');
    const modalVarianteOpciones = document.getElementById('modal-variante-opciones');
    const modalVarianteCancelar = document.getElementById('modal-variante-cancelar');

    const modal = document.getElementById('modal-guisado');
    const modalProducto = document.getElementById('modal-producto');
    const modalOpciones = document.getElementById('modal-opciones');
    const modalCancelar = document.getElementById('modal-cancelar');

    let pendiente = null;

    function agregar(productoId, nombre, precio, guisado, variante) {
        const guisadoFinal = guisado || '';
        const varianteId = variante ? variante.id : null;
        const varianteNombre = variante ? variante.nombre : '';
        const existente = carrito.find(
            (linea) =>
                linea.producto_id === productoId &&
                linea.variante_id === varianteId &&
                linea.guisado === guisadoFinal
        );
        if (existente) {
            existente.cantidad += 1;
        } else {
            carrito.push({
                producto_id: productoId,
                nombre: nombre,
                precio: precio,
                variante_id: varianteId,
                variante_nombre: varianteNombre,
                guisado: guisadoFinal,
                cantidad: 1,
                no_disponible: false,
                motivo: '',
            });
        }
        ocultarAviso();
        render();
    }

    function render() {
        cuerpo.innerHTML = '';
        let total = 0;

        carrito.forEach((linea, indice) => {
            const importe = linea.precio * linea.cantidad;
            total += importe;

            const fila = document.createElement('tr');
            fila.className = 'border-b border-crema/60';
            if (linea.no_disponible) {
                fila.className += ' bg-red-50';
            }

            const celdaProducto = document.createElement('td');
            celdaProducto.className = 'py-1.5 pr-2';
            const nombre = document.createElement('p');
            nombre.className = 'font-semibold text-xs leading-tight';
            nombre.textContent = linea.nombre + (linea.variante_nombre ? ' · ' + linea.variante_nombre : '');
            celdaProducto.appendChild(nombre);
            if (linea.guisado) {
                const guisado = document.createElement('p');
                guisado.className = 'text-[10px] text-terracota font-bold';
                guisado.textContent = '🍲 ' + linea.guisado;
                celdaProducto.appendChild(guisado);
            }
            if (linea.no_disponible) {
                const motivo = document.createElement('p');
                motivo.className = 'text-[10px] text-red-700 font-bold';
                motivo.textContent = '⚠️ ' + (linea.motivo || 'No disponible');
                celdaProducto.appendChild(motivo);
            }

            const celdaCantidad = document.createElement('td');
            celdaCantidad.className = 'py-1.5 text-center whitespace-nowrap';
            celdaCantidad.innerHTML =
                `<button type="button" data-accion="menos" data-indice="${indice}" class="px-1.5 font-bold text-terracota">−</button>` +
                `<span class="font-semibold">${linea.cantidad}</span>` +
                `<button type="button" data-accion="mas" data-indice="${indice}" class="px-1.5 font-bold text-verde">+</button>`;

            const celdaImporte = document.createElement('td');
            celdaImporte.className = 'py-1.5 text-right font-semibold text-xs';
            celdaImporte.textContent = formato.format(importe);

            const celdaQuitar = document.createElement('td');
            celdaQuitar.className = 'py-1.5 text-right';
            celdaQuitar.innerHTML =
                `<button type="button" data-accion="quitar" data-indice="${indice}" class="text-red-500 font-bold">✕</button>`;

            fila.appendChild(celdaProducto);
            fila.appendChild(celdaCantidad);
            fila.appendChild(celdaImporte);
            fila.appendChild(celdaQuitar);
            cuerpo.appendChild(fila);
        });

        totalEl.textContent = formato.format(total);
        const hayProductos = carrito.length > 0;
        tabla.classList.toggle('hidden', !hayProductos);
        vacio.classList.toggle('hidden', hayProductos);
        botonConfirmar.disabled = !hayProductos;
    }

    function abrirModalVariante(producto) {
        pendiente = producto;
        modalVarianteProducto.textContent = producto.nombre;
        modalVarianteOpciones.innerHTML = '';

        producto.variantes.forEach((variante) => {
            const opcion = document.createElement('button');
            opcion.type = 'button';
            opcion.className =
                'border border-cremaoscura rounded-xl px-3 py-3 text-sm font-semibold hover:bg-terracota hover:text-white hover:border-terracota transition bg-crema/40 text-left';
            opcion.innerHTML =
                `<span class="block">${variante.nombre}</span>` +
                `<span class="block text-xs mt-1">${formato.format(Number(variante.precio))}</span>`;
            opcion.addEventListener('click', () => {
                const elegida = {
                    id: Number(variante.id),
                    nombre: variante.nombre,
                    precio: Number(variante.precio),
                };
                cerrarModalVariante();
                if (producto.guisado) {
                    abrirModalGuisado(
                        producto.id,
                        producto.nombre,
                        elegida.precio,
                        elegida
                    );
                } else {
                    agregar(producto.id, producto.nombre, elegida.precio, '', elegida);
                }
            });
            modalVarianteOpciones.appendChild(opcion);
        });

        modalVariante.classList.remove('hidden');
        modalVariante.classList.add('flex');
    }

    function cerrarModalVariante() {
        modalVariante.classList.add('hidden');
        modalVariante.classList.remove('flex');
    }

    function abrirModalGuisado(productoId, nombre, precio, variante) {
        pendiente = { productoId, nombre, precio, variante: variante || null };
        modalProducto.textContent =
            nombre + (variante ? ' · ' + variante.nombre : '');
        modalOpciones.innerHTML = '';

        window.GUISADOS_DISPONIBLES.forEach((guisado) => {
            const opcion = document.createElement('button');
            opcion.type = 'button';
            opcion.className =
                'border border-cremaoscura rounded-xl px-3 py-2 text-sm font-semibold hover:bg-terracota hover:text-white hover:border-terracota transition bg-crema/40';
            opcion.textContent = guisado;
            opcion.addEventListener('click', () => {
                agregar(
                    pendiente.productoId,
                    pendiente.nombre,
                    pendiente.precio,
                    guisado,
                    pendiente.variante
                );
                cerrarModal();
            });
            modalOpciones.appendChild(opcion);
        });

        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }

    function cerrarModal() {
        pendiente = null;
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }

    document.querySelectorAll('.boton-producto').forEach((boton) => {
        boton.addEventListener('click', () => {
            const id = Number(boton.dataset.id);
            const nombre = boton.dataset.nombre;
            const precio = Number(boton.dataset.precio);
            let variantes = [];
            try {
                variantes = JSON.parse(boton.dataset.variantes || '[]');
            } catch (error) {
                variantes = [];
            }
            const guisado = boton.dataset.guisado === '1';

            if (variantes.length > 0) {
                abrirModalVariante({ id, nombre, precio, variantes, guisado });
            } else if (guisado) {
                abrirModalGuisado(id, nombre, precio, null);
            } else {
                agregar(id, nombre, precio, '', null);
            }
        });
    });

    cuerpo.addEventListener('click', (evento) => {
        const boton = evento.target.closest('button[data-accion]');
        if (!boton) {
            return;
        }
        const indice = Number(boton.dataset.indice);
        const accion = boton.dataset.accion;
        if (accion === 'mas') {
            carrito[indice].cantidad += 1;
        } else if (accion === 'menos') {
            carrito[indice].cantidad -= 1;
            if (carrito[indice].cantidad <= 0) {
                carrito.splice(indice, 1);
            }
        } else if (accion === 'quitar') {
            carrito.splice(indice, 1);
        }
        ocultarAviso();
        render();
    });

    modalCancelar.addEventListener('click', cerrarModal);
    modalVarianteCancelar.addEventListener('click', cerrarModalVariante);

    const selectMesa = document.getElementById('mesa_id');
    const bloqueMesa = document.getElementById('bloque-mesa');
    const bloquePago = document.getElementById('bloque-pago');
    const selectPago = document.getElementById('metodo_pago');
    const notaCuenta = document.getElementById('nota-cuenta');

    function sincronizarMesa() {
        const tipo = document.querySelector('input[name="tipo_orden"]:checked');
        const esAqui = tipo && tipo.value === 'AQUI';
        if (bloqueMesa) {
            bloqueMesa.classList.toggle('opacity-40', !esAqui);
        }
        if (selectMesa) {
            selectMesa.disabled = !esAqui;
            if (esAqui) {
                selectMesa.setAttribute('required', 'required');
            } else {
                selectMesa.removeAttribute('required');
                selectMesa.value = '';
            }
        }
        if (bloquePago) {
            bloquePago.classList.toggle('hidden', esAqui);
        }
        if (notaCuenta) {
            notaCuenta.classList.toggle('hidden', !esAqui);
        }
        if (selectPago) {
            selectPago.disabled = esAqui;
        }
        if (botonConfirmar) {
            botonConfirmar.textContent = esAqui
                ? '🚀 Enviar a cocina (a la cuenta)'
                : '🚀 Enviar a cocina y cobrar';
        }
    }

    document.querySelectorAll('input[name="tipo_orden"]').forEach((radio) => {
        radio.addEventListener('change', sincronizarMesa);
    });
    sincronizarMesa();

    const parametros = new URLSearchParams(window.location.search);
    if (parametros.get('mesa') && selectMesa) {
        const opcion = selectMesa.querySelector('option[value="' + parametros.get('mesa') + '"]');
        if (opcion && !opcion.disabled) {
            opcion.selected = true;
        }
    }

    function ocultarAviso() {
        if (avisoFaltantes) {
            avisoFaltantes.classList.add('hidden');
        }
        carrito.forEach((linea) => {
            linea.no_disponible = false;
            linea.motivo = '';
        });
    }

    function mostrarAviso() {
        const faltantes = carrito.filter((linea) => linea.no_disponible);
        if (!faltantes.length) {
            ocultarAviso();
            render();
            return false;
        }
        listaFaltantes.innerHTML = '';
        faltantes.forEach((linea) => {
            const item = document.createElement('li');
            item.textContent =
                linea.cantidad + '× ' + linea.nombre +
                (linea.variante_nombre ? ' · ' + linea.variante_nombre : '') +
                (linea.motivo ? ' — ' + linea.motivo : '');
            listaFaltantes.appendChild(item);
        });
        botonQuitarFaltantes.textContent =
            'Quitar ' + faltantes.length +
            (faltantes.length === 1 ? ' platillo' : ' platillos') + ' y continuar';
        avisoFaltantes.classList.remove('hidden');
        render();
        return true;
    }

    function datosPedido() {
        return carrito.map((linea) => ({
            producto_id: linea.producto_id,
            cantidad: linea.cantidad,
            guisado: linea.guisado,
            variante_id: linea.variante_id,
        }));
    }

    function enviarFormulario() {
        itemsJson.value = JSON.stringify(datosPedido());
        botonConfirmar.disabled = true;
        botonConfirmar.textContent = '⏳ Procesando venta...';
        formPedido.submit();
    }

    async function verificarYEnviar() {
        botonConfirmar.disabled = true;
        botonConfirmar.textContent = '⏳ Revisando inventario...';
        try {
            const respuesta = await fetch(window.URL_DISPONIBILIDAD, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    turno: window.TURNO_ACTUAL,
                    items: datosPedido(),
                }),
            });
            if (!respuesta.ok) {
                enviarFormulario();
                return;
            }
            const resultado = await respuesta.json();
            let hayFaltantes = false;
            (resultado.lineas || []).forEach((linea) => {
                const destino = carrito[linea.indice];
                if (!destino) {
                    return;
                }
                destino.no_disponible = !linea.disponible;
                destino.motivo = linea.motivo || '';
                if (!linea.disponible) {
                    hayFaltantes = true;
                }
            });
            if (!hayFaltantes) {
                enviarFormulario();
                return;
            }
            botonConfirmar.disabled = false;
            sincronizarMesa();
            mostrarAviso();
        } catch (error) {
            enviarFormulario();
        }
    }

    if (botonQuitarFaltantes) {
        botonQuitarFaltantes.addEventListener('click', () => {
            for (let indice = carrito.length - 1; indice >= 0; indice -= 1) {
                if (carrito[indice].no_disponible) {
                    carrito.splice(indice, 1);
                }
            }
            ocultarAviso();
            render();
            if (!carrito.length) {
                sincronizarMesa();
                return;
            }
            verificarYEnviar();
        });
    }

    if (botonRevisarFaltantes) {
        botonRevisarFaltantes.addEventListener('click', () => {
            avisoFaltantes.classList.add('hidden');
        });
    }

    formPedido.addEventListener('submit', (evento) => {
        evento.preventDefault();
        if (carrito.length === 0) {
            return;
        }
        const tipo = document.querySelector('input[name="tipo_orden"]:checked');
        if (tipo && tipo.value === 'AQUI' && selectMesa && !selectMesa.value) {
            alert('Elige la mesa para este pedido (o cambia a "Para llevar").');
            selectMesa.focus();
            return;
        }
        verificarYEnviar();
    });

    render();
})();
