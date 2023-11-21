from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    
    # user authentication
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    
    path("signup/", views.signup_view, name="signup"),
    path('signup/<str:referral_code>/', views.signup_with_referrer_view, name='signup_with_referrer_view'),

    # wallet page
    path("portfolio/", views.portfolio_view, name="portfolio"),
    
    # CRUD operations on cryptos
    path("search/", views.search_view, name="search"),
    path("add_to_portfolio/", views.add_to_portfolio_view, name="add_to_portfolio"),
    path('delete_from_portfolio/<int:pk>/', views.delete_from_portfolio_view, name='delete_from_portfolio'),
    
    # password reset stuff
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name="reset/password_reset.html"), name='password_reset'),
    
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name="reset/password_reset_done.html"), name='password_reset_done'),
    
    path('password_reset_confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
    template_name='reset/password_reset_confirm.html'), name='password_reset_confirm'),

    path('password_reset_complete/', auth_views.PasswordResetCompleteView.as_view(
    template_name='reset/password_reset_complete.html'), name='password_reset_complete'),


    path('about-us', views.about_us, name = "about_us"),
    path('terms-and-conditions', views.terms_of_service, name = "terms_of_service"),
    path('privacy-policy', views.privacy_policy, name = 'privacy_policy'),
    path('contact-us', views.contact_us, name = 'contact_us'),
    path('rate_limit_err/', views.rate_limit_err, name="rate_limit_err")
]

