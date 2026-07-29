from django.db import models
from django.contrib.auth.models import AbstractUser


# ─────────────────────────────────────────────
# USUARIO PERSONALIZADO (extiende django.auth)
# Roles: admin, oficinista, cliente, mecanico
# ─────────────────────────────────────────────
class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('admin',      'Administrador'),
        ('oficinista', 'Oficinista'),
        ('cliente',    'Cliente'),
        ('mecanico',   'Mecánico'),
    ]
    rol      = models.CharField(max_length=20, choices=ROL_CHOICES, default='cliente')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    foto     = models.ImageField(upload_to='usuarios/', blank=True, null=True)

    def __str__(self):
        return f"{self.get_full_name()} [{self.get_rol_display()}]"

    # Helpers de rol rápidos
    @property
    def es_admin(self):
        return self.rol == 'admin' or self.is_superuser

    @property
    def es_oficinista(self):
        return self.rol == 'oficinista'

    @property
    def es_cliente(self):
        return self.rol == 'cliente'

    @property
    def es_mecanico(self):
        return self.rol == 'mecanico'


# ─────────────────────────────────────────────
# CLIENTE  (perfil extendido del Usuario)
# Creado por el Oficinista
# ─────────────────────────────────────────────
class Cliente(models.Model):
    usuario   = models.OneToOneField(
        Usuario, on_delete=models.CASCADE,
        related_name='perfil_cliente', null=True, blank=True
    )
    cedula    = models.CharField(max_length=20, unique=True)
    nombre    = models.CharField(max_length=100)
    apellido  = models.CharField(max_length=100)
    telefono  = models.CharField(max_length=20)
    email     = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido} – CI: {self.cedula}"


# ─────────────────────────────────────────────
# MECÁNICO  (perfil extendido del Usuario)
# ─────────────────────────────────────────────
class Mecanico(models.Model):
    ESPECIALIDAD_CHOICES = [
        ('general',      'Mecánica General'),
        ('electrico',    'Sistema Eléctrico'),
        ('transmision',  'Transmisión'),
        ('suspension',   'Suspensión y Frenos'),
        ('carroceria',   'Carrocería y Pintura'),
    ]
    usuario       = models.OneToOneField(
        Usuario, on_delete=models.CASCADE,
        related_name='perfil_mecanico'
    )
    especialidad  = models.CharField(
        max_length=30, choices=ESPECIALIDAD_CHOICES, default='general'
    )
    activo        = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario.get_full_name()} – {self.get_especialidad_display()}"


# ─────────────────────────────────────────────
# VEHÍCULO
# Registrado por el Oficinista, pertenece a un Cliente
# ─────────────────────────────────────────────
class Vehiculo(models.Model):
    cliente       = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name='vehiculos'
    )
    placa         = models.CharField(max_length=10, unique=True)
    marca         = models.CharField(max_length=60)
    modelo        = models.CharField(max_length=60)
    anio          = models.PositiveIntegerField()
    color         = models.CharField(max_length=40, blank=True, null=True)
    tipo          = models.CharField(
        max_length=30,
        choices=[('sedan','Sedán'),('suv','SUV'),('pickup','Pick-up'),
                 ('hatchback','Hatchback'),('furgon','Furgón'),('otro','Otro')],
        default='sedan'
    )

    def __str__(self):
        return f"{self.placa} – {self.marca} {self.modelo} {self.anio}"


# ─────────────────────────────────────────────
# BAHÍA / ELEVADOR
# Distribución visual por drag & drop (jQuery UI)
# Dashboard: Ocupado / Libre / En Espera
# ─────────────────────────────────────────────
class Bahia(models.Model):
    ESTADO_CHOICES = [
        ('libre',     'Libre'),
        ('ocupada',   'Ocupada'),
        ('en_espera', 'En Espera'),
    ]
    numero      = models.PositiveIntegerField(unique=True)
    nombre      = models.CharField(max_length=60)   # ej. "Bahía 1 – Elevador"
    estado      = models.CharField(
        max_length=15, choices=ESTADO_CHOICES, default='libre'
    )
    descripcion = models.TextField(blank=True, null=True)

    # Posición en el plano visual (para drag & drop)
    pos_x       = models.PositiveIntegerField(default=0)
    pos_y       = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.nombre} – {self.get_estado_display()}"


