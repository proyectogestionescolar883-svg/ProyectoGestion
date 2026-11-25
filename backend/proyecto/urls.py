from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

from escuela.media_views import media_proxy


class TokenRefreshThrottledView(TokenRefreshView):
    throttle_scope = 'refresh'


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/media/<path:ruta>', media_proxy, name='media_proxy'),
    path('api/', include('escuela.urls')),
    path('api/token/refresh/', TokenRefreshThrottledView.as_view(), name='token_refresh'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
