import logging

from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages

logger = logging.getLogger(__name__)
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import (
    Usuario, Cliente, Mecanico,
    Vehiculo, Bahia, Repuesto,
    OrdenTrabajo, DetalleRepuesto,
    InspeccionInicial, HistorialOrden,
)
from .email_utils import enviar_notificaciones_orden


def solo_roles(*roles):
    """Devuelve un decorador que verifica que el usuario tenga uno de los roles indicados."""
    def decorador(func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('/login/')
            if request.user.rol not in roles and not request.user.is_superuser:
                messages.error(request, 'No tienes permiso para acceder a esta sección.')
                return redirect('/inicio/')
            return func(request, *args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorador


# ══════════════════════════════════════════════════
#  AUTENTICACIÓN
# ══════════════════════════════════════════════════
def loginVista(request):
    if request.user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        usuario = authenticate(request, username=username, password=password)
        if usuario is not None:
            login(request, usuario)
            messages.success(request, f'Bienvenido/a, {usuario.get_full_name() or usuario.username}.')
            return redirect('/')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'login.html')


@login_required(login_url='/login/')
def logoutVista(request):
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('/login/')


# ══════════════════════════════════════════════════
#  INICIO  (dashboard según rol)
# ══════════════════════════════════════════════════
def inicio(request):
    contexto = {}
    if request.user.is_authenticated:
        # Vista mecánico: solo sus órdenes
        if request.user.rol == 'mecanico' and not request.user.is_superuser:
            try:
                mecanico = request.user.perfil_mecanico
                contexto['mis_ordenes'] = OrdenTrabajo.objects.filter(
                    mecanico=mecanico,
                    estado__in=('pendiente', 'en_proceso')
                ).select_related('vehiculo')
            except Mecanico.DoesNotExist:
                contexto['mis_ordenes'] = []
        elif request.user.rol == 'cliente' and not request.user.is_superuser:
            try:
                cliente = request.user.perfil_cliente
                contexto['mis_ordenes'] = OrdenTrabajo.objects.filter(
                    vehiculo__cliente=cliente
                ).order_by('-fecha_ingreso')
            except Cliente.DoesNotExist:
                contexto['mis_ordenes'] = []
    return render(request, 'inicio.html', contexto)


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def dashboard(request):
    import json
    from django.db.models import Count, Q

    bahias = Bahia.objects.all()
    contexto = {}
    contexto['total_bahias']   = bahias.count()
    contexto['bahias_libres']  = bahias.filter(estado='libre').count()
    contexto['bahias_ocupadas']= bahias.filter(estado='ocupada').count()
    contexto['bahias_espera']  = bahias.filter(estado='en_espera').count()
    contexto['bahias_estado_json'] = {
        'libres': contexto['bahias_libres'],
        'ocupadas': contexto['bahias_ocupadas'],
        'en_espera': contexto['bahias_espera']
    }
    contexto['total_ordenes']  = OrdenTrabajo.objects.filter(estado__in=('pendiente','en_proceso')).count()
    contexto['total_clientes'] = Cliente.objects.count()
    contexto['total_mecanicos']= Mecanico.objects.filter(activo=True).count()
    contexto['ultimas_ordenes']= OrdenTrabajo.objects.select_related('vehiculo').order_by('-creado_en')[:8]

    estados = OrdenTrabajo.objects.values('estado').annotate(total=Count('id'))
    estado_labels = {'pendiente':'Pendiente','en_proceso':'En Proceso','pausada':'Pausada',
                     'finalizada':'Finalizada','entregada':'Entregada','cancelada':'Cancelada'}
    contexto['etiquetas_ordenes_json'] = [estado_labels.get(e['estado'], e['estado']) for e in estados]
    contexto['conteo_ordenes_json'] = [e['total'] for e in estados]

    mecanicos_qs = Mecanico.objects.filter(activo=True).select_related('usuario').annotate(
        total_asignadas = Count('ordenes'),
        total_cerradas  = Count('ordenes', filter=Q(ordenes__estado='finalizada')),
    )
    contexto['nombres_mec_json']            = [m.usuario.get_full_name() or m.usuario.username for m in mecanicos_qs]
    contexto['ordenes_mec_json']            = [m.total_asignadas for m in mecanicos_qs]
    contexto['cerradas_mec_json']           = [m.total_cerradas  for m in mecanicos_qs]
    contexto['nombres_mec_eficiencia_json'] = [m.usuario.get_full_name() or m.usuario.username for m in mecanicos_qs]
    contexto['eficiencia_mec_json']         = [
        round((m.total_cerradas / m.total_asignadas * 100) if m.total_asignadas else 0, 1)
        for m in mecanicos_qs
    ]
    contexto['mecanicos_eficiencia']        = mecanicos_qs

    ordenes_recientes = OrdenTrabajo.objects.select_related('vehiculo').order_by('-creado_en')[:8]
    contexto['ultimas_ordenes'] = ordenes_recientes
    estados_recientes = {}
    for orden in ordenes_recientes:
        estados_recientes[orden.estado] = estados_recientes.get(orden.estado, 0) + 1
    contexto['etiquetas_ordenes_recientes_json'] = [estado_labels.get(k, k) for k in estados_recientes.keys()]
    contexto['conteo_ordenes_recientes_json'] = [estados_recientes[k] for k in estados_recientes.keys()]

    repuestos_margen = list(Repuesto.objects.all().order_by('nombre'))
    contexto['repuestos_margen'] = repuestos_margen
    contexto['nombres_repuestos_json'] = [r.nombre for r in repuestos_margen]
    contexto['margenes_repuestos_json'] = [float(r.margen_ganancia) for r in repuestos_margen]

    return render(request, 'dashboard.html', contexto)


# ══════════════════════════════════════════════════
#  CLIENTES
# ══════════════════════════════════════════════════
@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def listadoClientes(request):
    clientes = Cliente.objects.all()
    return render(request, 'clientes/listadoClientes.html', {'clientes': clientes})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def nuevoCliente(request):
    return render(request, 'clientes/nuevoCiente.html')


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def guardarCliente(request):
    cedula    = request.POST['cedula']
    nombre    = request.POST['nombre']
    apellido  = request.POST['apellido']
    telefono  = request.POST['telefono']
    email     = request.POST.get('email', '')
    direccion = request.POST.get('direccion', '')
    username  = request.POST.get('username', '').strip()
    password  = request.POST.get('password', '')
    password2 = request.POST.get('password2', '')

    if Cliente.objects.filter(cedula=cedula).exists():
        messages.error(request, 'Ya existe un cliente con esa cédula.')
        return redirect('/clientes/nuevo/')

    # Validaciones de credenciales
    if username:
        if Usuario.objects.filter(username=username).exists():
            messages.error(request, f'El usuario "{username}" ya existe. Elige otro.')
            return redirect('/clientes/nuevo/')
        if password != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('/clientes/nuevo/')
        if len(password) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
            return redirect('/clientes/nuevo/')

    # Crear el usuario de acceso si se proporcionaron credenciales
    usuario = None
    if username and password:
        usuario = Usuario.objects.create_user(
            username=username,
            password=password,
            first_name=nombre,
            last_name=apellido,
            email=email,
            rol='cliente',
        )

    cliente = Cliente.objects.create(
        usuario=usuario,
        cedula=cedula, nombre=nombre, apellido=apellido,
        telefono=telefono, email=email, direccion=direccion,
    )
    if usuario:
        messages.success(request, f'Cliente registrado con acceso al sistema (usuario: {username}).')
    else:
        messages.success(request, 'Cliente registrado. Sin acceso al sistema (no se proporcionaron credenciales).')
    return redirect('/clientes/')


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def editarCliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    return render(request, 'clientes/editarCliente.html', {'cliente': cliente})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def actualizarCliente(request):
    id        = request.POST['id']
    cliente   = get_object_or_404(Cliente, id=id)
    username  = request.POST.get('username', '').strip()
    password  = request.POST.get('password', '')
    password2 = request.POST.get('password2', '')

    cliente.cedula    = request.POST['cedula']
    cliente.nombre    = request.POST['nombre']
    cliente.apellido  = request.POST['apellido']
    cliente.telefono  = request.POST['telefono']
    cliente.email     = request.POST.get('email', '')
    cliente.direccion = request.POST.get('direccion', '')
    cliente.save()

    # Actualizar o crear usuario de acceso
    if username:
        if cliente.usuario:
            # Verificar que el nuevo username no esté tomado por otro usuario
            if (Usuario.objects.filter(username=username)
                    .exclude(pk=cliente.usuario.pk).exists()):
                messages.error(request, f'El usuario "{username}" ya está en uso.')
                return redirect(f'/clientes/editar/{id}/')
            cliente.usuario.username   = username
            cliente.usuario.first_name = cliente.nombre
            cliente.usuario.last_name  = cliente.apellido
            cliente.usuario.email      = cliente.email
            if password:
                if password != password2:
                    messages.error(request, 'Las contraseñas no coinciden.')
                    return redirect(f'/clientes/editar/{id}/')
                if len(password) < 6:
                    messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
                    return redirect(f'/clientes/editar/{id}/')
                cliente.usuario.set_password(password)
            cliente.usuario.save()
        else:
            # Crear nuevo usuario para este cliente
            if Usuario.objects.filter(username=username).exists():
                messages.error(request, f'El usuario "{username}" ya existe. Elige otro.')
                return redirect(f'/clientes/editar/{id}/')
            if not password or password != password2:
                messages.error(request, 'Debes ingresar una contraseña y confirmarla para crear el acceso.')
                return redirect(f'/clientes/editar/{id}/')
            nuevo_usuario = Usuario.objects.create_user(
                username=username,
                password=password,
                first_name=cliente.nombre,
                last_name=cliente.apellido,
                email=cliente.email,
                rol='cliente',
            )
            cliente.usuario = nuevo_usuario
            cliente.save()

    messages.success(request, 'Cliente actualizado correctamente.')
    return redirect('/clientes/')


@login_required(login_url='/login/')
@solo_roles('admin')
def eliminarCliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    cliente.delete()
    messages.success(request, 'Cliente eliminado.')
    return redirect('/clientes/')


# ══════════════════════════════════════════════════
#  VEHÍCULOS
# ══════════════════════════════════════════════════
@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def listadoVehiculos(request):
    vehiculos = Vehiculo.objects.select_related('cliente').all()
    return render(request, 'vehiculos/listadoVehiculos.html', {'vehiculos': vehiculos})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def nuevoVehiculo(request):
    clientes = Cliente.objects.all()
    return render(request, 'vehiculos/nuevoVehiculo.html', {'clientes': clientes})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def guardarVehiculo(request):
    cliente_id = request.POST['cliente']
    placa      = request.POST['placa'].upper()

    if Vehiculo.objects.filter(placa=placa).exists():
        messages.error(request, 'Ya existe un vehículo con esa placa.')
        return redirect('/vehiculos/nuevo/')

    cliente = get_object_or_404(Cliente, id=cliente_id)
    Vehiculo.objects.create(
        cliente       = cliente,
        placa         = placa,
        marca         = request.POST['marca'],
        modelo        = request.POST['modelo'],
        anio          = request.POST['anio'],
        color         = request.POST.get('color', ''),
        tipo          = request.POST.get('tipo', 'sedan'),
    )
    messages.success(request, 'Vehículo registrado exitosamente.')
    return redirect('/vehiculos/')


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def editarVehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, id=id)
    clientes = Cliente.objects.all()
    return render(request, 'vehiculos/editarVehiculo.html', {'vehiculo': vehiculo, 'clientes': clientes})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def actualizarVehiculo(request):
    vehiculo = get_object_or_404(Vehiculo, id=request.POST['id'])
    vehiculo.cliente    = get_object_or_404(Cliente, id=request.POST['cliente'])
    vehiculo.placa      = request.POST['placa'].upper()
    vehiculo.marca      = request.POST['marca']
    vehiculo.modelo     = request.POST['modelo']
    vehiculo.anio       = request.POST['anio']
    vehiculo.color      = request.POST.get('color', '')
    vehiculo.tipo       = request.POST.get('tipo', 'sedan')
    vehiculo.save()
    messages.success(request, 'Vehículo actualizado correctamente.')
    return redirect('/vehiculos/')


