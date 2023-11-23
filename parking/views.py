import os
import qrcode
from io import BytesIO
from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.platypus import Image
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor, black
from datetime import datetime, timedelta
from django.urls import reverse
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.http import FileResponse
from django.contrib import messages, auth
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import *
from .tasks import *

def home(request):
    return render(request, 'home.html', {})

@user_not_authenticated
def signup(request):
    if request.method == 'POST':
        userCreateForm = UserCreateForm(request.POST)
        vehicleForm = VehicleForm(request.POST)

        if userCreateForm.is_valid() and vehicleForm.is_valid():
            user = userCreateForm.save(commit=False)
            user.is_logged_in = True
            user.is_active = False
            user.save()

            vehicle = vehicleForm.save(commit=False)
            vehicle.owner = user
            vehicle.save()

            if userCreateForm.cleaned_data.get('agreed_to_terms'):
                user_agreement, created = UserAgreement.objects.get_or_create(user=user)
                user_agreement.agreed_to_terms = True
                user_agreement.save()
    
            activeEmail(request, user, userCreateForm.cleaned_data.get('email'))
            return redirect(reverse('profile'))
    else:
        userCreateForm = UserCreateForm()
        vehicleForm = VehicleForm()

    return render(request, 'registration/signup.html', {'userCreateForm': userCreateForm, 'vehicleForm': vehicleForm})

def login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, request.POST)
        if form.is_valid():
            user = form.get_user()
            
            if not user.is_staff:
                user.is_logged_in = True
                user.save()
                auth.login(request, user)
                return redirect('profile')
            else:
                messages.error(request, 'Staff members are not allowed to log in.')
    else:
        form = CustomAuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})    

@login_required(login_url='login')
def logout(request):
    user = request.user
    user.is_logged_in = False
    user.last_logout = timezone.now()
    user.save()

    auth.logout(request)
    return redirect('home')

@login_required(login_url="login")
def about(request):
    return render(request, 'parking/about.html', {})

@login_required(login_url="login")
def terms_conditions(request):        
    return render(request, 'parking/terms_conditions.html', {})

@login_required(login_url='login')
def guidelines(request):        
    return render(request, 'parking/guidelines.html', {})

@login_required(login_url='login')
def profile(request):
    vehicles = Vehicle.objects.filter(owner=request.user)

    return render(request, 'parking/profile.html', {'user': request.user, 'vehicles': vehicles})

@login_required(login_url='login')
def edit_profile(request):
    userEditForm = UserEditForm(request.POST, instance=request.user)
    pwordForm = CustomPasswordChangeForm(request.user, request.POST)

    if request.method == 'POST' and 'edit_profile' in request.POST:
        if userEditForm.is_valid():
            user = userEditForm.save(commit=False)
            user.save()
    
            profile_updated_notification(request.user)
            messages.success(request, 'Your profile changes have been saved successfully.')
            return redirect('profile')        
    else:
        userEditForm = UserEditForm(instance=request.user)    
        
    if request.method == 'POST' and 'change_password' in request.POST:
        if pwordForm.is_valid():
            user = pwordForm.save()
            auth.update_session_auth_hash(request, user)

            profile_updated_notification(request.user)
            messages.success(request, 'Your profile changes have been saved successfully.')
            return redirect('profile')
    else:    
        pwordForm = CustomPasswordChangeForm(request.user)

    return render(request, 'parking/edit_profile.html', {'userEditForm': userEditForm, 'pwordForm': pwordForm})

@login_required(login_url='login')
def add_vehicle(request):
    if request.method == "POST":
        form = VehicleForm(request.POST)
        
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = request.user
            vehicle.save()

            vehicle_added_notification(request.user, vehicle.license_plate)
            return redirect(reverse('profile'))
    else:
        form = VehicleForm()

    return render(request, 'parking/add_vehicle.html', {'form': form})

@login_required(login_url='login')
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
    current_time = timezone.now()
    
    return render(request, 'parking/notification_list.html', {'notifications': notifications, 'current_time': current_time})

@login_required(login_url='login')
def parking_area(request):
    check_and_ban_user(request.user.username)

    slots = Slot.objects.all().order_by('number')

    paid_reservation = Payment.objects.filter(booking__user=request.user, booking__is_valid=True, payment_status="Paid", fee_type="Reservation").first()
    if paid_reservation:
        already_booked = True
    else:
        already_booked = False

    context = {'slots': slots, 'already_booked': already_booked}

    if request.htmx:
        return render(request, 'partials/slot.html', context)
    else:
        return render(request, 'parking/parking_area.html', context)

