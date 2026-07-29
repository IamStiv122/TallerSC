from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from .models import (
    Usuario, Cliente, Mecanico, Vehiculo, Bahia, OrdenTrabajo,
)
from .email_utils import enviar_notificaciones_orden


class EmailNotificationsTests(TestCase):
    def setUp(self):
        self.bahia = Bahia.objects.create(numero=1, nombre='Bahía 1')
        self.cliente_user = Usuario.objects.create_user(
            username='cliente-mail', password='123456', rol='cliente',
            first_name='Cliente', last_name='Correo', email='cliente@example.com'
        )
        self.cliente = Cliente.objects.create(
            usuario=self.cliente_user,
            cedula='1234567890',
            nombre='Cliente',
            apellido='Correo',
            telefono='0999999999',
            email='cliente@example.com',
        )
        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente, placa='ABC999', marca='Toyota', modelo='Corolla', anio=2020
        )
        self.mecanico_user = Usuario.objects.create_user(
            username='mecanico-mail', password='123456', rol='mecanico',
            first_name='Mecánico', last_name='Correo', email='mecanico@example.com'
        )
        self.mecanico = Mecanico.objects.create(usuario=self.mecanico_user, activo=True)
        self.orden = OrdenTrabajo.objects.create(
            vehiculo=self.vehiculo,
            mecanico=self.mecanico,
            numero='OT-EMAIL-1',
            descripcion='Revisión general',
            fecha_ingreso=timezone.now(),
            bahia=self.bahia,
        )

    def test_envia_notificaciones_al_crear_orden(self):
        with patch('facturacion.email_utils.send_mail') as mock_send:
            enviar_notificaciones_orden(self.orden, evento='creada')

        self.assertGreaterEqual(mock_send.call_count, 2)
        destinatarios = []
        for call in mock_send.call_args_list:
            destinatarios.extend(call.args[3])
        self.assertIn('cliente@example.com', destinatarios)
        self.assertIn('mecanico@example.com', destinatarios)

    def test_envia_notificaciones_al_finalizar_orden(self):
        with patch('facturacion.email_utils.send_mail') as mock_send:
            enviar_notificaciones_orden(self.orden, evento='finalizada')

        self.assertGreaterEqual(mock_send.call_count, 2)