@login_required(login_url='/login/')
@solo_roles('admin')
def eliminarVehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, id=id)
    vehiculo.delete()
    messages.success(request, 'Vehículo eliminado.')
    return redirect('/vehiculos/')


# ══════════════════════════════════════════════════
#  ÓRDENES DE TRABAJO
# ══════════════════════════════════════════════════
@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista', 'mecanico', 'cliente')
def listadoOrdenes(request):
    ordenes = OrdenTrabajo.objects.select_related(
        'vehiculo__cliente', 'mecanico__usuario', 'bahia'
    ).all().order_by('-fecha_ingreso')

    if request.user.rol == 'mecanico' and not request.user.is_superuser:
        try:
            mecanico = request.user.perfil_mecanico
            ordenes = ordenes.filter(mecanico=mecanico)
        except Mecanico.DoesNotExist:
            ordenes = ordenes.none()
    elif request.user.rol == 'cliente' and not request.user.is_superuser:
        try:
            cliente = request.user.perfil_cliente
            ordenes = ordenes.filter(vehiculo__cliente=cliente)
        except Cliente.DoesNotExist:
            ordenes = ordenes.none()

    return render(request, 'ordenes/listadoOrdenes.html', {'ordenes': ordenes})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def nuevaOrden(request):
    vehiculos = Vehiculo.objects.select_related('cliente').all()
    mecanicos = Mecanico.objects.filter(activo=True).select_related('usuario')
    return render(request, 'ordenes/nuevaOrden.html', {'vehiculos': vehiculos, 'mecanicos': mecanicos})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def guardarOrden(request):
    import uuid
    numero   = 'OT-' + str(uuid.uuid4())[:8].upper()
    vehiculo = get_object_or_404(Vehiculo, id=request.POST['vehiculo'])
    mecanico_id = request.POST.get('mecanico')
    mecanico = get_object_or_404(Mecanico, id=mecanico_id) if mecanico_id else None

    from datetime import datetime, time as dtime
    from django.utils import timezone as tz
    def parsear_fecha(valor, hora_defecto=dtime(8, 0)):
        """Convierte 'YYYY-MM-DD' o 'DD/MM/YYYY' a datetime aware con hora fija a las 08:00."""
        if not valor:
            return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y'):
            try:
                dt_naive = datetime.combine(datetime.strptime(valor.strip(), fmt).date(), hora_defecto)
                return tz.make_aware(dt_naive)
            except ValueError:
                continue
        return None

    orden = OrdenTrabajo.objects.create(
        numero                 = numero,
        vehiculo               = vehiculo,
        mecanico               = mecanico,
        creada_por             = request.user,
        descripcion            = request.POST['descripcion'],
        kilometraje_ingreso    = request.POST.get('kilometraje_ingreso', 0),
        fecha_ingreso          = parsear_fecha(request.POST.get('fecha_ingreso')),
        fecha_estimada_entrega = parsear_fecha(request.POST.get('fecha_estimada_entrega')),
        mano_obra              = request.POST.get('mano_obra', 0),
    )
    # Registrar en historial
    HistorialOrden.objects.create(
        orden        = orden,
        estado_nuevo = 'pendiente',
        observacion  = 'Orden creada',
        cambiado_por = request.user,
    )
    try:
        enviar_notificaciones_orden(orden, evento='creada')
    except Exception as exc:
        logger.error("Error enviando notificaciones para orden %s: %s", orden.numero, exc, exc_info=True)
    messages.success(request, f'Orden {numero} creada. Completa la inspección inicial del vehículo.')
    return redirect(f'/ordenes/{orden.id}/inspeccion/')


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista', 'mecanico', 'cliente')
def detalleOrden(request, id):
    orden = get_object_or_404(OrdenTrabajo, id=id)
    if request.user.rol == 'cliente' and not request.user.is_superuser:
        try:
            cliente = request.user.perfil_cliente
            if orden.vehiculo.cliente != cliente:
                messages.error(request, 'No tienes permiso para ver esta orden.')
                return redirect('/inicio/')
        except Cliente.DoesNotExist:
            return redirect('/inicio/')
    elif request.user.rol == 'mecanico' and not request.user.is_superuser:
        try:
            mecanico = request.user.perfil_mecanico
            if orden.mecanico != mecanico:
                messages.error(request, 'No tienes permiso para ver esta orden.')
                return redirect('/inicio/')
        except Mecanico.DoesNotExist:
            return redirect('/inicio/')
    repuestos = orden.detalle_repuestos.select_related('repuesto').all()
    historial = orden.historial.all()
    try:
        inspeccion = orden.inspeccion
    except InspeccionInicial.DoesNotExist:
        inspeccion = None
    return render(request, 'ordenes/detalleOrden.html', {'orden': orden, 'repuestos': repuestos, 'historial': historial, 'inspeccion': inspeccion})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def editarOrden(request, id):
    orden     = get_object_or_404(OrdenTrabajo, id=id)
    vehiculos = Vehiculo.objects.select_related('cliente').all()
    mecanicos = Mecanico.objects.filter(activo=True).select_related('usuario')
    return render(request, 'ordenes/editarOrden.html', {'orden': orden, 'vehiculos': vehiculos, 'mecanicos': mecanicos})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def actualizarOrden(request):
    orden    = get_object_or_404(OrdenTrabajo, id=request.POST['id'])
    estado_anterior = orden.estado
    mecanico_id = request.POST.get('mecanico')
    orden.vehiculo   = get_object_or_404(Vehiculo, id=request.POST['vehiculo'])
    orden.mecanico   = get_object_or_404(Mecanico, id=mecanico_id) if mecanico_id else None
    orden.descripcion   = request.POST['descripcion']
    orden.mano_obra     = request.POST.get('mano_obra', 0)
    from datetime import datetime, time as dtime
    from django.utils import timezone as tz
    def parsear_fecha(valor, hora_defecto=dtime(8, 0)):
        if not valor:
            return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y'):
            try:
                dt_naive = datetime.combine(datetime.strptime(valor.strip(), fmt).date(), hora_defecto)
                return tz.make_aware(dt_naive)
            except ValueError:
                continue
        return None
    orden.fecha_estimada_entrega = parsear_fecha(request.POST.get('fecha_estimada_entrega'))
    orden.save()
    messages.success(request, 'Orden actualizada correctamente.')
    return redirect('/ordenes/')


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista', 'mecanico')
def cambiarEstadoOrden(request, id):
    """
    Ctrl+Enter / F2 en el front llaman a esta vista vía POST.
    El campo 'estado' viene del formulario/hotkey.
    """
    orden  = get_object_or_404(OrdenTrabajo, id=id)
    nuevo_estado   = request.POST.get('estado')
    observacion    = request.POST.get('observacion', '')
    estado_anterior= orden.estado

    # El mecánico solo puede cambiar entre en_proceso y finalizada
    if request.user.rol == 'mecanico':
        if nuevo_estado not in ('en_proceso', 'finalizada'):
            messages.error(request, 'Acción no permitida.')
            return redirect(f'/ordenes/{id}/')

    # No se puede iniciar trabajo sin bahía asignada
    if nuevo_estado == 'en_proceso' and not orden.bahia:
        messages.error(request, 'No se puede iniciar la orden sin una bahía asignada. Solicita al administrador que asigne una bahía primero.')
        return redirect(f'/ordenes/{id}/')

    if nuevo_estado == 'finalizada':
        orden.fecha_real_entrega = timezone.now()

    orden.estado = nuevo_estado
    orden.save()

    HistorialOrden.objects.create(
        orden           = orden,
        estado_anterior = estado_anterior,
        estado_nuevo    = nuevo_estado,
        observacion     = observacion,
        cambiado_por    = request.user,
    )
    if nuevo_estado == 'finalizada':
        try:
            enviar_notificaciones_orden(orden, evento='finalizada')
        except Exception as exc:
            logger.error("Error enviando notificaciones para orden %s: %s", orden.numero, exc, exc_info=True)
    messages.success(request, f'Estado actualizado a "{orden.get_estado_display()}".')
    return redirect(f'/ordenes/{id}/')


