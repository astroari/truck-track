from django.shortcuts import render
import requests
from django.http import JsonResponse
from requests.auth import HTTPBasicAuth
from django.conf import settings


def fetch_aircraft_by_icao(request, icao24):
    url = "https://opensky-network.org/api/states/all"
    
    params = {
        'icao24': icao24 #icao of the aircraft i want to track
    }

    # using my credentials
    username = settings.OPENSKY_USERNAME
    password = settings.OPENSKY_PASSWORD

    # fetching data
    #response = requests.get(url, params=params) # anonymous auth
    response = requests.get(url, params=params, auth=HTTPBasicAuth(username, password))
    data = response.json()

    if response.status_code == 200:
        data = response.json()
        return JsonResponse(data)
    else:
        return JsonResponse({'error': 'Unable to fetch data from OpenSky API'}, status=response.status_code)

def index(request):
    return render(request, 'tracking/index.html')

