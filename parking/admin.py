from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from .models import  *

class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'contact_number',
        'is_banned', 'ban_end_time', 'is_logged_in', 'last_logout', 'date_joined'
    )

    list_editable = ('is_banned', )

    ordering = ('-date_joined', )

    search_fields = ('first_name', 'last_name', 'username', 'email')

    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'email', 'contact_number')
        }),
        ('User status', {
            'fields': ('is_banned', 'ban_end_time')
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
                )
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        })
    )

    add_fieldsets = (
        (None, {
            'fields': ('username', 'password1', 'password2')
        }),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'email', 'contact_number')
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
        ('Additional info', {
            'fields': ('is_banned', 'ban_end_time')
        })
    )

admin.site.register(CustomUser, CustomUserAdmin)

class UserAgreementAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'agreed_to_terms'
    )

admin.site.register(UserAgreement, UserAgreementAdmin)

class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        'license_plate', 'vehicle_model', 'vehicle_make', 'vehicle_color', 'owner', 'vehicle_photo',
    )

    search_fields = ('license_plate', 'vehicle_model', 'vehicle_make', 'vehicle_color', 'owner')

    fieldsets = (
        (None, {
            'fields': ('owner', 'license_plate', 'vehicle_model', 'vehicle_make', 'vehicle_color', 'vehicle_photo',)
        }),
    )
        
    add_fieldsets = (
        (None, {
            'fields': ('license_plate', 'vehicle_model', 'vehicle_make', 'vehicle_color', 'owner', 'vehicle_photo',)
        })
    )

admin.site.register(Vehicle, VehicleAdmin)

class SlotAdmin(admin.ModelAdmin):

    list_display = (
        'number', 'status',
    )

    list_editable = ('status', )

    ordering = ('number', )

    list_filter = ('status', )

    fieldsets = (
        (None, {
            'fields': ('number', 'status')
        }),
    )

    add_fieldsets = (
        (None, {
            'fields': ('number', 'status')
        })
    )

admin.site.register(Slot, SlotAdmin)

class BookingAdmin(admin.ModelAdmin):

    list_display = (
        'slot', 'user', 'start_time', 'expiration_time', 'is_valid', 'extended'
    )

    list_filter = ('is_valid', 'extended')

    ordering = ('created_at', )

    fieldsets = (
        (None, {
            'fields': ('slot', 'user', 'vehicle', 'start_time', 'expiration_time', 'end_time', 'is_valid', 'extended'),
        }),
    )

admin.site.register(Booking, BookingAdmin)

class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'booking', 'fee_type', 'amount_paid', 'payment_status'
    )

    list_filter = ('payment_status', )

    fieldsets = (
        (None, {
            'fields': ('booking', 'fee_type', 'amount_paid', 'payment_status')
        }),
    )

admin.site.register(Payment, PaymentAdmin)

class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        'payment',
    )

    fieldsets = (
        (None, {
            'fields': ('payment',)
        }),
    )

admin.site.register(Receipt, ReceiptAdmin)

class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'notification_type'
    )

    fieldsets = (
        (None, {
            'fields': ('user', 'notification_type', 'message', 'is_read')
        }),
    )

    add_fieldsets = (
        (None, {
            'fields': ('user', 'notification_type', 'message')
        }),
    )

admin.site.register(Notification, NotificationAdmin)

class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        'payment', 'rating', 'comments'
    )

    fieldsets = (
        (None, {
            'fields': ('payment', 'rating', 'comments')
        }),
    )

    add_fieldsets = (
        (None, {
            'fields': ('payment', 'rating', 'comments')
        }),
    )

admin.site.register(Feedback, FeedbackAdmin)

# Unregister default models 
admin.site.unregister(Group)
