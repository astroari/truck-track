from django.shortcuts import render
import requests
from django.http import JsonResponse
from requests.auth import HTTPBasicAuth
from django.conf import settings
from django.views import View
import json
from django.utils import timezone
from datetime import timedelta

api_url = 'http://1.gpsmonitor.uz/wialon/ajax.html'
api_token = ""

class VehicleLocationView(View):

    session_key = None         # Session is only valid for 5 minutes since last request
    last_request_time = None

    def get(self, request, icao24):
        # Check if the session key is expired
        if self.session_key is None or self.is_session_expired():      # Need to limit amount of times we log in
            self.session_key = self.login(api_token)
            if not self.session_key:
                return JsonResponse({"error": "Login failed"}, status=500)

        # Get the last position of the vehicle
        vehicle_info = self.get_last_position(self.session_key, icao24)

        if 'item' in vehicle_info and 'pos' in vehicle_info['item']:
            # Update the last request time
            self.last_request_time = timezone.now()
            # Extracting coordinates
            y = vehicle_info['item']['pos']['y']
            x = vehicle_info['item']['pos']['x']
            return JsonResponse({"location": {"y": y, "x": x}})
        else:
            return JsonResponse({"error": "Vehicle not found"}, status=404)

    def login(self, api_token):
        params = {
            "token": api_token,
            "fl": 3
        }

        request_url = f"{api_url}?svc=token/login&params={json.dumps(params)}"
        response = requests.post(request_url)

        if response.ok:
            return response.json().get('eid')
        return None

    def get_last_position(self, session_key, unit_id):
        params = {
            "id": unit_id,
            "flags": 1025,
        }

        request_url = f"{api_url}?svc=core/search_item&params={json.dumps(params)}&sid={session_key}"
        response = requests.post(request_url)

        if response.ok:
            return response.json()
        return {}
    
    def is_session_expired(self):
        # Check if the session key has expired (5 minutes)
        if self.last_request_time is None:
            return True
        return timezone.now() - self.last_request_time > timedelta(minutes=5)


def index(request):
    return render(request, 'tracking/index.html')