# ─────────────────────────────────────────────
# REPUESTO
# Inventario de piezas utilizadas en las órdenes
# ─────────────────────────────────────────────
class Repuesto(models.Model):
    codigo      = models.CharField(max_length=40, unique=True)
    nombre      = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, null=True)
    precio_costo  = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta  = models.DecimalField(max_digits=10, decimal_places=2)
    stock         = models.PositiveIntegerField(default=0)
    unidad        = models.CharField(max_length=20, default='unidad')

    def __str__(self):
        return f"[{self.codigo}] {self.nombre}"

    @property
    def margen_ganancia(self):
        """Retorna el margen de ganancia en porcentaje."""
        if self.precio_costo > 0:
            return round(
                ((self.precio_venta - self.precio_costo) / self.precio_costo) * 100, 2
            )
        return 0


# ─────────────────────────────────────────────
# ORDEN DE TRABAJO
# Creada por Oficinista; trabajada por Mecánico
# Visible por el Cliente (calendario + detalle)
# ─────────────────────────────────────────────
class OrdenTrabajo(models.Model):
    ESTADO_CHOICES = [
        ('pendiente',   'Pendiente'),
        ('en_proceso',  'En Proceso'),
        ('pausada',     'Pausada'),
        ('finalizada',  'Finalizada'),
        ('entregada',   'Entregada'),
        ('cancelada',   'Cancelada'),
    ]

    # Relaciones principales
    vehiculo  = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, related_name='ordenes'
    )
    mecanico  = models.ForeignKey(
        Mecanico, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ordenes'
    )
    bahia     = models.ForeignKey(
        Bahia, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ordenes'
    )
    creada_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, related_name='ordenes_creadas'
    )

    # Datos de la orden
    numero          = models.CharField(max_length=20, unique=True)
    estado          = models.CharField(
        max_length=15, choices=ESTADO_CHOICES, default='pendiente'
    )
    descripcion     = models.TextField(help_text="Problema reportado por el cliente")
    observaciones   = models.TextField(blank=True, null=True,
                                       help_text="Notas internas del mecánico")
    kilometraje_ingreso = models.PositiveIntegerField(default=0)

    # Calendario (FullCalendar)
    fecha_ingreso   = models.DateTimeField()
    fecha_estimada_entrega = models.DateTimeField(null=True, blank=True)
    fecha_real_entrega     = models.DateTimeField(null=True, blank=True)

    # Costos
    mano_obra       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_repuestos = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Auditoría
    creado_en       = models.DateTimeField(auto_now_add=True)
    actualizado_en  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OT-{self.numero} | {self.vehiculo} | {self.get_estado_display()}"

    @property
    def total(self):
        return self.mano_obra + self.total_repuestos

    def save(self, *args, **kwargs):
        """Sincroniza el estado de la bahía al guardar la orden.
        Solo actualiza la bahía si el estado es en_proceso, finalizada,
        entregada o cancelada. El estado 'pendiente' no toca la bahía
        porque la asignación se hace después, desde el módulo de bahías.
        """
        # Capturar bahía anterior antes de guardar (para limpiarla si cambia)
        bahia_anterior = None
        if self.pk:
            try:
                bahia_anterior = OrdenTrabajo.objects.get(pk=self.pk).bahia
            except OrdenTrabajo.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Si la bahía cambió y la anterior ya no tiene órdenes activas → librarla
        if bahia_anterior and bahia_anterior != self.bahia:
            otras = OrdenTrabajo.objects.filter(
                bahia=bahia_anterior,
                estado__in=('pendiente', 'en_proceso')
            ).exclude(pk=self.pk)
            if not otras.exists():
                bahia_anterior.estado = 'libre'
                bahia_anterior.save(update_fields=['estado'])

        # Sincronizar la bahía actual solo cuando el estado es activo
        if self.bahia:
            if self.estado == 'en_proceso':
                nuevo_estado = 'ocupada'
            elif self.estado in ('finalizada', 'entregada', 'cancelada'):
                otras = OrdenTrabajo.objects.filter(
                    bahia=self.bahia,
                    estado__in=('pendiente', 'en_proceso')
                ).exclude(pk=self.pk)
                nuevo_estado = 'libre' if not otras.exists() else 'ocupada'
            else:
                # pendiente, pausada: no cambia el estado de la bahía
                return
            if self.bahia.estado != nuevo_estado:
                self.bahia.estado = nuevo_estado
                self.bahia.save(update_fields=['estado'])


