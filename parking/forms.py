import re
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm, UsernameField, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox
from .models import *

class UserCreateForm(UserCreationForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'type': 'text', 'name': 'first_name', 'id': 'first_name', 'placeholder': 'First Name', 'required': 'required'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'type': 'text', 'name': 'last_name', 'id': 'last_name', 'placeholder': 'Last Name', 'required': 'required'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'type': 'text', 'name': 'username', 'id': 'username', 'placeholder': 'Username', 'required': 'required', 'autofocus': False}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'type': 'email', 'name': 'email', 'id': 'email', 'placeholder': 'Email', 'required': 'required'}))
    contact_number = forms.CharField(max_length=11, widget=forms.TextInput(attrs={'type': 'tel', 'name': 'contact_number', 'id': 'contact_number', 'placeholder': 'Contact Number', 'required': 'required', 'pattern': '09[0-9]{9}'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'type': 'password', 'name': 'password1', 'id': 'password1', 'placeholder': 'Password', 'required': 'required', 'class': 'password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'type': 'password', 'name': 'password2', 'id': 'password2', 'placeholder': 'Confirm Password', 'required': 'required', 'class': 'password'}))
    agreed_to_terms = forms.BooleanField(widget=forms.CheckboxInput(attrs={'id': 'agreed_to_terms', 'required': 'required'}))

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'email', 'contact_number', 'password1', 'password2', 'agreed_to_terms']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'autofocus': False})    

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']

        if not first_name:
            raise ValidationError('This field is required.')
        if not first_name.replace(" ", "").isalpha():
            raise ValidationError('First name should contain only letters and spaces.')
        
        return first_name.title()

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name']

        if not last_name:
            raise ValidationError('This field is required.')
        if not last_name.replace(" ", "").isalpha():
            raise ValidationError('Last name should contain only letters and spaces.')
        
        return last_name.title()
    
    def clean_username(self):
        username = self.cleaned_data['username']

        if not username:
            raise ValidationError('This field is required.')
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters long.')
        if len(username) > 20:
            raise ValidationError('Username cannot be longer than 20 characters.')
        if not re.match("^[a-zA-Z0-9]+$", username):
            raise ValidationError('Username should only contain letters and numbers.')
        if ' ' in username or not username.isalnum():
            raise ValidationError('Username cannot contain spaces or special characters.')
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError('This username is already registered.')
        
        return username.lower()
    
    def clean_email(self):
        email = self.cleaned_data['email']

        try: 
            validate_email(email)
        except ValidationError:
            raise ValidationError('Enter a valid email address.')
        
        if not email:
            raise ValidationError('This field is required.')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('This email address is already registered.')
        
        return email

    def clean_contact_number(self):
        contact_number = self.cleaned_data['contact_number']

        if not contact_number:
            raise ValidationError('This field is required.')
        if not contact_number.isdigit():
            raise ValidationError('Contact number should consist only of numeric characters.')
        if len(contact_number) != 11:
            raise ValidationError('Contact number should be 11 digits long.')
        if CustomUser.objects.filter(contact_number=contact_number).exists():
            raise ValidationError('This contact number is already registered.')

        valid_prefixes = ['090', '091', '092', '093', '094', '095', '096', '097', '098', '099']
        if not contact_number.startswith(tuple(valid_prefixes)):
            raise ValidationError('Invalid mobile number prefix - (09xx)')
        
        return contact_number     

