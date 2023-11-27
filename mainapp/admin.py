from django.contrib import admin
from .models import Cryptocurrency, Portfolio, Profile, Referal, PaymentHistory


@admin.register(Referal)
class ReferalAdmin(admin.ModelAdmin):
    list_display = ('user', 'referrer')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'referral_code', 'bonus')

@admin.register(Cryptocurrency)
class CryptocurrencyAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'id_from_api', 'symbol', 'current_price', 'quantity')

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_value')

@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'payment_date', 'amount', 'id_from_api', 'name', 'quantity', 'success_flag')

