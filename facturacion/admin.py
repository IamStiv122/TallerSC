from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Cliente, Mecanico,
    Vehiculo, Bahia, Repuesto,
    OrdenTrabajo, DetalleRepuesto,
    InspeccionInicial, HistorialOrden,
)


# ── Usuario personalizado ──────────────────────────────
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Datos del Taller', {'fields': ('rol', 'telefono', 'foto')}),
    )
    list_display  = ('username', 'get_full_name', 'email', 'rol', 'is_active')
    list_filter   = ('rol', 'is_active')


# ── Cliente ────────────────────────────────────────────
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display  = ('cedula', 'nombre', 'apellido', 'telefono', 'email')
    search_fields = ('cedula', 'nombre', 'apellido')


# ── Mecánico ───────────────────────────────────────────
@admin.register(Mecanico)
class MecanicoAdmin(admin.ModelAdmin):
    list_display  = ('usuario', 'especialidad', 'activo')
    list_filter   = ('especialidad', 'activo')


# ── Vehículo ───────────────────────────────────────────
@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display  = ('placa', 'marca', 'modelo', 'anio', 'cliente')
    search_fields = ('placa', 'marca', 'modelo')
    list_filter   = ('marca', 'tipo')


# ── Bahía ──────────────────────────────────────────────
@admin.register(Bahia)
class BahiaAdmin(admin.ModelAdmin):
    list_display  = ('numero', 'nombre', 'estado')
    list_filter   = ('estado',)


# ── Repuesto ───────────────────────────────────────────
@admin.register(Repuesto)
class RepuestoAdmin(admin.ModelAdmin):
    list_display  = ('codigo', 'nombre', 'precio_costo', 'precio_venta', 'stock', 'margen_ganancia')
    search_fields = ('codigo', 'nombre')


# ── Detalle de Repuesto (inline) ───────────────────────
class DetalleRepuestoInline(admin.TabularInline):
    model  = DetalleRepuesto
    extra  = 1
    fields = ('repuesto', 'cantidad', 'precio_unitario', 'subtotal')
    readonly_fields = ('subtotal',)


# ── Historial de Orden (inline) ────────────────────────
class HistorialOrdenInline(admin.TabularInline):
    model           = HistorialOrden
    extra           = 0
    readonly_fields = ('estado_anterior', 'estado_nuevo', 'cambiado_por', 'fecha')
    can_delete      = False


# ── Orden de Trabajo ───────────────────────────────────
@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display   = ('numero', 'vehiculo', 'mecanico', 'bahia',
                      'estado', 'fecha_ingreso', 'fecha_estimada_entrega', 'total')
    list_filter    = ('estado', 'mecanico', 'bahia')
    search_fields  = ('numero', 'vehiculo__placa')
    readonly_fields = ('creado_en', 'actualizado_en', 'total_repuestos')
    inlines        = [DetalleRepuestoInline, HistorialOrdenInline]


# ── Inspección Inicial ─────────────────────────────────
@admin.register(InspeccionInicial)
class InspeccionInicialAdmin(admin.ModelAdmin):
    list_display  = ('orden', 'realizada_por', 'fecha')
    search_fields = ('orden__numero',)


# ── Historial de Orden ─────────────────────────────────
@admin.register(HistorialOrden)
class HistorialOrdenAdmin(admin.ModelAdmin):
    list_display  = ('orden', 'estado_anterior', 'estado_nuevo', 'cambiado_por', 'fecha')
    list_filter   = ('estado_nuevo',)
    readonly_fields = ('fecha',)
