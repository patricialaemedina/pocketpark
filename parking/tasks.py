import uuid
import json
import time
import requests
import datetime
import urllib.parse
from django.conf import settings
from django.utils import timezone
from django.contrib import messages, auth
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage, send_mail
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.views import PasswordResetCompleteView
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from datetime import timedelta
from .models import *
from background_task import background
from background_task.models import CompletedTask

last_notification_times = {}

@background(schedule=10)
def delete_inactive_accounts():
    print('Successfully checked inactive accounts')
    currently_logged_out_users = get_currently_logged_out_users()

    for user in currently_logged_out_users:
        user_logout_time = timezone.localtime(user.last_logout)

        user_logout_time = timezone.localtime(user.last_logout)
        deletion_date = user_logout_time + timedelta(days=731)
        notification_time = deletion_date - timedelta(days=10)

        two_years_after_logout = timezone.localtime(user.last_logout + timedelta(days=731))
            
        if not user.is_logged_in and not user_logs_in_within_721_days(user):
            if user.username not in last_notification_times or (timezone.now() - last_notification_times[user.username]).days >= 721:
                if not user.notification_sent:
                    send_deletion_notification(user)
                    last_notification_times[user.username] = timezone.now()
                    user.notification_sent = True
        
        if not user.is_logged_in and not user_logs_in_within_2_years(user) and not user.is_staff:
            delete_user_account(user)

    CompletedTask.objects.all().delete()

def get_currently_logged_out_users():
    return CustomUser.objects.filter(last_logout__lte=timezone.now(), is_logged_in=False, is_active=True)

def user_logs_in_within_721_days(user):
    days_721_after_logout = timezone.localtime(user.last_logout + timedelta(days=721))
    return user.is_logged_in or days_721_after_logout > timezone.localtime(timezone.now())

def user_logs_in_within_2_years(user):
    two_years_after_logout = timezone.localtime(user.last_logout + timedelta(days=731))
    return user.is_logged_in or two_years_after_logout > timezone.localtime(timezone.now())

def send_deletion_notification(user):
    user_logout_time = timezone.localtime(user.last_logout)
    deletion_date = user_logout_time + timedelta(days=731)
    notification_time = deletion_date - timedelta(days=10)

    formatted_deletion_date = deletion_date.strftime('%b %d, %Y, %I:%M %p')

    subject = 'Account Deletion Notice'
    message = (
        f"Dear {user.username},\n\n"
        f"We hope this message finds you well. "
        f"We regret to inform you that your PocketPark account is scheduled for deletion.\n\n"
        f"Account Deletion Date: {formatted_deletion_date}\n\n"
        f"To prevent the deletion of your account, please log in to PocketPark before the specified deletion date. "
        f"By logging in, you can ensure that your account remains active.\n\n"
        f"Should you have any questions or require assistance, feel free to reach out to our support team at web.pocketpark@gmail.com.\n\n"
        f"Thank you for being a part of the PocketPark community.\n\n"
        f"Best regards,\nThe PocketPark Team"
    )
    from_email = 'your@example.com' 
    to_email = user.email

    send_mail(subject, message, from_email, [to_email])

def delete_user_account(user):
    two_years_after_logout = timezone.localtime(user.last_logout + timedelta(days=731))
    user.delete()

User = get_user_model()
def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None
    
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()

        auth.login(request, user)
        account_created_notification(request.user)

        custom_messages = [
            {
                'class': 'success-message',
                'content': "Your email has been successfully verified, and your account is now ready for login.",
            }
        ]

        for custom_message in custom_messages:
            messages.add_message(request, messages.SUCCESS, custom_message['content'], extra_tags=custom_message['class'])

        return redirect('login')

    else:
        custom_messages = [
            {
                'class': 'error-message',
                'content': "Oops! Activation link is invalid.",
            }
        ]

        for custom_message in custom_messages:
            messages.add_message(request, messages.ERROR, custom_message['content'], extra_tags=custom_message['class'])

    return redirect('profile')