@login_required(login_url='/login/')
@solo_roles('admin')
def eliminarOrden(request, id):
    orden = get_object_or_404(OrdenTrabajo, id=id)
    orden.delete()
    messages.success(request, 'Orden eliminada.')
    return redirect('/ordenes/')


# ══════════════════════════════════════════════════
#  REPUESTOS EN LA ORDEN
# ══════════════════════════════════════════════════
@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista', 'mecanico')
def agregarRepuesto(request, orden_id):
    orden     = get_object_or_404(OrdenTrabajo, id=orden_id)
    repuestos = Repuesto.objects.filter(stock__gt=0)
    return render(request, 'ordenes/agregarRepuesto.html', {'orden': orden, 'repuestos': repuestos})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista', 'mecanico')
def guardarRepuesto(request, orden_id):
    orden       = get_object_or_404(OrdenTrabajo, id=orden_id)
    repuesto    = get_object_or_404(Repuesto, id=request.POST['repuesto'])
    cantidad    = int(request.POST.get('cantidad', 1))
    precio_unit = repuesto.precio_venta

    if repuesto.stock < cantidad:
        messages.error(request, 'Stock insuficiente.')
        return redirect(f'/ordenes/{orden_id}/repuesto/')

    DetalleRepuesto.objects.create(
        orden           = orden,
        repuesto        = repuesto,
        cantidad        = cantidad,
        precio_unitario = precio_unit,
    )
    # Descontar stock
    repuesto.stock -= cantidad
    repuesto.save()
    messages.success(request, 'Repuesto agregado a la orden.')
    return redirect(f'/ordenes/{orden_id}/')


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def eliminarRepuesto(request, id):
    detalle = get_object_or_404(DetalleRepuesto, id=id)
    orden_id = detalle.orden.id
    # Devolver stock
    detalle.repuesto.stock += detalle.cantidad
    detalle.repuesto.save()
    detalle.delete()
    messages.success(request, 'Repuesto eliminado de la orden.')
    return redirect(f'/ordenes/{orden_id}/')


