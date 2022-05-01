from django.urls import path

from . import views

urlpatterns = [
    path('chat/', views.chat_view, name='chat-home'),
    path('', views.index_view, name='index'),
    path('webhook/', views.webhook, name='webhook'),
    #path('pokeapi/', views.pokeapi, name='pokeapi'),
]