@login_required(login_url='login')
def reservation(request, slot_number):
    already_reserved = False
    vehicles = Vehicle.objects.filter(owner=request.user)

    try: 
        slot = Slot.objects.get(number=slot_number)    
    except Slot.DoesNotExist:
        return redirect(reverse('parking_area'))

    if request.user.is_banned:
        return redirect(reverse('parking_area'))
    if Booking.objects.filter(user=request.user, is_valid=True).first():
        return redirect(reverse('my_reservation'))
    
    if request.method == 'POST':
        form_start_time = request.POST.get('start_time')
        form_vehicle = request.POST.get('vehicle')

        vehicle = Vehicle.objects.get(license_plate = form_vehicle)
        current_datetime = datetime.datetime.now()
        current_date = current_datetime.date()
        user_time = datetime.datetime.combine(current_date, datetime.datetime.strptime(form_start_time, '%H:%M').time())
        user_time_aware = timezone.make_aware(user_time)
        start_time = user_time_aware
        expiration_time = start_time + timedelta(minutes=15)

        fee_table = [(1, 2000), (2, 3000), (3, 4000), (4, 5000), (5, 6000), (6, 7000), (float('inf'), 8000)]
        time_difference = (start_time - timezone.now()).total_seconds() / 3600
        amount = next((fee for hours, fee in fee_table if time_difference <= hours), 0)

        with transaction.atomic():
            try:
                slot = Slot.objects.select_for_update().get(number=slot_number)
        
                if slot.status != 'Vacant':
                    return render(request, 'parking/reservation.html', {'user': request.user, 'vehicles': vehicles, 'slot_number': slot_number, 'already_reserved': True})
                else:
                    slot.refresh_from_db()
                    if slot.status != 'Vacant':
                        return render(request, 'parking/reservation.html', {'user': request.user, 'vehicles': vehicles, 'slot_number': slot_number, 'already_reserved': True})
                
                    new_booking = Booking.objects.create(slot=slot, user=request.user, vehicle=vehicle, start_time=start_time, expiration_time=expiration_time)

                    slot.status = 'Reserved'
                    slot.save()
                    new_booking.save()
            
                    payment = create_checkout_session(request, new_booking, fee_type="Reservation", fee=amount)
                    return redirect(payment.checkout_url)
            
            except IntegrityError:
                return render(request, 'parking/reservation.html', {'user': request.user, 'vehicles': vehicles, 'slot_number': slot_number, 'already_reserved': True})

    return render(request, 'parking/reservation.html', {'user': request.user, 'vehicles': vehicles, 'slot_number': slot_number, 'already_reserved': False})

@login_required(login_url='login')
def my_reservation(request):
    try:
        valid_booking = Payment.objects.get(booking__user=request.user, booking__is_valid=True, payment_status="Paid", fee_type="Reservation")
        feedback_exists = Feedback.objects.filter(payment=valid_booking).exists()
    except Payment.DoesNotExist:
        valid_booking = None
        feedback_exists = False
        
    paid_reservation = Payment.objects.filter(booking__user=request.user, booking__is_valid=True, payment_status="Paid", fee_type="Reservation")    
    unpaid_reservation = Payment.objects.filter(booking__user=request.user, booking__is_valid=True, payment_status="Pending", fee_type="Reservation")

    successful_bookings = Payment.objects.filter(booking__user=request.user, booking__is_valid=False, payment_status="Paid", fee_type="Reservation").order_by('-booking__created_at')
    failed_bookings = Payment.objects.filter(booking__user=request.user, booking__is_valid=False, payment_status="Failed", fee_type="Reservation").order_by('-booking__created_at')
            
    return render(request, 'parking/my_reservation.html', {'feedback_exists': feedback_exists, 'paid_reservation': paid_reservation, 'unpaid_reservation': unpaid_reservation, 'successful_bookings': successful_bookings, 'failed_bookings': failed_bookings})

@login_required(login_url='login')
def extend(request):
    paid_reservation = Payment.objects.filter(booking__user=request.user, booking__is_valid=True, payment_status="Paid", fee_type="Reservation").first()
    unpaid_extension = Payment.objects.filter(booking__user=request.user, booking__is_valid=True, payment_status="Pending", fee_type="Extension")

    current_datetime = timezone.now()

    if not (paid_reservation and current_datetime >= paid_reservation.booking.start_time):
        return redirect(reverse('my_reservation'))
    
    if paid_reservation.booking.extended:
        return redirect(reverse('my_reservation'))
        
    if request.method == "POST":
        amount = request.POST.get('amount')
        
        payment = create_checkout_session(request, paid_reservation.booking, fee_type='Extension', fee=amount)
        return redirect(payment.checkout_url)

    return render(request, 'parking/extend.html', {'unpaid_extension': unpaid_extension})

