# -*- coding: utf-8 -*-
from functools import wraps

"""
decorators for excalibur
"""


def is_excalibur(func):
    """
    check if excalibur can be called
    """

    def check_content_type(response):
        """ check if the content type of the response is json """
        return response['Content-Type'] == 'application/json'

    def check_request(request):
        """ check the request method and args """
        return request.method == "GET" and 'project' in \
            request.REQUEST.keys() and 'establishment' in request.REQUEST.keys() \
            and "REQUEST_EXCALIBUR_PARAMS" in request.META

    def check_permission(request, response):
        """ check if not 401 or 403 """
        return response.status_code not in (401, 403)

    def check_status_code(response):
        """
        Run excalibur if the response from the referentiel is 200 (data ok) or
        404 (not found, but excalibur try to find it)
        """
        return response.status_code in (200, 404)

    def check_excalibur(request, response):
        """
        return true if the request needs excalibur
        """
        return check_content_type(response) and check_request(request)\
            and check_permission(request, response) and check_status_code(response)

    @wraps(func)
    def wrapper(middleware, request, response):
        if not check_excalibur(request, response):
            return response
        return func(middleware, request, response)

    return wrapper
