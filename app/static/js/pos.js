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

    const modal = document.getElementById('modal-guisado');
    const modalProducto = document.getElementById('modal-producto');
    const modalOpciones = document.getElementById('modal-opciones');
    const modalCancelar = document.getElementById('modal-cancelar');

    let pendiente = null;

    function agregar(productoId, nombre, precio, guisado) {
        const guisadoFinal = guisado || '';
        const existente = carrito.find(
            (linea) => linea.producto_id === productoId && linea.guisado === guisadoFinal
        );
        if (existente) {
            existente.cantidad += 1;
        } else {
            carrito.push({
                producto_id: productoId,
                nombre: nombre,
                precio: precio,
                guisado: guisadoFinal,
                cantidad: 1,
            });
        }
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

            const celdaProducto = document.createElement('td');
            celdaProducto.className = 'py-1.5 pr-2';
            const nombre = document.createElement('p');
            nombre.className = 'font-semibold text-xs leading-tight';
            nombre.textContent = linea.nombre;
            celdaProducto.appendChild(nombre);
            if (linea.guisado) {
                const guisado = document.createElement('p');
                guisado.className = 'text-[10px] text-terracota font-bold';
                guisado.textContent = '🍲 ' + linea.guisado;
                celdaProducto.appendChild(guisado);
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

    function abrirModal(productoId, nombre, precio) {
        pendiente = { productoId, nombre, precio };
        modalProducto.textContent = nombre;
        modalOpciones.innerHTML = '';

        window.GUISADOS_DISPONIBLES.forEach((guisado) => {
            const opcion = document.createElement('button');
            opcion.type = 'button';
            opcion.className =
                'border border-cremaoscura rounded-xl px-3 py-2 text-sm font-semibold hover:bg-terracota hover:text-white hover:border-terracota transition bg-crema/40';
            opcion.textContent = guisado;
            opcion.addEventListener('click', () => {
                agregar(pendiente.productoId, pendiente.nombre, pendiente.precio, guisado);
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
            if (boton.dataset.guisado === '1') {
                abrirModal(id, nombre, precio);
            } else {
                agregar(id, nombre, precio, '');
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
        render();
    });

    modalCancelar.addEventListener('click', cerrarModal);

    const selectMesa = document.getElementById('mesa_id');
    const bloqueMesa = document.getElementById('bloque-mesa');

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

    formPedido.addEventListener('submit', (evento) => {
        if (carrito.length === 0) {
            evento.preventDefault();
            return;
        }
        const tipo = document.querySelector('input[name="tipo_orden"]:checked');
        if (tipo && tipo.value === 'AQUI' && selectMesa && !selectMesa.value) {
            evento.preventDefault();
            alert('Elige la mesa para este pedido (o cambia a "Para llevar").');
            selectMesa.focus();
            return;
        }
        itemsJson.value = JSON.stringify(
            carrito.map((linea) => ({
                producto_id: linea.producto_id,
                cantidad: linea.cantidad,
                guisado: linea.guisado,
            }))
        );
        botonConfirmar.disabled = true;
        botonConfirmar.textContent = '⏳ Procesando venta...';
    });

    render();
})();
