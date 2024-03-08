import traceback

from django.contrib.auth import get_user_model
from django.http import JsonResponse
import jwt
from index.models import *
from inspect_admin import settings

# Sys_User = get_user_model()

class TokenAuthenticationMiddleware:
    EXCLUDED_ROUTES = ['/login']
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(tuple(self.EXCLUDED_ROUTES)):
            if "HTTP_AUTHORIZATION" in request.META:
                token = request.META['HTTP_AUTHORIZATION'].split()
                try:
                    payload = jwt.decode(token[0], settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
                    user_id = payload['user_id']
                    sys_user = Sys_User.objects.get(id=user_id)
                    request.user = sys_user

                    response = self.get_response(request)
                    response['Access-Control-Allow-Origin'] = '*'
                    return response
                # except (jwt.DecodeError, jwt.ExpiredSignatureError, Sys_User.DoesNotExist):
                except Exception as e:
                    traceback.print_exc()
                    return JsonResponse({"code": 401,'error': 'Invalid token'})

            else:
                return JsonResponse({"code": 401,'error': 'Invalid token'})

        response = self.get_response(request)
        response['Access-Control-Allow-Origin'] = '*'
        return response