# ══════════════════════════════════════════════════
#  REPUESTOS (inventario)
# ══════════════════════════════════════════════════
@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def listadoRepuestos(request):
    repuestos = Repuesto.objects.all()
    return render(request, 'repuestos/listadoRepuestos.html', {'repuestos': repuestos})


@login_required(login_url='/login/')
@solo_roles('admin')
def nuevoRepuesto(request):
    return render(request, 'repuestos/nuevoRepuesto.html')


@login_required(login_url='/login/')
@solo_roles('admin')
def guardarRepuestoInventario(request):
    if Repuesto.objects.filter(codigo=request.POST['codigo']).exists():
        messages.error(request, 'Ya existe un repuesto con ese código.')
        return redirect('/repuestos/nuevo/')
    Repuesto.objects.create(
        codigo        = request.POST['codigo'],
        nombre        = request.POST['nombre'],
        descripcion   = request.POST.get('descripcion', ''),
        precio_costo  = request.POST['precio_costo'],
        precio_venta  = request.POST['precio_venta'],
        stock         = request.POST.get('stock', 0),
        unidad        = request.POST.get('unidad', 'unidad'),
    )
    messages.success(request, 'Repuesto agregado al inventario.')
    return redirect('/repuestos/')


@login_required(login_url='/login/')
@solo_roles('admin')
def editarRepuesto(request, id):
    repuesto = get_object_or_404(Repuesto, id=id)
    return render(request, 'repuestos/editarRepuesto.html', {'repuesto': repuesto})


