from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (CashCloseForm, CashMovementForm, CashOpenForm, ProductForm,
                    PurchaseForm, SaleForm, TankForm)
from .models import CashMovement, CashSession, Product, Purchase, Sale, Tank


def _money(value):
    return (value or Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _active_cash():
    return CashSession.objects.filter(closed_at__isnull=True).order_by("-opened_at").first()


def _cash_summary(session):
    if not session:
        return {"expected": Decimal("0.00"), "cash_sales": Decimal("0.00"),
                "income": Decimal("0.00"), "expenses": Decimal("0.00")}
    sales = session.sales.filter(payment_method=Sale.PaymentMethod.CASH).aggregate(total=Sum("total"))["total"]
    movements = session.movements.values("direction").annotate(total=Sum("amount"))
    totals = {item["direction"]: item["total"] or Decimal("0") for item in movements}
    cash_sales = sales or Decimal("0")
    income = totals.get(CashMovement.Direction.IN, Decimal("0"))
    expenses = totals.get(CashMovement.Direction.OUT, Decimal("0"))
    return {"cash_sales": cash_sales, "income": income, "expenses": expenses,
            "expected": _money(session.opening_amount + cash_sales + income - expenses)}


@login_required
def inicio(request):
    today = timezone.localdate()
    sales_today = Sale.objects.filter(sold_at__date=today)
    daily_totals = sales_today.aggregate(total=Sum("total"), count=Count("id"))
    low_tanks = Tank.objects.filter(is_active=True, current_stock__lte=F("warning_level"))
    session = _active_cash()
    return render(request, "control/inicio.html", {
        "products_count": Product.objects.filter(is_active=True).count(),
        "tanks_count": Tank.objects.filter(is_active=True).count(),
        "sales_total": daily_totals["total"] or Decimal("0.00"),
        "sales_count": daily_totals["count"],
        "low_tanks": low_tanks,
        "cash_session": session,
        "cash_summary": _cash_summary(session),
        "recent_sales": sales_today.select_related("product", "created_by")[:7],
        "today": today,
    })


@login_required
@require_POST
def toggle_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save(update_fields=["is_active", "updated_at"])
    messages.success(request, f"Producto {'activado' if product.is_active else 'desactivado'}.")
    return redirect("productos")


@login_required
def productos(request):
    editing = get_object_or_404(Product, pk=request.GET.get("editar")) if request.GET.get("editar") else None
    if request.method == "POST":
        form = ProductForm(request.POST, instance=editing)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto guardado correctamente.")
            return redirect("productos")
    else:
        form = ProductForm(instance=editing)
    query = request.GET.get("q", "").strip()
    items = Product.objects.all()
    if query:
        items = items.filter(name__icontains=query) | items.filter(sku__icontains=query)
    return render(request, "control/catalogo.html", {
        "form": form, "items": items, "query": query, "editing": editing,
        "title": "Productos", "kind": "product",
    })


@login_required
@require_POST
def toggle_tank(request, pk):
    tank = get_object_or_404(Tank, pk=pk)
    tank.is_active = not tank.is_active
    tank.save(update_fields=["is_active"])
    messages.success(request, f"Tanque {'activado' if tank.is_active else 'desactivado'}.")
    return redirect("tanques")


@login_required
def tanques(request):
    editing = get_object_or_404(Tank, pk=request.GET.get("editar")) if request.GET.get("editar") else None
    if request.method == "POST":
        form = TankForm(request.POST, instance=editing)
        if form.is_valid():
            form.save()
            messages.success(request, "Tanque guardado correctamente.")
            return redirect("tanques")
    else:
        form = TankForm(instance=editing)
    query = request.GET.get("q", "").strip()
    items = Tank.objects.select_related("product")
    if query:
        items = items.filter(code__icontains=query) | items.filter(product__name__icontains=query)
    return render(request, "control/catalogo.html", {
        "form": form, "items": items, "query": query, "editing": editing,
        "title": "Tanques", "kind": "tank",
    })


@login_required
def compras(request):
    if request.method == "POST":
        form = PurchaseForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            with transaction.atomic():
                product = Product.objects.select_for_update().get(pk=data["product"].pk)
                quantity = data["quantity"]
                tank = None
                if product.category == Product.Category.FUEL:
                    tank = Tank.objects.select_for_update().get(pk=data["tank"].pk)
                    if tank.current_stock + quantity > tank.capacity:
                        form.add_error("quantity", "La compra supera la capacidad disponible del tanque.")
                if form.errors:
                    pass
                else:
                    purchase = form.save(commit=False)
                    purchase.product = product
                    purchase.tank = tank
                    purchase.created_by = request.user
                    purchase.total = _money(quantity * data["unit_cost"])
                    purchase.save()
                    if tank:
                        tank.current_stock += quantity
                        tank.save(update_fields=["current_stock"])
                    else:
                        product.stock_quantity += quantity
                        product.save(update_fields=["stock_quantity", "updated_at"])
                    product.unit_cost = data["unit_cost"]
                    product.save(update_fields=["unit_cost", "updated_at"])
            if not form.errors:
                messages.success(request, "Compra registrada y existencia actualizada.")
                return redirect("compras")
    else:
        form = PurchaseForm()
    purchases = Purchase.objects.select_related("product", "tank", "created_by")[:50]
    return render(request, "control/operacion.html", {
        "form": form, "title": "Compras", "description": "Registra recepciones y actualiza existencias.",
        "records": purchases, "operation": "purchase",
    })


@login_required
def ventas(request):
    session = _active_cash()
    if request.method == "POST":
        form = SaleForm(request.POST)
        if form.is_valid():
            if not session:
                form.add_error(None, "Abre la caja antes de registrar una venta.")
            else:
                data = form.cleaned_data
                with transaction.atomic():
                    # Bloquear la fila de caja y existencia evita cerrar caja durante el despacho.
                    locked_session = CashSession.objects.select_for_update().get(pk=session.pk)
                    product = Product.objects.select_for_update().get(pk=data["product"].pk)
                    quantity = data["quantity"]
                    tank = None
                    if data["unit_price"] != product.unit_price:
                        form.add_error("unit_price", "El precio cambió; actualiza la venta e inténtalo otra vez.")
                    elif locked_session.closed_at:
                        form.add_error(None, "La caja fue cerrada. Abre otra para continuar.")
                    elif product.category == Product.Category.FUEL:
                        tank = Tank.objects.select_for_update().get(pk=data["tank"].pk)
                        if tank.current_stock < quantity:
                            form.add_error("quantity", "No hay suficiente combustible en el tanque.")
                    elif product.stock_quantity < quantity:
                        form.add_error("quantity", "No hay suficiente existencia de este producto.")
                    if not form.errors:
                        sale = form.save(commit=False)
                        sale.product = product
                        sale.tank = tank
                        sale.cash_session = locked_session
                        sale.created_by = request.user
                        sale.total = _money(quantity * data["unit_price"])
                        sale.save()
                        if tank:
                            tank.current_stock -= quantity
                            tank.save(update_fields=["current_stock"])
                        else:
                            product.stock_quantity -= quantity
                            product.save(update_fields=["stock_quantity", "updated_at"])
                if not form.errors:
                    messages.success(request, "Venta registrada y existencia descontada.")
                    return redirect("ventas")
    else:
        form = SaleForm()
    records = Sale.objects.select_related("product", "tank", "created_by")[:50]
    return render(request, "control/operacion.html", {
        "form": form, "title": "Ventas", "description": "Registra despachos y ventas de tienda.",
        "records": records, "operation": "sale", "cash_session": session,
    })


@login_required
def caja(request):
    session = _active_cash()
    open_form = CashOpenForm()
    movement_form = CashMovementForm()
    close_form = CashCloseForm()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "open":
            open_form = CashOpenForm(request.POST)
            if open_form.is_valid():
                with transaction.atomic():
                    # Serialize aperturas simultáneas del mismo usuario.
                    get_user_model().objects.select_for_update().get(pk=request.user.pk)
                    if _active_cash():
                        open_form.add_error(None, "Ya existe una caja abierta. Ciérrala antes de abrir otra.")
                    else:
                        CashSession.objects.create(opened_by=request.user,
                                                   opening_amount=open_form.cleaned_data["opening_amount"])
                if not open_form.errors:
                    messages.success(request, "Caja abierta.")
                    return redirect("caja")
        elif action == "movement":
            movement_form = CashMovementForm(request.POST)
            if movement_form.is_valid() and session:
                with transaction.atomic():
                    locked = CashSession.objects.select_for_update().get(pk=session.pk)
                    if locked.closed_at:
                        movement_form.add_error(None, "La caja está cerrada.")
                    else:
                        movement = movement_form.save(commit=False)
                        movement.cash_session = locked
                        movement.created_by = request.user
                        movement.save()
                if not movement_form.errors:
                    messages.success(request, "Movimiento de caja registrado.")
                    return redirect("caja")
            elif not session:
                movement_form.add_error(None, "Abre una caja antes de registrar movimientos.")
        elif action == "close" and session:
            close_form = CashCloseForm(request.POST)
            if close_form.is_valid():
                with transaction.atomic():
                    locked = CashSession.objects.select_for_update().get(pk=session.pk)
                    if locked.closed_at:
                        close_form.add_error(None, "Esta caja ya fue cerrada.")
                    else:
                        locked.closed_at = timezone.now()
                        locked.closed_by = request.user
                        locked.closing_amount = close_form.cleaned_data["closing_amount"]
                        locked.save(update_fields=["closed_at", "closed_by", "closing_amount"])
                if not close_form.errors:
                    messages.success(request, "Caja cerrada. La diferencia quedó registrada.")
                    return redirect("caja")
    session = _active_cash()
    return render(request, "control/caja.html", {
        "session": session, "summary": _cash_summary(session), "open_form": open_form,
        "movement_form": movement_form, "close_form": close_form,
        "movements": session.movements.select_related("created_by")[:30] if session else [],
        "sales": session.sales.select_related("product")[:30] if session else [],
        "recent_sessions": CashSession.objects.select_related("opened_by", "closed_by")[:10],
    })
