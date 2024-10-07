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
api_token = "9507c2ae48bac73a7204cdc1f5b55717934F0DA4730AE78BF6CB056330380B67BEF31945"
crm_token = "HMl2bfCJyLEUEMMbzQ-A9_Ywx8HJpneNtWRNt9T9YfIj6fRWgnc1_YAChYMJzR0yuIswJLpbNmKDK6Ew2vx3KNeFGmDO03IgZ6AsmfE3q-mPlOhH76qmGNojubJW5k7LDv4px0mp-cQQvP3lFORKPwcsLxlBhtSogzKnaYWfmLgXnD8uMwphrRc2HG-qY7iqYU0_NsoYU0Eo-LCFmpbmiEHug70MhqEtRXW-N5UepiMpq9_kunuruY4HmV"

class VehicleLocationView(View):

    session_key = None         # Session is only valid for 5 minutes since last request
    last_request_time = None
    courier_id = None
    unit_id = None

    def get(self, request, icao24):
        # Check if the session key is expired
        if self.session_key is None or self.is_session_expired():      # Need to limit amount of times we log in
            self.session_key = self.login(api_token)
            if not self.session_key:
                return JsonResponse({"error": "Login failed"}, status=500)
            
        # Check if there is a unit_id
        if self.unit_id is None:
            self.courier_id = self.get_courier_id(icao24)
            self.unit_id = self.get_unit_id(self.courier_id)
            if not self.unit_id:
                return JsonResponse({"error": "Unit retrieval failed"}, status=500)
        
        # Get the last position of the vehicle
        vehicle_info = self.get_last_position(self.session_key, self.unit_id)

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
    
    def get_courier_id(self, order_id):
        url = "https://crm.eman.uz/v1/api/get-delivery-info"

        payload = {'id': order_id}

        headers = {
            'token': crm_token
            }

        response = requests.request("POST", url, headers=headers, data=payload)

        if response.ok:
            courier_id = response.json().get('courier_id')
            return courier_id
        return None

    def get_unit_id(self, courier_id):
        url = "https://crm.eman.uz/v1/api/get-driver-info"

        payload = {'id': courier_id}

        headers = {
            'token': crm_token
            }

        response = requests.request("POST", url, headers=headers, data=payload)

        if response.ok:
            unit_id = response.json().get('gps_id')
            return unit_id
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