@login_required(login_url='/login/')
@solo_roles('admin')
def actualizarRepuesto(request):
    repuesto = get_object_or_404(Repuesto, id=request.POST['id'])
    repuesto.codigo       = request.POST['codigo']
    repuesto.nombre       = request.POST['nombre']
    repuesto.descripcion  = request.POST.get('descripcion', '')
    repuesto.precio_costo = request.POST['precio_costo']
    repuesto.precio_venta = request.POST['precio_venta']
    repuesto.stock        = request.POST.get('stock', 0)
    repuesto.unidad       = request.POST.get('unidad', 'unidad')
    repuesto.save()
    messages.success(request, 'Repuesto actualizado.')
    return redirect('/repuestos/')


@login_required(login_url='/login/')
@solo_roles('admin')
def eliminarRepuesto(request, id):
    repuesto = get_object_or_404(Repuesto, id=id)
    repuesto.delete()
    messages.success(request, 'Repuesto eliminado.')
    return redirect('/repuestos/')


# ══════════════════════════════════════════════════
#  BAHÍAS
# ══════════════════════════════════════════════════
@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def listadoBahias(request):
    bahias = Bahia.objects.all().order_by('numero')
    ordenes = OrdenTrabajo.objects.filter(
        estado__in=('pendiente', 'en_proceso')
    ).select_related('vehiculo', 'bahia').order_by('-creado_en')
    return render(request, 'bahias/listadoBahias.html', {'bahias': bahias, 'ordenes': ordenes})


@login_required(login_url='/login/')
@solo_roles('admin')
def nuevaBahia(request):
    return render(request, 'bahias/nuevaBahia.html')


@login_required(login_url='/login/')
@solo_roles('admin')
def guardarBahia(request):
    Bahia.objects.create(
        numero      = request.POST['numero'],
        nombre      = request.POST['nombre'],
        descripcion = request.POST.get('descripcion', ''),
    )
    messages.success(request, 'Bahía creada.')
    return redirect('/bahias/')


@login_required(login_url='/login/')
@solo_roles('admin')
def editarBahia(request, id):
    bahia = get_object_or_404(Bahia, id=id)
    return render(request, 'bahias/editarBahia.html', {'bahia': bahia})


@login_required(login_url='/login/')
@solo_roles('admin')
def actualizarBahia(request):
    bahia = get_object_or_404(Bahia, id=request.POST['id'])
    bahia.numero      = request.POST['numero']
    bahia.nombre      = request.POST['nombre']
    bahia.descripcion = request.POST.get('descripcion', '')
    bahia.save()
    messages.success(request, 'Bahía actualizada.')
    return redirect('/bahias/')


