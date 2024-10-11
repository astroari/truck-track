from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    #path('api/aircraft/<str:icao24>/', views.fetch_aircraft_by_icao, name='fetch_aircraft_by_icao'),
    path('api/aircraft/<str:icao24>/', views.VehicleLocationView.as_view(), name='fetch_aircraft_by_icao'),
    path('webhook/', views.webhook_receiver, name='webhook_receiver'),
]