# ─────────────────────────────────────────────
# DETALLE DE REPUESTOS POR ORDEN
# Relación M:N entre OrdenTrabajo y Repuesto
# ─────────────────────────────────────────────
class DetalleRepuesto(models.Model):
    orden    = models.ForeignKey(
        OrdenTrabajo, on_delete=models.CASCADE, related_name='detalle_repuestos'
    )
    repuesto = models.ForeignKey(
        Repuesto, on_delete=models.PROTECT, related_name='usos'
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.repuesto.nombre} x{self.cantidad} → OT-{self.orden.numero}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def save(self, *args, **kwargs):
        """Copia el precio de venta actual si no se especificó."""
        if not self.precio_unitario:
            self.precio_unitario = self.repuesto.precio_venta
        super().save(*args, **kwargs)
        # Recalcula el total de repuestos en la orden
        total = sum(
            d.subtotal for d in self.orden.detalle_repuestos.all()
        )
        self.orden.total_repuestos = total
        self.orden.save(update_fields=['total_repuestos'])


# ─────────────────────────────────────────────
# INSPECCIÓN INICIAL (guía de 20 puntos – Driver.js)
# ─────────────────────────────────────────────
class InspeccionInicial(models.Model):
    ESTADO_PUNTO = [
        ('ok',     'OK'),
        ('alerta', 'Alerta'),
        ('falla',  'Falla'),
        ('na',     'No Aplica'),
    ]

    orden = models.OneToOneField(
        OrdenTrabajo, on_delete=models.CASCADE, related_name='inspeccion'
    )
    # Los 20 puntos de inspección
    p01_frenos_delanteros   = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p02_frenos_traseros     = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p03_aceite_motor        = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p04_liquido_frenos      = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p05_liquido_refrigerante= models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p06_bateria             = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p07_alternador          = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p08_filtro_aire         = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p09_bujias              = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p10_correa_distribucion = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p11_suspension_delantera= models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p12_suspension_trasera  = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p13_neumaticos          = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p14_alineacion          = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p15_escape              = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p16_transmision         = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p17_direccion           = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p18_luces               = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p19_limpiabrisas        = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')
    p20_carroceria_visual   = models.CharField(max_length=6, choices=ESTADO_PUNTO, default='na')

    observaciones_generales = models.TextField(blank=True, null=True)
    realizada_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, related_name='inspecciones'
    )
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inspección OT-{self.orden.numero}"


# ─────────────────────────────────────────────
# HISTORIAL DE ESTADO DE LA ORDEN
# Trazabilidad completa (quién cambió, cuándo, a qué estado)
# ─────────────────────────────────────────────
class HistorialOrden(models.Model):
    orden      = models.ForeignKey(
        OrdenTrabajo, on_delete=models.CASCADE, related_name='historial'
    )
    estado_anterior = models.CharField(max_length=15, blank=True, null=True)
    estado_nuevo    = models.CharField(max_length=15)
    observacion     = models.TextField(blank=True, null=True)
    cambiado_por    = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True
    )
    fecha           = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return (
            f"OT-{self.orden.numero}: "
            f"{self.estado_anterior} → {self.estado_nuevo} "
            f"({self.fecha:%d/%m/%Y %H:%M})"
        )