@login_required(login_url='/login/')
@solo_roles('admin')
def actualizarPosicionBahia(request, id):
    """Recibe {pos_x, pos_y} vía POST desde el drag & drop (jQuery UI / fetch)."""
    import json
    bahia = get_object_or_404(Bahia, id=id)
    datos = json.loads(request.body)
    bahia.pos_x = datos.get('pos_x', bahia.pos_x)
    bahia.pos_y = datos.get('pos_y', bahia.pos_y)
    bahia.save()
    from django.http import JsonResponse
    return JsonResponse({'ok': True})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def asignarOrdenBahia(request, orden_id, bahia_id):
    """Asigna una orden a una bahía mediante drag & drop y actualiza el estado de la bahía."""
    from django.http import JsonResponse
    orden = get_object_or_404(OrdenTrabajo, id=orden_id)
    bahia = get_object_or_404(Bahia, id=bahia_id)

    # Liberar la bahía anterior si ya no tiene órdenes activas
    bahia_anterior = orden.bahia
    if bahia_anterior and bahia_anterior != bahia:
        otras = OrdenTrabajo.objects.filter(
            bahia=bahia_anterior,
            estado__in=('pendiente', 'en_proceso')
        ).exclude(pk=orden.pk)
        if not otras.exists():
            bahia_anterior.estado = 'libre'
            bahia_anterior.save(update_fields=['estado'])

    # Asignar la nueva bahía
    orden.bahia = bahia
    orden.save(update_fields=['bahia'])

    # Actualizar estado de la nueva bahía según el estado de la orden
    if orden.estado == 'en_proceso':
        bahia.estado = 'ocupada'
    elif orden.estado == 'pendiente':
        bahia.estado = 'en_espera'
    # finalizada/cancelada no deberían arrastrarse, pero por seguridad no tocamos
    bahia.save(update_fields=['estado'])

    return JsonResponse({'ok': True, 'bahia': bahia.nombre})


@login_required(login_url='/login/')
@solo_roles('admin')
def eliminarBahia(request, id):
    bahia = get_object_or_404(Bahia, id=id)
    bahia.delete()
    messages.success(request, 'Bahía eliminada.')
    return redirect('/bahias/')


# ══════════════════════════════════════════════════
#  MECÁNICOS
# ══════════════════════════════════════════════════
@login_required(login_url='/login/')
@solo_roles('admin')
def listadoMecanicos(request):
    mecanicos = Mecanico.objects.select_related('usuario').all()
    return render(request, 'mecanicos/listadoMecanicos.html', {'mecanicos': mecanicos})


@login_required(login_url='/login/')
@solo_roles('admin')
def nuevoMecanico(request):
    return render(request, 'mecanicos/nuevoMecanico.html',
                  {'especialidades': Mecanico.ESPECIALIDAD_CHOICES})


@login_required(login_url='/login/')
@solo_roles('admin')
def editarMecanico(request, id):
    mecanico = get_object_or_404(Mecanico, id=id)
    return render(request, 'mecanicos/editarMecanico.html',
                  {'mecanico': mecanico, 'especialidades': Mecanico.ESPECIALIDAD_CHOICES})


@login_required(login_url='/login/')
@solo_roles('admin')
def guardarMecanico(request):
    username     = request.POST['username']
    password     = request.POST['password']
    first_name   = request.POST['nombre']
    last_name    = request.POST['apellido']
    email        = request.POST.get('email', '')
    telefono     = request.POST.get('telefono', '')
    especialidad = request.POST.get('especialidad', 'general')

    if Usuario.objects.filter(username=username).exists():
        messages.error(request, 'Ese nombre de usuario ya existe.')
        return redirect('/mecanicos/nuevo/')

    usuario = Usuario.objects.create_user(
        username=username, password=password,
        first_name=first_name, last_name=last_name,
        email=email, telefono=telefono, rol='mecanico'
    )
    Mecanico.objects.create(usuario=usuario, especialidad=especialidad)
    messages.success(request, 'Mecánico registrado correctamente.')
    return redirect('/mecanicos/')


@login_required(login_url='/login/')
@solo_roles('admin')
def actualizarMecanico(request):
    mecanico = get_object_or_404(Mecanico, id=request.POST['id'])
    usuario = mecanico.usuario

    usuario.username = request.POST['username']
    usuario.first_name = request.POST['nombre']
    usuario.last_name = request.POST['apellido']
    usuario.email = request.POST.get('email', '')
    usuario.telefono = request.POST.get('telefono', '')

    if request.POST.get('password'):
        usuario.set_password(request.POST['password'])

    usuario.save()
    mecanico.especialidad = request.POST.get('especialidad', 'general')
    mecanico.activo = request.POST.get('activo') == 'on'
    mecanico.save()

    messages.success(request, 'Mecánico actualizado correctamente.')
    return redirect('/mecanicos/')


@login_required(login_url='/login/')
@solo_roles('admin')
def eliminarMecanico(request, id):
    mecanico = get_object_or_404(Mecanico, id=id)
    mecanico.usuario.delete()   # borra el usuario y en cascada el mecánico
    messages.success(request, 'Mecánico eliminado.')
    return redirect('/mecanicos/')


# ══════════════════════════════════════════════════
#  INSPECCIÓN INICIAL (guía 20 puntos – Driver.js)
# ══════════════════════════════════════════════════
@login_required(login_url='/login/')
@solo_roles('admin', 'mecanico', 'oficinista')
def inspeccionOrden(request, orden_id):
    orden = get_object_or_404(OrdenTrabajo, id=orden_id)
    try:
        inspeccion = orden.inspeccion
    except InspeccionInicial.DoesNotExist:
        inspeccion = None
    puntos = [f'p{str(i).zfill(2)}' for i in range(1, 21)]
    return render(request, 'ordenes/inspeccionOrden.html', {'orden': orden, 'inspeccion': inspeccion, 'puntos': puntos, 'opciones': InspeccionInicial.ESTADO_PUNTO})


