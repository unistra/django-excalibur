import json

"""
Excalibur exceptions handler
"""


def excalibur_exception_handler(exc, response):
    """
    Return excalibur error response
    """

    response.content = json.dumps({'error': str(exc)})
    response.status_code = 500

    return response