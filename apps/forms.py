from decimal import Decimal

from django import forms

from .models import CashMovement, Product, Purchase, Sale, Tank


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field-control")


class ProductSelect(forms.Select):
    """Adjunta el precio al option para mostrarlo al seleccionar el producto."""
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        queryset = getattr(self.choices, "queryset", None)
        if value and queryset is not None:
            try:
                option["attrs"]["data-unit-price"] = str(queryset.get(pk=value).unit_price)
            except (Product.DoesNotExist, ValueError, TypeError):
                pass
        return option


class ProductForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "sku", "category", "unit", "unit_cost", "unit_price", "is_active"]
        widgets = {"unit_cost": forms.NumberInput(attrs={"step": "0.001"}),
                   "unit_price": forms.NumberInput(attrs={"step": "0.001"})}

    def clean(self):
        data = super().clean()
        if data.get("category") == Product.Category.FUEL and data.get("unit") != Product.Unit.LITER:
            self.add_error("unit", "Los combustibles se controlan en litros.")
        if self.instance.pk and data.get("category") != self.instance.category:
            has_history = (self.instance.tanks.exists() or self.instance.purchases.exists()
                           or self.instance.sales.exists())
            if has_history or self.instance.stock_quantity > 0:
                self.add_error("category", "No se puede cambiar la categoría de un producto con inventario o movimientos.")
        return data


class TankForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Tank
        fields = ["code", "product", "capacity", "current_stock", "warning_level", "is_active"]
        widgets = {name: forms.NumberInput(attrs={"step": "0.001"})
                   for name in ("capacity", "current_stock", "warning_level")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(
            category=Product.Category.FUEL, is_active=True
        ).order_by("name")
        if self.instance.pk:
            # Las existencias solo cambian al registrar compras y ventas.
            self.fields["current_stock"].disabled = True

    def clean(self):
        data = super().clean()
        capacity, stock = data.get("capacity"), data.get("current_stock")
        if capacity is not None and stock is not None and stock > capacity:
            self.add_error("current_stock", "La existencia no puede superar la capacidad del tanque.")
        return data


class PurchaseForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ["product", "tank", "supplier", "reference", "quantity", "unit_cost"]
        widgets = {"quantity": forms.NumberInput(attrs={"step": "0.001", "min": "0.001"}),
                   "unit_cost": forms.NumberInput(attrs={"step": "0.001", "min": "0.001"}),
                   "product": ProductSelect()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True).order_by("name")
        self.fields["tank"].queryset = Tank.objects.filter(is_active=True, product__is_active=True).select_related("product")

    def clean(self):
        data = super().clean()
        product, tank = data.get("product"), data.get("tank")
        if product and product.category == Product.Category.FUEL and not tank:
            self.add_error("tank", "Selecciona el tanque que recibe el combustible.")
        if product and product.category != Product.Category.FUEL and tank:
            self.add_error("tank", "Los productos de tienda no se ingresan a un tanque.")
        if product and tank and tank.product_id != product.id:
            self.add_error("tank", "El tanque seleccionado almacena otro combustible.")
        if product and not product.is_active:
            self.add_error("product", "No se pueden registrar compras de productos inactivos.")
        return data


class SaleForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Sale
        fields = ["product", "tank", "quantity", "unit_price", "payment_method"]
        widgets = {"quantity": forms.NumberInput(attrs={"step": "0.001", "min": "0.001"}),
                   "unit_price": forms.NumberInput(attrs={"step": "0.001", "min": "0.001"}),
                   "product": ProductSelect()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True).order_by("name")
        self.fields["tank"].queryset = Tank.objects.filter(is_active=True, product__is_active=True).select_related("product")
        product_id = self.data.get(self.add_prefix("product")) if self.is_bound else None
        product_id = product_id or self.initial.get("product")
        if product_id:
            product = Product.objects.filter(pk=product_id, is_active=True).first()
            if product:
                self.initial["unit_price"] = product.unit_price

    def clean(self):
        data = super().clean()
        product, tank = data.get("product"), data.get("tank")
        if product and product.category == Product.Category.FUEL and not tank:
            self.add_error("tank", "Selecciona el tanque de despacho.")
        if product and product.category != Product.Category.FUEL and tank:
            self.add_error("tank", "Los productos de tienda no usan tanque.")
        if product and tank and tank.product_id != product.id:
            self.add_error("tank", "El tanque seleccionado almacena otro combustible.")
        if product and not product.is_active:
            self.add_error("product", "No se pueden vender productos inactivos.")
        if product and data.get("unit_price") != product.unit_price:
            self.add_error("unit_price", "El precio debe coincidir con el precio de venta del catálogo.")
        return data


class CashMovementForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CashMovement
        fields = ["direction", "description", "amount"]
        widgets = {"amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"})}


class CashOpenForm(StyledFormMixin, forms.Form):
    opening_amount = forms.DecimalField(label="Fondo inicial", min_value=Decimal("0"),
                                        decimal_places=2, max_digits=12,
                                        widget=forms.NumberInput(attrs={"step": "0.01"}))


class CashCloseForm(StyledFormMixin, forms.Form):
    closing_amount = forms.DecimalField(label="Efectivo contado", min_value=Decimal("0"),
                                        decimal_places=2, max_digits=12,
                                        widget=forms.NumberInput(attrs={"step": "0.01"}))