@login_required(login_url='/login/')
@solo_roles('admin', 'mecanico', 'oficinista')
def guardarInspeccion(request, orden_id):
    orden = get_object_or_404(OrdenTrabajo, id=orden_id)
    campos = {
        f'p{str(i).zfill(2)}_{nombre}': request.POST.get(f'p{str(i).zfill(2)}', 'na')
        for i, nombre in enumerate([
            'frenos_delanteros','frenos_traseros','aceite_motor','liquido_frenos',
            'liquido_refrigerante','bateria','alternador','filtro_aire','bujias',
            'correa_distribucion','suspension_delantera','suspension_trasera',
            'neumaticos','alineacion','escape','transmision','direccion',
            'luces','limpiabrisas','carroceria_visual'
        ], start=1)
    }
    campos['orden']                  = orden
    campos['observaciones_generales']= request.POST.get('observaciones', '')
    campos['realizada_por']          = request.user

    InspeccionInicial.objects.update_or_create(orden=orden, defaults=campos)
    messages.success(request, 'Inspección guardada correctamente.')
    return redirect(f'/ordenes/{orden_id}/')


# ══════════════════════════════════════════════════
#  CALENDARIO  (datos para FullCalendar en JSON)
# ══════════════════════════════════════════════════
@login_required(login_url='/login/')
def calendario(request):
    return render(request, 'calendario.html')


@login_required(login_url='/login/')
def eventosCalendario(request):
    """Retorna las órdenes como eventos JSON para FullCalendar.
    Filtra según el rol: cliente → sus vehículos, mecánico → sus asignaciones.
    """
    from django.http import JsonResponse
    qs = OrdenTrabajo.objects.select_related(
        'vehiculo__cliente', 'mecanico__usuario'
    ).all()

    rol = request.user.rol
    es_superuser = request.user.is_superuser

    if rol == 'cliente' and not es_superuser:
        try:
            cliente = request.user.perfil_cliente
            qs = qs.filter(vehiculo__cliente=cliente)
        except Cliente.DoesNotExist:
            qs = qs.none()
    elif rol == 'mecanico' and not es_superuser:
        try:
            mecanico = request.user.perfil_mecanico
            qs = qs.filter(mecanico=mecanico)
        except Mecanico.DoesNotExist:
            qs = qs.none()

    colores = {
        'pendiente' : '#f0ad4e',
        'en_proceso': '#5bc0de',
        'pausada'   : '#999999',
        'finalizada': '#5cb85c',
        'entregada' : '#337ab7',
        'cancelada' : '#d9534f',
    }

    eventos = []
    for o in qs:
        placa    = o.vehiculo.placa
        marca    = f'{o.vehiculo.marca} {o.vehiculo.modelo}'
        estado   = o.get_estado_display()
        cliente_nombre = (
            f'{o.vehiculo.cliente.nombre} {o.vehiculo.cliente.apellido}'
        )
        mecanico_nombre = (
            o.mecanico.usuario.get_full_name()
            if o.mecanico else 'Sin asignar'
        )

        # Título adaptado al rol
        if rol == 'cliente' and not es_superuser:
            # El cliente ve su placa y el estado
            titulo = f'{placa} — {estado}'
        elif rol == 'mecanico' and not es_superuser:
            # El mecánico ve la placa y el cliente
            titulo = f'{placa} ({cliente_nombre})'
        else:
            # Admin / oficinista ven todo
            titulo = f'{placa} · {cliente_nombre} · {estado}'

        eventos.append({
            'id'         : o.id,
            'title'      : titulo,
            'start'      : o.fecha_ingreso.isoformat(),
            'end'        : o.fecha_estimada_entrega.isoformat() if o.fecha_estimada_entrega else None,
            'color'      : colores.get(o.estado, '#777777'),
            'url'        : f'/ordenes/{o.id}/',
            'extendedProps': {
                'descripcion': o.descripcion,
                'mecanico'   : mecanico_nombre,
                'estado'     : estado,
                'marca'      : marca,
            },
        })
    return JsonResponse(eventos, safe=False)


# ══════════════════════════════════════════════════
#  REPORTES  (solo Administrador)
# ══════════════════════════════════════════════════
@login_required(login_url='/login/')
@solo_roles('admin')
def reporteIndex(request):
    """Hub / landing del módulo de reportes."""
    from django.db.models import Count, Q
    ctx = {}
    ctx['total_ordenes']       = OrdenTrabajo.objects.count()
    ctx['ordenes_finalizadas'] = OrdenTrabajo.objects.filter(estado='finalizada').count()
    ctx['total_mecanicos']     = Mecanico.objects.filter(activo=True).count()
    ctx['repuestos_bajo_stock']= Repuesto.objects.filter(stock__lte=3).count()
    return render(request, 'reportes/index.html', ctx)


