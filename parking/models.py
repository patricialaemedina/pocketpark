import six
import uuid
from functools import wraps
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from decimal import Decimal

class CustomUser(AbstractUser):
    contact_number = models.CharField(max_length=11, help_text='Enter a 11-digit contact number (e.g. 09xx).')
    is_banned = models.BooleanField(default=False, verbose_name='Banned')
    ban_end_time = models.DateTimeField(null=True, blank=True, verbose_name='End of Ban')
    is_logged_in = models.BooleanField(default=False, verbose_name='Logged In')
    last_logout = models.DateTimeField(null=True, blank=True, verbose_name='Logged Out Time')
    notification_sent = models.BooleanField(default=False, verbose_name='Deletion Notification')

    def __str__(self):
        return str(self.username)

class UserAgreement(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    agreed_to_terms = models.BooleanField(default=False)

    def __str__(self):
        return f"User Agreement for {self.user.username}"

class Vehicle(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    license_plate = models.CharField(max_length=20, help_text='Enter a license plate (e.g. ABC 1234).')
    vehicle_make = models.CharField(max_length=50)
    vehicle_model = models.CharField(max_length=50)
    vehicle_color = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.license_plate} {self.vehicle_make} {self.vehicle_model}"

class Slot(models.Model):
    SLOT_STATUS = (
        ('Vacant', 'Vacant'),
        ('Occupied', 'Occupied'),
        ('Reserved', 'Reserved'),
    )
    number = models.IntegerField()
    status = models.CharField(max_length=20, choices=SLOT_STATUS, help_text='Slot Status', default='Vacant')

    def __str__(self):
        return f"Slot {self.number}"

class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text='Unique ID for this particular booking.')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    expiration_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    is_valid = models.BooleanField(default=True)
    extended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}"
    
class Payment(models.Model):
    PAYMENT_STATUS = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
    )
    FEE_TYPE = (
        ('Reservation', 'Reservation'),
        ('Extension', 'Extension'),
    )
    creation_datetime = models.DateTimeField(auto_now_add=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE, help_text='Payment Fee Type')
    checkout_session_id = models.CharField(max_length=255)
    checkout_url = models.URLField(max_length=200, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Pending')

    def save(self, *args, **kwargs):
        if not self.id:  
            self.amount_paid = Decimal(self.amount_paid) / Decimal('100.00')
        super().save(*args, **kwargs) 

    def __str__(self):
        return f"{self.fee_type} Fee: {self.payment_status} - {self.booking.user.first_name} {self.booking.user.last_name} - ₱{self.amount_paid}"

class Receipt(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    qr_code_data = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Receipt for Booking {self.payment.booking.id}"   

class Feedback(models.Model):
    RATINGS = (
        ('Excellent', 'Excellent'),
        ('Good', 'Good'),
        ('Medium', 'Medium'),
        ('Poor', 'Poor'),
        ('Very Bad', 'Very Bad'),
    )
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    rating = models.CharField(max_length=20, choices=RATINGS)
    comments = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for Booking {self.payment.booking.id}"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.message
        
def create_notification(user, notification_type, message):
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        message=message
    )

def account_created_notification(user):
    message = f"Hi, {user.first_name}! Welcome to PocketPark! Reserve your slot now."
    create_notification(
        user=user,
        notification_type='Account Created',
        message=message
    )

def profile_updated_notification(user):
    create_notification(
        user=user,
        notification_type='Profile Updated',
        message='Your profile information has been updated.'
    )

def vehicle_added_notification(user, license_plate):
    message = f"You have added a new vehicle ({license_plate})!"
    create_notification(
        user=user,
        notification_type='Vehicle Added',
        message=message
    )

def reservation_created_notification(user, slot_info, reservation_time):
    formatted_time = timezone.localtime(reservation_time).strftime("%B %d, %Y, %I:%M %p")
    message = f"Reservation for '{slot_info}' at ({formatted_time}) has been made."
    create_notification(
        user=user,
        notification_type='Reservation Created',
        message=message
    )   

def reservation_extended_notification(user, slot_info, reservation_time):
    formatted_time = timezone.localtime(reservation_time).strftime("%B %d, %Y, %I:%M %p")
    message = f"Your reservation for '{slot_info}' has been extended to ({formatted_time})."
    create_notification(
        user=user,
        notification_type='Reservation Extended',
        message=message
    )

def user_not_authenticated(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        return redirect('signup') 

    return _wrapped_view

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk) + six.text_type(timestamp) + six.text_type(user.is_active)
        )

account_activation_token = AccountActivationTokenGenerator()