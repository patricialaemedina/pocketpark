"""
URL configuration for pocketpark project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from parking.tasks import get_slot, delete_inactive_accounts

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('parking.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler400 = 'parking.views.error_400'
handler403 = 'parking.views.error_403'
handler404 = 'parking.views.error_404'
handler500 = 'parking.views.error_500'

get_slot(repeat=15)
delete_inactive_accounts(repeat=15)