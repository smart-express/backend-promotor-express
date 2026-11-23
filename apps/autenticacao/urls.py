from django.urls import path
from .views import LoginPromotorView
urlpatterns = [path("login/", LoginPromotorView.as_view(), name="promotor-login")]
