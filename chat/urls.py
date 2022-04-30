from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('webhook/', views.webhook, name='webhook'),
    #path('pokeapi/', views.pokeapi, name='pokeapi'),
]