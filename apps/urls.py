from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("productos/", views.productos, name="productos"),
    path("productos/<int:pk>/estado/", views.toggle_product, name="toggle_product"),
    path("tanques/", views.tanques, name="tanques"),
    path("tanques/<int:pk>/estado/", views.toggle_tank, name="toggle_tank"),
    path("compras/", views.compras, name="compras"),
    path("ventas/", views.ventas, name="ventas"),
    path("caja/", views.caja, name="caja"),
]