class VehicleForm(forms.ModelForm):
    license_plate = forms.CharField(required=True, widget=forms.TextInput(attrs={'type': 'text', 'name': 'license_plate', 'id': 'license_plate', 'placeholder': 'License Plate Number'}))
    vehicle_make = forms.CharField(required=True, widget=forms.TextInput(attrs={'type': 'text', 'name': 'vehicle_make', 'id': 'vehicle_make', 'placeholder': 'Vehicle Make'}))
    vehicle_model = forms.CharField(required=True, widget=forms.TextInput(attrs={'type': 'text', 'name': 'vehicle_model', 'id': 'vehicle_model', 'placeholder': 'Vehicle Model'}))
    vehicle_color = forms.CharField(required=True, widget=forms.TextInput(attrs={'type': 'text', 'name': 'vehicle_color', 'id': 'vehicle_color', 'placeholder': 'Vehicle Color'}))
    vehicle_photo = forms.ImageField(required=True, label='Upload Vehicle Photo')
    
    class Meta:
        model = Vehicle
        fields = ['license_plate', 'vehicle_make', 'vehicle_model', 'vehicle_color', 'vehicle_photo']

    def clean_license_plate(self):
        license_plate = self.cleaned_data['license_plate']

        private_vehicle_plate_pattern = re.compile(r'^[A-Z]{3}-\d{3,4}$')

        if not license_plate:
            raise ValidationError('This field is required.')
        if Vehicle.objects.filter(license_plate=license_plate).exists():
            raise ValidationError('This license plate is already registered.')
        if not private_vehicle_plate_pattern.match(license_plate):
            raise ValidationError('License plate should be in the format LLL-DDD or LLL-DDDD.')
                    
        return license_plate

class CustomAuthenticationForm(AuthenticationForm):
    username = UsernameField(widget=forms.TextInput(
        attrs={'type': 'text', 'name': 'username', 'id': 'username', 'placeholder': 'Username', 'required': 'required'}
    ))

    password = forms.CharField(widget=forms.PasswordInput(
        attrs={'type': 'password', 'name': 'password', 'id': 'password', 'placeholder': 'Password', 'required': 'required'}
    ))

    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    error_messages = {
        'invalid_login': "Invalid login. Please check your credentials.",
    }

class UserEditForm(UserChangeForm):
    first_name = forms.CharField(label='First Name')
    last_name = forms.CharField(label='Last Name')
    username = forms.CharField(label='Username')
    email = forms.CharField(label='Email Address', required=True)
    contact_number = forms.CharField(label='Contact Number', max_length=11)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'contact_number']

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']

        if not first_name.replace(" ", "").isalpha():
            raise ValidationError('First name should contain only letters and spaces.')
        
        return first_name.title()

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name']

        if not last_name.replace(" ", "").isalpha():
            raise ValidationError('Last name should contain only letters and spaces.')
        
        return last_name.title()
    
    def clean_username(self):
        username = self.cleaned_data['username']

        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters long.')
        if len(username) > 20:
            raise ValidationError('Username cannot be longer than 20 characters.')
        if not re.match("^[a-zA-Z0-9]+$", username):
            raise ValidationError('Username should only contain letters and numbers.')
        if ' ' in username or not username.isalnum():
            raise ValidationError('Username cannot contain spaces or special characters.')
        if CustomUser.objects.filter(username=username).exclude(id=self.instance.id).first():
            raise ValidationError('This username is already registered.')
        
        return username.lower()
    
    def clean_email(self):
        email = self.cleaned_data['email']

        try: 
            validate_email(email)
        except ValidationError:
            raise ValidationError('Enter a valid email address.')

        if CustomUser.objects.filter(email=email).exclude(id=self.instance.id).first():
            raise ValidationError('This email address is already registered.')
        
        return email

    def clean_contact_number(self):
        contact_number = self.cleaned_data['contact_number']

        if not contact_number.isdigit():
            raise ValidationError('Contact number should consist only of numeric characters.')
        if len(contact_number) != 11:
            raise ValidationError('Contact number should be 11 digits long.')
        if CustomUser.objects.filter(contact_number=contact_number).exclude(id=self.instance.id).first():
            raise ValidationError('This contact number is already registered.')

        valid_prefixes = ['090', '091', '092', '093', '094', '095', '096', '097', '098', '099']
        if not contact_number.startswith(tuple(valid_prefixes)):
            raise ValidationError('Invalid mobile number prefix - (09xx)')
        
        return contact_number 

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'})
    )
    
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'})
    )