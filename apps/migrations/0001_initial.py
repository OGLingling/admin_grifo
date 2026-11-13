import decimal

import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="CashSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("opened_at", models.DateTimeField(auto_now_add=True, verbose_name="apertura")),
                ("opening_amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0"), max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="fondo inicial")),
                ("closed_at", models.DateTimeField(blank=True, null=True, verbose_name="cierre")),
                ("closing_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name="efectivo contado")),
                ("closed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="closed_cash_sessions", to=settings.AUTH_USER_MODEL, verbose_name="cerrada por")),
                ("opened_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cash_sessions", to=settings.AUTH_USER_MODEL, verbose_name="abierta por")),
            ],
            options={"db_table": "cajas", "ordering": ["-opened_at"]},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="nombre")),
                ("sku", models.CharField(max_length=32, unique=True, verbose_name="código")),
                ("category", models.CharField(choices=[("fuel", "Combustible"), ("store", "Tienda / lubricante")], max_length=12, verbose_name="categoría")),
                ("unit", models.CharField(choices=[("L", "Litros"), ("UND", "Unidades")], max_length=5, verbose_name="unidad")),
                ("unit_cost", models.DecimalField(decimal_places=3, max_digits=10, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.001"))], verbose_name="costo unitario")),
                ("unit_price", models.DecimalField(decimal_places=3, max_digits=10, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.001"))], verbose_name="precio de venta")),
                ("stock_quantity", models.DecimalField(decimal_places=3, default=decimal.Decimal("0"), max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="existencia")),
                ("is_active", models.BooleanField(default=True, verbose_name="activo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "productos", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Tank",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=24, unique=True, verbose_name="código")),
                ("capacity", models.DecimalField(decimal_places=3, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.001"))], verbose_name="capacidad (L)")),
                ("current_stock", models.DecimalField(decimal_places=3, default=decimal.Decimal("0"), max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="existencia (L)")),
                ("warning_level", models.DecimalField(decimal_places=3, default=decimal.Decimal("500"), max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="alerta de mínimo (L)")),
                ("is_active", models.BooleanField(default=True, verbose_name="activo")),
                ("product", models.ForeignKey(limit_choices_to={"category": "fuel"}, on_delete=django.db.models.deletion.PROTECT, related_name="tanks", to="apps.product", verbose_name="combustible")),
            ],
            options={"db_table": "tanques", "ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="Purchase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("supplier", models.CharField(max_length=120, verbose_name="proveedor")),
                ("reference", models.CharField(blank=True, max_length=60, verbose_name="documento")),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.001"))], verbose_name="cantidad")),
                ("unit_cost", models.DecimalField(decimal_places=3, max_digits=10, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.001"))], verbose_name="costo unitario")),
                ("total", models.DecimalField(decimal_places=2, max_digits=13, verbose_name="total")),
                ("purchased_at", models.DateTimeField(auto_now_add=True, verbose_name="registrada")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="purchases", to="apps.product", verbose_name="producto")),
                ("tank", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="purchases", to="apps.tank", verbose_name="tanque")),
            ],
            options={"db_table": "compras", "ordering": ["-purchased_at"]},
        ),
        migrations.CreateModel(
            name="Sale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.001"))], verbose_name="cantidad")),
                ("unit_price", models.DecimalField(decimal_places=3, max_digits=10, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.001"))], verbose_name="precio unitario")),
                ("total", models.DecimalField(decimal_places=2, max_digits=13, verbose_name="total")),
                ("payment_method", models.CharField(choices=[("cash", "Efectivo"), ("card", "Tarjeta"), ("transfer", "Transferencia / billetera")], max_length=12, verbose_name="medio de pago")),
                ("sold_at", models.DateTimeField(auto_now_add=True, verbose_name="registrada")),
                ("cash_session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="apps.cashsession", verbose_name="caja")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="apps.product", verbose_name="producto")),
                ("tank", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="apps.tank", verbose_name="tanque")),
            ],
            options={"db_table": "ventas", "ordering": ["-sold_at"]},
        ),
        migrations.CreateModel(
            name="CashMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("direction", models.CharField(choices=[("in", "Ingreso"), ("out", "Egreso")], max_length=3, verbose_name="tipo")),
                ("description", models.CharField(max_length=160, verbose_name="concepto")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))], verbose_name="monto")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("cash_session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movements", to="apps.cashsession", verbose_name="caja")),
            ],
            options={"db_table": "movimientos_caja", "ordering": ["-created_at"]},
        ),
    ]
