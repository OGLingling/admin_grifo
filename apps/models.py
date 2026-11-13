from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    class Category(models.TextChoices):
        FUEL = "fuel", "Combustible"
        STORE = "store", "Tienda / lubricante"

    class Unit(models.TextChoices):
        LITER = "L", "Litros"
        UNIT = "UND", "Unidades"

    name = models.CharField("nombre", max_length=100)
    sku = models.CharField("código", max_length=32, unique=True)
    category = models.CharField("categoría", max_length=12, choices=Category.choices)
    unit = models.CharField("unidad", max_length=5, choices=Unit.choices)
    unit_cost = models.DecimalField("costo unitario", max_digits=10, decimal_places=3,
                                    validators=[MinValueValidator(Decimal("0.001"))])
    unit_price = models.DecimalField("precio de venta", max_digits=10, decimal_places=3,
                                     validators=[MinValueValidator(Decimal("0.001"))])
    stock_quantity = models.DecimalField("existencia", max_digits=12, decimal_places=3,
                                         default=Decimal("0"), validators=[MinValueValidator(0)])
    is_active = models.BooleanField("activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "productos"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.sku})"


class Tank(models.Model):
    code = models.CharField("código", max_length=24, unique=True)
    product = models.ForeignKey(Product, verbose_name="combustible", on_delete=models.PROTECT,
                                related_name="tanks", limit_choices_to={"category": "fuel"})
    capacity = models.DecimalField("capacidad (L)", max_digits=12, decimal_places=3,
                                   validators=[MinValueValidator(Decimal("0.001"))])
    current_stock = models.DecimalField("existencia (L)", max_digits=12, decimal_places=3,
                                        default=Decimal("0"), validators=[MinValueValidator(0)])
    warning_level = models.DecimalField("alerta de mínimo (L)", max_digits=12, decimal_places=3,
                                        default=Decimal("500"), validators=[MinValueValidator(0)])
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "tanques"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} · {self.product.name}"

    @property
    def fill_percent(self):
        if not self.capacity:
            return 0
        return min(100, int(self.current_stock * 100 / self.capacity))


class CashSession(models.Model):
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="abierta por",
                                  on_delete=models.PROTECT, related_name="cash_sessions")
    opened_at = models.DateTimeField("apertura", auto_now_add=True)
    opening_amount = models.DecimalField("fondo inicial", max_digits=12, decimal_places=2,
                                         default=Decimal("0"), validators=[MinValueValidator(0)])
    closed_at = models.DateTimeField("cierre", null=True, blank=True)
    closing_amount = models.DecimalField("efectivo contado", max_digits=12, decimal_places=2,
                                         null=True, blank=True, validators=[MinValueValidator(0)])
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="cerrada por",
                                  on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="closed_cash_sessions")

    class Meta:
        db_table = "cajas"
        ordering = ["-opened_at"]

    def __str__(self):
        return f"Caja #{self.pk} · {self.opened_at:%d/%m/%Y %H:%M}"

    @property
    def is_open(self):
        return self.closed_at is None

    @property
    def closing_difference(self):
        if self.closed_at is None or self.closing_amount is None:
            return None
        cash_sales = self.sales.filter(payment_method="cash").aggregate(total=models.Sum("total"))["total"] or Decimal("0")
        movement_totals = self.movements.values("direction").annotate(total=models.Sum("amount"))
        amounts = {row["direction"]: row["total"] or Decimal("0") for row in movement_totals}
        expected = self.opening_amount + cash_sales + amounts.get("in", Decimal("0")) - amounts.get("out", Decimal("0"))
        return (self.closing_amount - expected).quantize(Decimal("0.01"))


class Purchase(models.Model):
    product = models.ForeignKey(Product, verbose_name="producto", on_delete=models.PROTECT,
                                related_name="purchases")
    tank = models.ForeignKey(Tank, verbose_name="tanque", on_delete=models.PROTECT,
                             null=True, blank=True, related_name="purchases")
    supplier = models.CharField("proveedor", max_length=120)
    reference = models.CharField("documento", max_length=60, blank=True)
    quantity = models.DecimalField("cantidad", max_digits=12, decimal_places=3,
                                   validators=[MinValueValidator(Decimal("0.001"))])
    unit_cost = models.DecimalField("costo unitario", max_digits=10, decimal_places=3,
                                    validators=[MinValueValidator(Decimal("0.001"))])
    total = models.DecimalField("total", max_digits=13, decimal_places=2)
    purchased_at = models.DateTimeField("registrada", auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        db_table = "compras"
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"Compra #{self.pk} · {self.product.name}"


class Sale(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Efectivo"
        CARD = "card", "Tarjeta"
        TRANSFER = "transfer", "Transferencia / billetera"

    product = models.ForeignKey(Product, verbose_name="producto", on_delete=models.PROTECT,
                                related_name="sales")
    tank = models.ForeignKey(Tank, verbose_name="tanque", on_delete=models.PROTECT,
                             null=True, blank=True, related_name="sales")
    cash_session = models.ForeignKey(CashSession, verbose_name="caja", on_delete=models.PROTECT,
                                     related_name="sales")
    quantity = models.DecimalField("cantidad", max_digits=12, decimal_places=3,
                                   validators=[MinValueValidator(Decimal("0.001"))])
    unit_price = models.DecimalField("precio unitario", max_digits=10, decimal_places=3,
                                     validators=[MinValueValidator(Decimal("0.001"))])
    total = models.DecimalField("total", max_digits=13, decimal_places=2)
    payment_method = models.CharField("medio de pago", max_length=12,
                                      choices=PaymentMethod.choices)
    sold_at = models.DateTimeField("registrada", auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        db_table = "ventas"
        ordering = ["-sold_at"]

    def __str__(self):
        return f"Venta #{self.pk} · S/ {self.total}"


class CashMovement(models.Model):
    class Direction(models.TextChoices):
        IN = "in", "Ingreso"
        OUT = "out", "Egreso"

    cash_session = models.ForeignKey(CashSession, verbose_name="caja", on_delete=models.PROTECT,
                                     related_name="movements")
    direction = models.CharField("tipo", max_length=3, choices=Direction.choices)
    description = models.CharField("concepto", max_length=160)
    amount = models.DecimalField("monto", max_digits=12, decimal_places=2,
                                 validators=[MinValueValidator(Decimal("0.01"))])
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        db_table = "movimientos_caja"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_direction_display()} · S/ {self.amount}"
