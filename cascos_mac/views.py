from django.shortcuts import render

# Vista para el error 400
def bad_request(request, exception=None):
    return render(request, 'errores/400.html', status=400)

# Vista para el error 403
def forbidden(request, exception=None):
    return render(request, 'errores/403.html', status=403)

# Vista para el error 404
def not_found(request, exception=None):
    return render(request, 'errores/404.html', status=404)

# Vista para el error 500
def server_error(request):
    return render(request, 'errores/500.html', status=500)

# Vista para el error 405
def error_405_view(request, exception=None):
    return render(request, 'errores/405.html', status=405)

# Vista para el error 408
def error_408_view(request, exception=None):
    return render(request, 'errores/408.html', status=408)

# Vista para el error 503
def error_503_view(request):
    return render(request, 'errores/503.html', status=503)