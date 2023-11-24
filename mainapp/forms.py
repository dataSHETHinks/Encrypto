from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        required=True,
        label='Username',
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    email = forms.EmailField(
        required=True,
        label='Email',
        help_text='Required. Enter a valid email address.',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    password1 = forms.CharField(
        required=True,
        label='Password',
        help_text='Required. Enter a valid password.',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    password2 = forms.CharField(
        required=True,
        label='Password confirmation',
        help_text='Enter the same password as before, for verification.',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    id_or_photo = forms.ImageField(
        required=True,
        label='Upload a Valid ID or Photo',
        help_text='Required. Upload a valid ID or photo.',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg, image/png, image/jpg'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'id_or_photo']
