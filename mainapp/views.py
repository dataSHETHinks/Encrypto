import requests
from django.contrib import auth, messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.template.defaultfilters import slugify
from django.utils.http import urlsafe_base64_decode

from .forms import CustomUserCreationForm, ContactForm, SubscriptionForm
from .models import Cryptocurrency, Portfolio, Profile, Referal
from decimal import Decimal


def login_view(request):
    # check if user is already logged in
    if request.user.is_authenticated:
        return redirect('portfolio')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=raw_password)
            if user is not None:
                login(request, user)
                return redirect('/')
        else:
            messages.error(request, "Invalid username or password.", extra_tags='danger')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


@login_required(login_url="login")
def logout_view(request):
    logout(request)
    messages.success(request, 'You have successfully logged out!')
    return redirect('home')


def signup_view(request):
    # check if user is already logged in
    if request.user.is_authenticated:
        return redirect('portfolio')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        print("form is", form)
        if form.is_valid():
            print("yes")
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data['password1'])
            user.email = form.cleaned_data['email']
            user.save()
            messages.success(request, 'You have successfully signed up!', extra_tags='success')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})


# block access to signup page if user is already logged in
def signup_with_referrer_view(request, referral_code):
    # check if user is already logged in
    if request.user.is_authenticated:
        return redirect('portfolio')

    try:
        # get the User Profile of the referrer
        referrer = User.objects.get(profile__referral_code=referral_code)
    except User.DoesNotExist:
        # show error message if referrer does not exist
        return HttpResponse("Referrer does not exist")

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data['password1'])
            user.email = form.cleaned_data['email']
            user.save()
            # create a referral instance
            referral = Referal.objects.create(user=user, referrer=referrer)
            referral.save()

            if referrer is not None:
                referrer.profile.bonus += 100  # add referral bonus to referrer
                referrer.profile.save()
                messages.success(request,
                                 f'{referrer.username} recieved a bonus of 100 points from you because you signed up using their referral link!')

            messages.success(request, 'You have successfully signed up!')
            return redirect('login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'signup.html', {'form': form, 'referrer': referrer})


@login_required(login_url="login")
def portfolio_view(request):
    # get the current logged in user
    current_user = request.user

    # get the referal code of the current user
    referral_code = current_user.profile.referral_code

    # get a list of all users who have the current user as their referrer
    referrals = Referal.objects.filter(referrer=current_user)

    # get total bonus earned by the current user
    total_bonus = current_user.profile.bonus

    # get the list of cryptocurrencies owned by the current user
    user_cryptocurrencies = Cryptocurrency.objects.filter(user=current_user)

    if len(user_cryptocurrencies) == 0:
        context = {
            'current_user': current_user,
            'user_cryptocurrencies': user_cryptocurrencies,
            'new_portfolio_value': 0.0,
            'margin': 0
        }
        return render(request, 'portfolio.html', context)

    if user_portfolio := Portfolio.objects.filter(user=current_user).first():
        portfolio = Portfolio.objects.get(user=current_user)

        # get all the crypto currencies in the portfolio and recalculate the total value of the portfolio
        new_portfolio_value = 0.0
        sp_sum = 0.0
        bp_sum = 0.0

        user_cryptocurrencies = Cryptocurrency.objects.filter(user=current_user)
        all_user_crypto = []

        for crypto in user_cryptocurrencies:
            api_url = f'https://api.coingecko.com/api/v3/simple/price?ids={crypto.id_from_api}&vs_currencies=usd'
            try:
                response = requests.get(api_url)
                response.raise_for_status()
                data = response.json()
                curr = data[crypto.id_from_api]['usd']
                new_crypto_data = {
                    'id': crypto.id,
                    'name': crypto.name,
                    'id_from_api': crypto.id_from_api,
                    'current_price': crypto.current_price,
                    'quantity': crypto.quantity,
                    'now': curr,
                }
                all_user_crypto.append(new_crypto_data)
                sp_sum = sp_sum + (float(new_crypto_data['now']) * float(new_crypto_data['quantity']))
                bp_sum = bp_sum + (float(crypto.current_price) * float(crypto.quantity))

            except requests.exceptions.RequestException as e:
                return redirect('rate_limit_err')

        try:
            for cryptocurrency in all_user_crypto:
                total_value = float(cryptocurrency['quantity']) * float(cryptocurrency['now'])
                new_portfolio_value += total_value
        except TypeError as e:
            return redirect('rate_limit_err')
        portfolio.total_value = new_portfolio_value
        portfolio.save()

        context = {
            'current_user': current_user,
            'user_cryptocurrencies': all_user_crypto,
            'user_portfolio': user_portfolio,
            'new_portfolio_value': new_portfolio_value,
            'margin': ((sp_sum - bp_sum) / sp_sum) * 100
        }
    return render(request, 'portfolio.html', context)


def home_view(request):
    # Get the top 10 cryptocurrencies by market cap
    try:

        top_10_crypto_url_global = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=USD&order=market_cap_desc&per_page=10&page=1&sparkline=true'
        top_10_crypto_data_global = requests.get(top_10_crypto_url_global).json()

        # Get the trending cryptocurrencies
        trending_crypto_url = 'https://api.coingecko.com/api/v3/search/trending'
        trending_crypto_data = requests.get(trending_crypto_url).json()

        # Get highlights data
        highlights_data = Cryptocurrency.objects.all().order_by('-current_price')[:3]

        # Get the latest 3 cryptocurrencies based on date added
        latest_3_added = Cryptocurrency.objects.all().order_by('-id')[:3]

        # Initialize the subscription form
        subscription_form = SubscriptionForm()

        # Handle the subscription form submission
        if request.method == 'POST':
            subscription_form = SubscriptionForm(request.POST)
            if subscription_form.is_valid():
                messages.success(request, 'You are all set!')
                return redirect('home')  # Redirect to clear POST data and avoid resubmitting the form

        # Check if the user is authenticated
        if request.user.is_authenticated:
            # Get user's cryptocurrencies and portfolio
            user_cryptocurrencies = Cryptocurrency.objects.filter(user=request.user)
            user_portfolio = Portfolio.objects.filter(user=request.user).first()

            # Get the prices and price changes for user's cryptocurrencies
            names = [crypto.name for crypto in user_cryptocurrencies]
            symbols = [crypto.symbol for crypto in user_cryptocurrencies]
            ids = [crypto.id_from_api for crypto in user_cryptocurrencies]
            prices = []

            try:
                for crypto_id in ids:
                    prices_url = f'https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd&include_24hr_change=true'
                    prices_data = requests.get(prices_url).json()
                    price_change = prices_data[crypto_id]['usd_24h_change']
                    prices.append(price_change)
            except Exception as e:
                return redirect('rate_limit_err')

            # Create a dictionary of names and prices
            crypto_price_changes = dict(zip(names, prices))

            context = {
                'top_10_crypto_data_global': top_10_crypto_data_global,
                'user_cryptocurrencies': user_cryptocurrencies,
                'user_portfolio': user_portfolio,
                'crypto_price_changes': crypto_price_changes,
                'highlights_data': highlights_data,
                'trending_crypto_data': trending_crypto_data,
                'latest_3_added': latest_3_added,
                'subscription_form': subscription_form,
            }
        else:
            context = {
                'top_10_crypto_data_global': top_10_crypto_data_global,
                'highlights_data': highlights_data,
                'trending_crypto_data': trending_crypto_data,
                'latest_3_added': latest_3_added,
                'subscription_form': subscription_form,  # Add the subscription form to the context
            }

        return render(request, 'home.html', context)
    except:
        return redirect('rate_limit_err')


def search_view(request):
    if request.method != 'POST':
        # return HTTP status code 405 if the request method is not POST along with a message
        return HttpResponseNotAllowed(['POST'],
                                      'Only POST requests are allowed for this view. Go back and search a cryptocurrency.')

    if not (search_query := request.POST.get('search_query')):
        return HttpResponse('No crypto currency found based on your search query.')

    api_url = f'https://api.coingecko.com/api/v3/search?query={search_query}'
    response = requests.get(api_url)
    search_results = response.json()
    cryptocurrencies = []
    for data in search_results.get('coins', []):
        coin_id = data.get('id')
        image = data.get('large')
        symbol = data.get('symbol')
        market_cap = data.get('market_cap_rank')
        print(coin_id)

        cryptocurrency_info = {
            'data': data,
            'coin_id': coin_id,
            'image': image,
            'symbol': symbol,
            'market_cap': market_cap,
            # 'is_already_in_portfolio': is_already_in_portfolio,
        }

        cryptocurrencies.append(cryptocurrency_info)
    context = {
        'cryptocurrencies': cryptocurrencies,
        'search_query': search_query,
    }
    return render(request, 'search.html', {"cryptocurrencies": cryptocurrencies})


@login_required(login_url="login")
def checkout(request):
    if request.method != 'POST':
        return HttpResponse("Please select crypto currency to add to your portfolio.")

    coin_id = request.POST.get('id')
    quantity = request.POST.get('quantity')
    api_url = f'https://api.coingecko.com/api/v3/coins/{coin_id}'
    response = requests.get(api_url)
    data = response.json()
    crypto = {
        'user': request.user,
        'name': data['name'],
        'id_from_api': coin_id,
        'symbol': data['symbol'],
        'current_price': data['market_data']['current_price']['usd'],
        'quantity': quantity
    }
    context = {
        'crypto': crypto,
        'amount': float(quantity) * float(crypto['current_price'])
    }
    return render(request, 'checkout.html', context)


@login_required(login_url="login")
def checkout_complete(request):
    if request.method != "POST":
        return HttpResponse("Error in checkout")

    ccn = request.POST.get('ccn')

    if ccn == '4242424242424242424':
        # ----------------------------------------------------
        # code to update payment history with failed payment
        # ----------------------------------------------------
        return HttpResponse("Error in checkout")
    else:
        user = request.user
        try:
            curr_crypto = Cryptocurrency.objects.filter(user=user, name=request.POST.get('cname'))
            if len(curr_crypto) != 0:
                curr_crypto = curr_crypto[0]
                curr_crypto.current_price = float(request.POST.get('current_price'))
                curr_crypto.quantity += int(request.POST.get('quantity'))
                curr_crypto.save()
            else:
                # save the crypto currency to the database
                crypto_currency = Cryptocurrency.objects.create(
                    user=user,
                    name=request.POST.get('cname'),
                    id_from_api=request.POST.get('id_from_api'),
                    symbol=request.POST.get('symbol'),
                    quantity=request.POST.get('quantity'),
                    current_price=request.POST.get('current_price'),
                )
                crypto_currency.save()
        except Exception as e:
            print(e)

        # ----------------------------------------------------
        # code to update payment history with success payment
        # ----------------------------------------------------

        # calculate the total value of the crypto currency
        total_value = float(request.POST.get('quantity')) * float(request.POST.get('current_price'))

        # save the total value of the crypto currency to the database in the portfolio model
        # check if the user already has a portfolio
        if Portfolio.objects.filter(user=request.user).exists():
            portfolio = Portfolio.objects.get(user=request.user)
            portfolio.total_value += Decimal(total_value)
        else:
            portfolio = Portfolio(user=request.user, total_value=total_value)

        portfolio.save()
        messages.success(request, f'{request.POST.get("cname")} has been added to your portfolio.')
        return redirect('portfolio')


@login_required(login_url="login")
def add_to_portfolio_view(request):
    if request.method != 'POST':
        return HttpResponse('Need a crypto currency to add to your portfolio. Go back to the home page and search for '
                            'a crypto currency.')

    # get values from the form
    coin_id = request.POST.get('id')
    quantity = request.POST.get('quantity')
    print(coin_id)

    # get the crypto currency data from the coingecko api based on the coin id
    api_url = f'https://api.coingecko.com/api/v3/coins/{coin_id}'
    response = requests.get(api_url)
    data = response.json()
    print(data)
    # store the name, symbol, current price, and market cap rank of the crypto currency
    user = request.user
    name = data['name']
    id_from_api = data['id']
    symbol = data['symbol']
    current_price = data['market_data']['current_price']['usd']

    try:
        # save the crypto currency to the database
        crypto_currency = Cryptocurrency.objects.create(
            user=user,
            name=name,
            id_from_api=id_from_api,
            symbol=symbol,
            quantity=quantity,
            current_price=current_price,
        )
    except IntegrityError:
        crypto_currency = Cryptocurrency.objects.get(user=user, name=name)
        crypto_currency.quantity += int(quantity)

    crypto_currency.save()

    # calculate the total value of the crypto currency
    total_value = int(quantity) * int(current_price)

    # save the total value of the crypto currency to the database in the portfolio model
    # check if the user already has a portfolio
    if Portfolio.objects.filter(user=user).exists():
        portfolio = Portfolio.objects.get(user=user)
        portfolio.total_value += total_value
    else:
        portfolio = Portfolio(user=user, total_value=total_value)

    portfolio.save()
    messages.success(request, f'{name} has been added to your portfolio.')

    # if all the above steps are successful, redirect the user to the portfolio page
    return redirect('portfolio')


@login_required(login_url="login")
def delete_from_portfolio_view(request, pk):
    # get the current logged in user
    user = request.user
    sp = request.GET.get('sp', None)
    if sp is None:
        # Do something with sp_value
        messages.warning(request, f'Failed to obtain selling price!')
        return redirect('portfolio')
    sp = float(sp)

    # get the crypto currency object from the database
    crypto_currency = Cryptocurrency.objects.get(pk=pk)

    # delete the crypto currency from the database
    # crypto_currency.delete()

    # update the total value of the portfolio
    portfolio = Portfolio.objects.get(user=user)
    portfolio.total_value = float(portfolio.total_value) - (float(crypto_currency.quantity) * sp)

    crypto_currency.delete()
    portfolio.save()

    # get all the crypto currencies in the portfolio and recalculate the total value of the portfolio
    # user_cryptocurrencies = Cryptocurrency.objects.filter(user=user)
    # for cryptocurrency in user_cryptocurrencies:
    #     total_value = cryptocurrency.quantity * sp
    #     portfolio.total_value += total_value

    # portfolio.save()

    # send an alert to the user that the crypto currency has been deleted from the portfolio
    messages.warning(request, f'{crypto_currency.name} has been deleted from your portfolio.')

    return redirect('portfolio')


def about_us(request):
    return render(request, 'aboutUs.html')


def terms_of_service(request):
    return render(request, 'termsAndConditions.html')


def privacy_policy(request):
    return render(request, 'privacyPolicy.html')


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Process the form data
            form.save()
            # Add success message
            messages.success(request, 'Email Sent Successfully!')
            return redirect('contact')  # Redirect back to the contact page or another page
    else:
        form = ContactForm()

    return render(request, 'contactUs.html', {'form': form})


def rate_limit_err(request):
    return render(request, 'rate_limit.html')