def activeEmail(request, user, to_email):
    mail_subject = "Account Activation"
    message = render_to_string ("registration/template_activate_account.html", {
        'user': user.username,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        "protocol": 'https' if request.is_secure() else 'http'
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    custom_messages = []
    if email.send():
        custom_messages.append({
            'class': 'confirmation-message',
            'content': f"Hello, {user}! We've sent an activation link to your email inbox at {to_email}. "
                       "Please click on the received activation link to confirm and complete your registration. "
                       "If you don't see the email in your inbox, please check your spam folder.",
        })
    else:
        custom_messages.append({
            'class': 'error-message',
            'content': f"Oops! We encountered an issue while trying to send the email to {to_email}. "
                       "Please double-check if you've entered the email address correctly.",
        })

    for custom_message in custom_messages:
        messages.add_message(request, messages.SUCCESS if custom_message['class'] == 'confirmation-message' else messages.ERROR, custom_message['content'], extra_tags=custom_message['class'])

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    def get(self, request, *args, **kwargs):
        return render(request, 'registration/login.html')

def check_and_ban_user(username):
    try:
        user = CustomUser.objects.get(username=username)
        now = timezone.now()

        if user.is_banned:            
            if now >= user.ban_end_time:
                user.is_banned = False
                user.ban_end_time = None
                user.save()
                return False
            else:
                return True
        
        else:
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            past_failed_bookings = Payment.objects.filter(booking__user=user, booking__is_valid=False, payment_status="Failed", creation_datetime__gte=start_of_day)
            
            if past_failed_bookings.count() >= 3:
                user.is_banned = True
                user.ban_end_time = now + timedelta(days=1)
                user.save()
                return True
            else:
                return False

    except CustomUser.DoesNotExist:
        pass

def check_reservation_status(request):
    slot_number = request.GET.get("slot_number") 
    already_reserved = False 

    try:
        slot = Slot.objects.get(number=slot_number)
        if slot.status != "Vacant":
            already_reserved = True

    except Slot.DoesNotExist:
        pass

    return JsonResponse({"already_reserved": already_reserved})

def create_checkout_session(request, booking, fee_type, fee):
    url = "https://api.paymongo.com/v1/checkout_sessions"

    payload = { 
        "data": { 
            "attributes": {
                "send_email_receipt": True, 
                "show_description": True,
                "show_line_items": True,
                "cancel_url": "https://ph.pocketpark.online/parking_area",
                "line_items": [{
                    "currency": "PHP",
                    "amount": int(fee),
                    "name": f"{fee_type} Fee",
                    "quantity": 1
                }],
                "payment_method_types": ["gcash", "paymaya", "card"],
                "success_url": "https://ph.pocketpark.online/parking_area",
                "description": f"{fee_type} Fee"
            } } }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "authorization": "Basic c2tfdGVzdF9keVIzYVp0elRRNGMxN2dIc21Kd3hOc3g6"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        attributes = data['data']['attributes']

        new_payment = Payment.objects.create(booking=booking, checkout_session_id=data['data']['id'], checkout_url=attributes['checkout_url'], amount_paid=attributes['line_items'][0]['amount'], fee_type=fee_type, payment_status='Pending')
        new_payment.save()

        request.session['payment_processed'] = True
        return new_payment

def expire_checkout_session(checkout_session_id):
    url = f"https://api.paymongo.com/v1/checkout_sessions/{checkout_session_id}/expire"

    headers = {
        "accept": "application/json",
        "authorization": "Basic c2tfdGVzdF9keVIzYVp0elRRNGMxN2dIc21Kd3hOc3g6"
    }

    response = requests.post(url, headers=headers)

@csrf_exempt
def clear_payment_processed(request):
    request.session['payment_processed'] = False
    return JsonResponse({'message': 'Session variable cleared'})

@csrf_exempt
def confirm_payment(request):
    if request.method == "POST":    
        data = json.loads(request.body)
        paid_payment = Payment.objects.get(checkout_url=(data['data']['attributes']['data']['attributes']['checkout_url']))

        if paid_payment.fee_type == "Reservation":
            new_ereceipt = Receipt.objects.create(payment=paid_payment)
            new_ereceipt.save()
            reservation_created_notification(paid_payment.booking.user, f"Slot {paid_payment.booking.slot.number}", paid_payment.booking.start_time)

        if paid_payment.fee_type == "Extension":
            extension_times = {20.00: 15, 30.00: 30, 40.00: 45}
            amount_paid_minutes = extension_times.get(paid_payment.amount_paid, 0)
            paid_payment.booking.expiration_time += timedelta(minutes=amount_paid_minutes)
            paid_payment.booking.extended = True
            reservation_extended_notification(paid_payment.booking.user, f"Slot {paid_payment.booking.slot.number}", paid_payment.booking.expiration_time)
            
        paid_payment.payment_status = "Paid"
        paid_payment.booking.slot.status = "Reserved"
        paid_payment.booking.save()
        paid_payment.save()

        apikey = 'd56bd8f11cfea2b104f86ba054f8e0d7'
        sendername = 'SEMAPHORE'
        expiration_time = paid_payment.booking.expiration_time
        manila_timezone = timezone.get_current_timezone()
        expiration_time_manila = expiration_time.astimezone(manila_timezone)
        formatted_time = expiration_time_manila.strftime("%B %d, %Y, %I:%M %p")
        message = f"Hello {paid_payment.booking.user.first_name} {paid_payment.booking.user.last_name}! Your {paid_payment.fee_type} for Slot {paid_payment.booking.slot.number} has been made. Please arrive before {formatted_time} and present your receipt to the parking attendant."
        number = paid_payment.booking.user.contact_number
        params = {'apikey': apikey, 'sendername': sendername, 'message': message, 'number': number}
        url = 'https://api.semaphore.co/api/v4/messages?' + urllib.parse.urlencode(params)
        requests.post(url)

        expire_checkout_session(paid_payment.checkout_session_id)

        return HttpResponse(status=200)
    else:
        return HttpResponse(status=405)

@csrf_exempt
def process_qr(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            qrData = data.get('data')

            if qrData is not None:
                try:
                    booking_id = uuid.UUID(qrData)
                    payment = Payment.objects.get(booking__id=booking_id, fee_type="Reservation")
                    if payment.booking.is_valid:
                        response_data = {'message': "VALID",
                                        'user': f"{payment.booking.user.first_name} {payment.booking.user.last_name}",
                                        'slot': f"{payment.booking.slot.number}",
                                        'start_time': f"{payment.booking.start_time}",
                                        'license_plate': f"{payment.booking.vehicle.license_plate}",
                                        'vehicle_model': f"{payment.booking.vehicle.vehicle_model}",
                                        'vehicle_make': f"{payment.booking.vehicle.vehicle_make}",
                                        'vehicle_color': f"{payment.booking.vehicle.vehicle_color}",
                                        }
                except Payment.DoesNotExist:
                    response_data = {'message': 'INVALID'}
                except ValueError:
                    response_data = {'message': 'Invalid UUID format'}
            else:
                response_data = {'message': 'Invalid data format'}

            return JsonResponse(response_data)
        except json.JSONDecodeError:
            response_data = {'message': 'Invalid JSON format'}
            return JsonResponse(response_data, status=400)
    else:
        response_data = {'error': 'Invalid request method'}
        return JsonResponse(response_data, status=405)

def update_slot_status(slot_number: int, is_occupied: bool):
    current_time = timezone.now()

    try:
        slot_instance, created = Slot.objects.get_or_create(number=slot_number)
        
        try:
            booking = Booking.objects.get(slot=slot_instance, is_valid=True)
        
            try:
                extension = Payment.objects.get(booking=booking, fee_type="Extension", payment_status="Pending")

                if (current_time - extension.creation_datetime).total_seconds() > 300:
                    extension.payment_status = "Failed"
                    extension.save()
                    expire_checkout_session(extension.checkout_session_id)

            except Payment.DoesNotExist:
                pass  

            try:
                reservation = Payment.objects.get(booking=booking, fee_type="Reservation")
        
                if reservation.payment_status == "Pending" and (current_time - reservation.creation_datetime).total_seconds() > 300:
                    reservation.booking.is_valid = False
                    reservation.booking.end_time = current_time
                    reservation.booking.slot.status = "Vacant"
                    reservation.payment_status = "Failed"
                    reservation.booking.save()
                    reservation.save()
                    expire_checkout_session(reservation.checkout_session_id)
                        
                elif reservation.payment_status == "Paid" and reservation.booking.expiration_time < current_time and not is_occupied:
                    reservation.booking.is_valid = False
                    reservation.booking.end_time = current_time
                    reservation.booking.slot.status = "Vacant"
                    reservation.booking.save()

                elif reservation.payment_status == "Paid" and reservation.booking.expiration_time > current_time:
                    if is_occupied:
                        reservation.booking.is_valid = True
                        reservation.booking.slot.status = "Occupied"
                        reservation.booking.save()
                    elif not is_occupied and reservation.booking.slot.status == "Occupied":
                        reservation.booking.is_valid = False
                        reservation.booking.end_time = current_time
                        reservation.booking.slot.status = "Vacant"
                        reservation.booking.save()
                    else:
                        reservation.booking.is_valid = True
                        reservation.booking.slot.status = "Reserved"
                        reservation.booking.save()

                else:
                    if is_occupied:
                        reservation.booking.slot.status = "Occupied"
                        reservation.booking.save()
                    else:
                        reservation.booking.slot.status = "Vacant"
                        reservation.booking.save()

            except Payment.DoesNotExist:
                pass
            
        except Booking.DoesNotExist:
            if is_occupied:
                slot_instance.status = "Occupied"
                slot_instance.save()
            else:
                slot_instance.status = "Vacant"
                slot_instance.save()
    
    except Slot.DoesNotExist:
        pass

@background(schedule=10)
def get_slot():
    flask_api_url = "http://api.pocketpark.online/api/run_yolo"

    response = requests.get(flask_api_url)

    if response.status_code == 200:
        slot_data = response.json()
        
        for slot in slot_data:
            slot_number = slot.get("number")
            is_occupied = slot.get("occupied")
            
            # Call the update_slot_status function to update the slot status in your database
            update_slot_status(slot_number, is_occupied)
            
        print('slot update')
        return slot_data
    else:
        error_message = {"error": "Failed to retrieve slot data"}
        print(error_message)
        return None