@login_required(login_url='/login/')
@solo_roles('admin')
def reporteEficiencia(request):
    """Reporte de eficiencia operativa por mecánico."""
    import json
    from django.db.models import Count, Q, Avg, F, ExpressionWrapper, fields

    mecanicos_qs = Mecanico.objects.filter(activo=True).select_related('usuario').annotate(
        total_ordenes      = Count('ordenes'),
        ordenes_finalizadas= Count('ordenes', filter=Q(ordenes__estado='finalizada')),
        en_proceso         = Count('ordenes', filter=Q(ordenes__estado='en_proceso')),
    )

    # Calcular tiempo promedio y % eficiencia en Python (no todos los backends
    # soportan ExpressionWrapper con DurationField sobre DateTimeField nullable)
    mecanicos_data = []
    for m in mecanicos_qs:
        # Tiempo promedio de resolución (solo órdenes finalizadas con fecha real)
        ordenes_con_fecha = OrdenTrabajo.objects.filter(
            mecanico=m,
            estado='finalizada',
            fecha_real_entrega__isnull=False,
        )
        tiempos = [
            (o.fecha_real_entrega - o.fecha_ingreso).days
            for o in ordenes_con_fecha
            if o.fecha_real_entrega and o.fecha_ingreso
        ]
        m.tiempo_promedio_dias = round(sum(tiempos) / len(tiempos), 1) if tiempos else None
        m.eficiencia_pct = (
            round(m.ordenes_finalizadas / m.total_ordenes * 100, 1)
            if m.total_ordenes else 0
        )
        mecanicos_data.append(m)

    total_ordenes_global     = sum(m.total_ordenes      for m in mecanicos_data)
    total_finalizadas_global = sum(m.ordenes_finalizadas for m in mecanicos_data)
    eficiencia_global = (
        round(total_finalizadas_global / total_ordenes_global * 100, 1)
        if total_ordenes_global else 0
    )

    ctx = {
        'mecanicos'               : mecanicos_data,
        'total_mecanicos'         : len(mecanicos_data),
        'total_ordenes_global'    : total_ordenes_global,
        'total_finalizadas_global': total_finalizadas_global,
        'eficiencia_global'       : eficiencia_global,
        'nombres_json'    : json.dumps([
            m.usuario.get_full_name() or m.usuario.username for m in mecanicos_data
        ]),
        'asignadas_json'  : json.dumps([m.total_ordenes       for m in mecanicos_data]),
        'finalizadas_json': json.dumps([m.ordenes_finalizadas  for m in mecanicos_data]),
        'eficiencias_json': json.dumps([m.eficiencia_pct       for m in mecanicos_data]),
    }
    return render(request, 'reportes/eficiencia.html', ctx)


@login_required(login_url='/login/')
@solo_roles('admin')
def reporteRepuestos(request):
    """Reporte de margen de ganancia y stock por repuesto."""
    import json
    from decimal import Decimal

    repuestos_qs = list(Repuesto.objects.all().order_by('nombre'))

    # Anotar campos calculados en Python
    for r in repuestos_qs:
        r.ganancia_unitaria   = round(r.precio_venta - r.precio_costo, 2)
        r.ganancia_stock_total= round(r.ganancia_unitaria * r.stock, 2)

    total_repuestos   = len(repuestos_qs)
    ganancia_potencial= round(sum(r.ganancia_stock_total for r in repuestos_qs), 2)
    margen_promedio   = (
        round(sum(float(r.margen_ganancia) for r in repuestos_qs) / total_repuestos, 1)
        if total_repuestos else 0
    )
    criticos      = [r for r in repuestos_qs if r.stock <= 3]
    stock_critico = len(criticos)
    stock_medio   = sum(1 for r in repuestos_qs if 4 <= r.stock <= 10)
    stock_ok      = sum(1 for r in repuestos_qs if r.stock > 10)

    ctx = {
        'repuestos'         : repuestos_qs,
        'criticos'          : criticos,
        'total_repuestos'   : total_repuestos,
        'ganancia_potencial': ganancia_potencial,
        'margen_promedio'   : margen_promedio,
        'repuestos_criticos': stock_critico,
        'stock_ok'          : stock_ok,
        'stock_medio'       : stock_medio,
        'stock_critico'     : stock_critico,
        'nombres_json'      : json.dumps([r.nombre for r in repuestos_qs]),
        'margenes_json'     : json.dumps([float(r.margen_ganancia) for r in repuestos_qs]),
    }
    return render(request, 'reportes/repuestos.html', ctx)


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def reporteClientes(request):
    """Reporte imprimible de clientes."""
    clientes = Cliente.objects.all()
    return render(request, 'clientes/reporteClientes.html', {'clientes': clientes})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def reporteVehiculos(request):
    vehiculos = Vehiculo.objects.select_related('cliente').all()
    return render(request, 'vehiculos/reporteVehiculos.html', {'vehiculos': vehiculos})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def reporteOrdenes(request):
    ordenes = OrdenTrabajo.objects.select_related('vehiculo__cliente').all().order_by('-fecha_ingreso')
    return render(request, 'ordenes/reporteOrdenes.html', {'ordenes': ordenes})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def reporteRepuestosTabla(request):
    repuestos = Repuesto.objects.all()
    return render(request, 'repuestos/reporteRepuestos.html', {'repuestos': repuestos})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def reporteBahias(request):
    bahias = Bahia.objects.all().order_by('numero')
    return render(request, 'bahias/reporteBahias.html', {'bahias': bahias})


@login_required(login_url='/login/')
@solo_roles('admin', 'oficinista')
def reporteMecanicos(request):
    mecanicos = Mecanico.objects.select_related('usuario').all()
    return render(request, 'mecanicos/reporteMecanicos.html', {'mecanicos': mecanicos})