@login_required(login_url='login')
def submit_feedback(request):
    valid_booking = None
    feedback_exists = False

    try:
        valid_booking = Payment.objects.get(booking__user=request.user, booking__is_valid=True, payment_status="Paid", fee_type="Reservation")
        feedback_exists = Feedback.objects.filter(payment=valid_booking).exists()
    except Payment.DoesNotExist:
        pass

    if request.method == 'POST' and not feedback_exists and valid_booking:
        rating = request.POST.get('rating')
        comments = request.POST.get('comments')
        
        feedback = Feedback.objects.create(payment=valid_booking, rating=rating, comments=comments)

        return redirect('my_reservation')
    
    return render(request, 'parking/my_reservation.html', {'feedback_exists': feedback_exists})

@login_required(login_url='login')
def download_receipt(request):
    paid_reservation = Payment.objects.filter(booking__user=request.user, booking__is_valid=True, payment_status="Paid", fee_type="Reservation").first()
    paid_extension = Payment.objects.filter(booking__user=request.user, booking__is_valid=True, payment_status="Paid", fee_type="Extension").first()

    if not paid_reservation:
        return redirect(reverse('my_reservation'))

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=(400, 225))

    p.setFillColor(HexColor("#3B5D50"))
    p.rect(0, 0, 400, 225, fill=True)

    logo_path = 'parking/static/images/pocket-park.png'
    logo = Image(logo_path, width=90, height=16)
    logo.drawOn(p, 20, 191)

    p.setFont("Helvetica-Bold", 12)
    p.setFillColor("#EBEEED")
    p.drawString(120, 200, "Mayflower Parking E-Receipt")

    p.setFont("Helvetica-Bold", 8)
    p.drawString(140, 190, "Greenfield District Mandaluyong")

    p.setFillColor(HexColor("#D9D9D9"))  
    p.setLineWidth(1)
    p.roundRect(10, 10, 380, 170, 20, stroke=True, fill=True)

    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(black) 
    p.drawString(35, 160, "BOOKING DETAILS")

    p.setFont('Times-Roman', 8)
    p.drawString(35, 150, f"Booking ID: {paid_reservation.booking.id}")
    p.drawString(35, 140, f"Slot Number: {paid_reservation.booking.slot.number}")
    p.drawString(35, 130, f"User: {paid_reservation.booking.user.first_name} {paid_reservation.booking.user.last_name}")
    p.drawString(35, 120, f"Start Time: {timezone.localtime(paid_reservation.booking.start_time).strftime('%B %d, %Y, %I:%M %p')}")
    p.drawString(35, 110, f"Expiration Time: {timezone.localtime(paid_reservation.booking.expiration_time).strftime('%B %d, %Y, %I:%M %p')}")

    p.setFont("Helvetica-Bold", 8)
    p.drawString(35, 90, "CAR DETAILS")

    p.setFont('Times-Roman', 8)
    p.drawString(35, 80, f"License Plate: {paid_reservation.booking.vehicle.license_plate}")
    p.drawString(35, 70, f"Vehicle Make: {paid_reservation.booking.vehicle.vehicle_make}")
    p.drawString(35, 60, f"Vehicle Model: {paid_reservation.booking.vehicle.vehicle_model}")
    p.drawString(35, 50, f"Vehicle Color: {paid_reservation.booking.vehicle.vehicle_color}")

    p.setFont("Helvetica-Bold", 8)
    p.drawString(250, 160, "PAYMENT DETAILS")

    p.setFont('Times-Roman', 8)
    p.drawString(250, 150, f"Reservation Fee: {paid_reservation.amount_paid}")

    if paid_extension:
        p.drawString(250, 140, f"Extension Fee: {paid_extension.amount_paid}")
        p.drawString(250, 130, f"Total Amount: {paid_reservation.amount_paid + paid_extension.amount_paid}")

    p.setFont('Times-Italic', 8) 
    p.drawString(60, 17, "Please present the QR code at the parking attendant's booth for booking verification.")
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    
    qr.add_data(paid_reservation.booking.id)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='black', back_color='white')

    buffer_img = BytesIO()
    qr_img.save(buffer_img, format="PNG")
    p.drawImage(ImageReader(buffer_img), 250, 30, width=90, height=90)

    p.showPage()

    p.setPageSize(letter)

    p.setPageSize(landscape(letter)) 

    image_path_second_page = 'parking/static/images/parking_map.png'
    second_page_image = PILImage.open(image_path_second_page)
    image_width, image_height = p._pagesize  

    title_text = "Navigating Mayflower Parking Reservation Area"
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(image_width / 2, image_height - 50, title_text)

    p.drawImage(image_path_second_page, x=0, y=0, width=image_width, height=image_height, preserveAspectRatio=True)

    p.showPage()    
    p.save()

    buffer.seek(0)

    response = FileResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="e-receipt-booking-{paid_reservation.booking.id}.pdf'

    return response

def error_400(request, exception):
    return render(request, 'errors/400.html', status=400)

def error_403(request, exception):
    return render(request, 'errors/403.html', status=403)

def error_404(request, exception):
    return render(request, 'errors/404.html', status=404)

def error_500(request):
    return render(request, 'errors/500.html', status=500)




