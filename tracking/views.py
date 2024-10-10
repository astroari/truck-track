from django.shortcuts import render
import requests
from django.http import JsonResponse, HttpResponse
from requests.auth import HTTPBasicAuth
from django.conf import settings
from django.views import View
import json
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

api_url = 'http://1.gpsmonitor.uz/wialon/ajax.html'
api_token = settings.WIALON_TOKEN
crm_token = settings.EMAN_CRM_TOKEN

class VehicleLocationView(View):

    def get(self, request, icao24):
        logger.info(f"Received request for icao24: {icao24}")
        try:
            # Try to get the session data from cache
            session_data = cache.get(f'session_data_{icao24}')
            logger.info(f"Retrieved session data from cache: {session_data}")
            
            if session_data is None or self.is_session_expired(session_data.get('last_request_time')):
                logger.info("Session data is None or expired, creating new session")
                # If no session data or session expired, create new session
                session_key = self.login(api_token)
                if not session_key:
                    logger.error("Login failed")
                    return JsonResponse({"error": "Login failed"}, status=500)
                
                courier_id, branch, destination_lat, destination_long = self.get_courier_id(icao24)
                unit_id = self.get_unit_id(courier_id)
                if not unit_id:
                    return JsonResponse({"error": "Unit retrieval failed"}, status=500)
                
                session_data = {
                    'session_key': session_key,
                    'last_request_time': timezone.now(),
                    'courier_id': courier_id,
                    'unit_id': unit_id,
                    'branch': branch,
                    'destination_lat': destination_lat,
                    'destination_long': destination_long,
                }
                # Store the session data in cache
                cache.set(f'session_data_{icao24}', session_data, timeout=300)  # 5 minutes timeout
            
            # Get start location based on branch
            start_lat, start_long = self.get_start_location(session_data['branch'])
            
            # Get the last position of the vehicle
            vehicle_info = self.get_last_position(session_data['session_key'], session_data['unit_id'])

            if 'item' in vehicle_info and 'pos' in vehicle_info['item']:
                # Update the last request time in cache
                session_data['last_request_time'] = timezone.now()
                cache.set(f'session_data_{icao24}', session_data, timeout=300)
                
                # Extracting coordinates
                y = vehicle_info['item']['pos']['y']
                x = vehicle_info['item']['pos']['x']
                return JsonResponse({
                    "location": {
                        "y": y, 
                        "x": x, 
                        "start_lat": start_lat, 
                        "start_long": start_long, 
                        "destination_lat": session_data['destination_lat'], 
                        "destination_long": session_data['destination_long']
                    }
                })
            else:
                return JsonResponse({"error": "Vehicle not found"}, status=404)
        except Exception as e:
            logger.exception(f"An error occurred while processing request for icao24: {icao24}")
            return JsonResponse({"error": "An unexpected error occurred"}, status=500)

    def is_session_expired(self, last_request_time):
        if last_request_time is None:
            return True
        return timezone.now() - last_request_time > timedelta(minutes=5)

    def get_start_location(self, branch):
        if branch == 'jomiy':
            return 41.35556949663072, 69.25377917274001
        elif branch == 'chinobod':
            return 41.35554159796273, 69.30574801224093
        else: 
            return 41.35556949663072, 69.25377917274001  # Default to Jomiy location

    def login(self, api_token):
        params = {
            "token": api_token,
            "fl": 3
        }

        request_url = f"{api_url}?svc=token/login&params={json.dumps(params)}"
        logger.info(f"Attempting login with URL: {request_url}")
        
        try:
            response = requests.post(request_url)
            logger.info(f"Login response status code: {response.status_code}")
            logger.info(f"Login response content: {response.text}")
            
            if response.ok:
                data = response.json()
                logger.info(f"Parsed JSON response: {data}")
                eid = data.get('eid')
                if eid:
                    logger.info(f"Login successful, eid: {eid}")
                    return eid
                else:
                    logger.error("Login failed: 'eid' not found in response")
            else:
                logger.error(f"Login failed with status code: {response.status_code}")
            
            return None
        except requests.RequestException as e:
            logger.error(f"Login failed due to request exception: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
        
        return None
    
    def get_courier_id(self, order_id):
        url = "https://crm.eman.uz/v1/api/get-delivery-info"

        payload = {'id': order_id}

        headers = {
            'token': crm_token
            }

        response = requests.request("POST", url, headers=headers, data=payload)

        if response.ok:
            delivery_info = response.json()
            courier_id = delivery_info.get('courier_id')
            branch = delivery_info.get('branch')
            branch = branch.replace(" ", "").lower()
            destination_lat = delivery_info.get('latitude')
            destination_long = delivery_info.get('longitude')
            return courier_id, branch, destination_lat, destination_long
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
    
def index(request):
    return render(request, 'tracking/index.html')

