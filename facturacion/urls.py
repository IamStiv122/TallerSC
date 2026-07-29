from django.urls import path
from . import views

app_name = 'facturacion'

urlpatterns = [

    # ── Autenticación ──────────────────────────────────
    path('login/',  views.loginVista),
    path('logout/', views.logoutVista),

    # ── Inicio / Dashboard ─────────────────────────────
    path('',           views.inicio),
    path('inicio/',    views.inicio),
    path('dashboard/', views.dashboard),

    # ── Clientes ───────────────────────────────────────
    path('clientes/',                views.listadoClientes),
    path('clientes/nuevo/',          views.nuevoCliente),
    path('clientes/guardar/',        views.guardarCliente),
    path('clientes/editar/<int:id>/',views.editarCliente),
    path('clientes/actualizar/',     views.actualizarCliente),
    path('clientes/eliminar/<int:id>/', views.eliminarCliente),

    # ── Vehículos ──────────────────────────────────────
    path('vehiculos/',                  views.listadoVehiculos),
    path('vehiculos/nuevo/',            views.nuevoVehiculo),
    path('vehiculos/guardar/',          views.guardarVehiculo),
    path('vehiculos/editar/<int:id>/',  views.editarVehiculo),
    path('vehiculos/actualizar/',       views.actualizarVehiculo),
    path('vehiculos/eliminar/<int:id>/',views.eliminarVehiculo),

    # ── Órdenes de Trabajo ─────────────────────────────
    path('ordenes/',                   views.listadoOrdenes, name='listado_ordenes'),
    path('ordenes/nueva/',             views.nuevaOrden),
    path('ordenes/guardar/',           views.guardarOrden),
    path('ordenes/<int:id>/',          views.detalleOrden),
    path('ordenes/editar/<int:id>/',   views.editarOrden),
    path('ordenes/actualizar/',        views.actualizarOrden),
    path('ordenes/estado/<int:id>/',   views.cambiarEstadoOrden),
    path('ordenes/eliminar/<int:id>/', views.eliminarOrden),

    # ── Repuestos en la Orden ──────────────────────────
    path('ordenes/<int:orden_id>/repuesto/',         views.agregarRepuesto),
    path('ordenes/<int:orden_id>/repuesto/guardar/', views.guardarRepuesto),
    path('repuesto-orden/eliminar/<int:id>/',        views.eliminarRepuesto),

    # ── Inspección Inicial ─────────────────────────────
    path('ordenes/<int:orden_id>/inspeccion/',         views.inspeccionOrden),
    path('ordenes/<int:orden_id>/inspeccion/guardar/', views.guardarInspeccion),

    # ── Repuestos (inventario) ─────────────────────────
    path('repuestos/',                  views.listadoRepuestos),
    path('repuestos/nuevo/',            views.nuevoRepuesto),
    path('repuestos/guardar/',          views.guardarRepuestoInventario),
    path('repuestos/editar/<int:id>/',  views.editarRepuesto),
    path('repuestos/actualizar/',       views.actualizarRepuesto),
    path('repuestos/eliminar/<int:id>/',views.eliminarRepuesto),

    # ── Bahías ─────────────────────────────────────────
    path('bahias/',                   views.listadoBahias),
    path('bahias/nueva/',             views.nuevaBahia),
    path('bahias/guardar/',           views.guardarBahia),
    path('bahias/editar/<int:id>/',   views.editarBahia),
    path('bahias/actualizar/',        views.actualizarBahia),
    path('bahias/posicion/<int:id>/', views.actualizarPosicionBahia),
    path('bahias/orden/<int:orden_id>/<int:bahia_id>/', views.asignarOrdenBahia),
    path('bahias/eliminar/<int:id>/', views.eliminarBahia),

    # ── Mecánicos ──────────────────────────────────────
    path('mecanicos/',                   views.listadoMecanicos),
    path('mecanicos/nuevo/',             views.nuevoMecanico),
    path('mecanicos/guardar/',           views.guardarMecanico),
    path('mecanicos/editar/<int:id>/',   views.editarMecanico),
    path('mecanicos/actualizar/',        views.actualizarMecanico),
    path('mecanicos/eliminar/<int:id>/', views.eliminarMecanico),

    # ── Calendario ─────────────────────────────────────
    path('calendario/',         views.calendario),
    path('calendario/eventos/', views.eventosCalendario),

    # ── Reportes (solo admin) ──────────────────────────
    path('reportes/',            views.reporteIndex),
    path('reportes/eficiencia/', views.reporteEficiencia),
    path('reportes/repuestos/',  views.reporteRepuestos),
    path('reportes/clientes/',   views.reporteClientes),

    # ── Reportes HTML por tabla ───────────────────────
    path('vehiculos/reporte/', views.reporteVehiculos),
    path('ordenes/reporte/', views.reporteOrdenes),
    path('repuestos/reporte/', views.reporteRepuestosTabla),
    path('bahias/reporte/', views.reporteBahias),
    path('mecanicos/reporte/', views.reporteMecanicos),
]
