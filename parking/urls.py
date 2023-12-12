from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import admin_views
from . import tasks

urlpatterns = [
    path('', views.home, name='home'),
    path('signup', views.signup, name='signup'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('about', views.about, name='about'),
    path('guidelines', views.guidelines, name='guidelines'),
    path('terms_conditions', views.terms_conditions, name='terms_conditions'),
    path('suggestions', views.suggestions, name='suggestions'),
    path('profile', views.profile, name='profile'),
    path('delete-vehicle/<str:license_plate>/', tasks.delete_vehicle, name='delete_vehicle'),
    path('get-vehicle-info/', tasks.get_vehicle_info, name='get_vehicle_info'),
    path('edit_profile', views.edit_profile, name='edit_profile'),
    path('add_vehicle', views.add_vehicle, name='add_vehicle'),
    path('notification_list', views.notification_list, name='notification_list'),
    path('parking_area', views.parking_area, name='parking_area'),
    path('reservation/<str:slot_number>', views.reservation, name='reservation'),
    path('check_reservation_status', tasks.check_reservation_status, name='check_reservation_status'),
    path('my_reservation', views.my_reservation, name='my_reservation'),
    path('clear_payment_processed', tasks.clear_payment_processed, name='clear_payment_processed'),
    path('confirm_payment', tasks.confirm_payment, name='confirm_payment'),
    path('submit_feedback', views.submit_feedback, name='submit_feedback'),
    path('extend', views.extend, name='extend'),
    path('download_receipt', views.download_receipt, name='download_receipt'),
    path('surveillance', admin_views.surveillance, name='surveillance'),
    path('generate_report', admin_views.generate_report, name='generate_report'),
    path('scan_qr', admin_views.scan_qr, name='scan_qr'),
    path('process_qr', tasks.process_qr, name='process_qr'),
    path('activate/<uidb64>/<token>', tasks.activate, name='activate'),
    path('password_reset', auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'), name='password_reset'),
    path('password_reset/done', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('login', tasks.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
