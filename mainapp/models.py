from django.contrib.auth.models import User
from django.db import models

# Override the default User model to make the email unique
User._meta.get_field('email')._unique = True

# Make the profile for a user, automatically created when a user is created using Django signals
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} profile'


# Create the Cryptocurrency model
class Cryptocurrency(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cryptocurrencies', null=True)
    id_from_api = models.CharField(max_length=50)
    name = models.CharField(max_length=50) 
    symbol = models.CharField(max_length=10)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return f'{self.name} ({self.symbol})'

# Create the portfolio linked to a user and store the total value of the portfolio
class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolios')
    total_value = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return f'{self.user.username} - Portfolio: {self.total_value}'

class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField()

    def __str__(self):
        return self.subject

class PaymentHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_history')
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    id_from_api = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    success_flag = models.BooleanField()


    def __str__(self):
            return f'{self.user.username} - Payment on {self.payment_date}'