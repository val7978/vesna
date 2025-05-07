from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    # Основные страницы
    path('', views.index, name='index'),
    path('modern/', views.modern_art, name='modern'),
    path('summer/', views.summer_art, name='summer'),
    path('geometric/', views.geometric_art, name='geometric'),
    path('novinki/', views.new_arrivals, name='new_arrivals'),
    path('artwork/<int:pk>/', views.artwork_detail, name='artwork_detail'),
    path('search/', views.search, name='search'),
    
    # Пользовательские страницы
    path('profile/', views.profile, name='profile'),
    path('delivery/', views.delivery_info, name='delivery'),
    path('work-registration/', views.work_registration, name='work_registration'),
    
    # Функционал
    path('favorites/', views.favorites, name='favorites'),
    path('cart/', views.cart, name='cart'),
    path('toggle-favorite/<int:artwork_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('add-to-cart/<int:artwork_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    
    # Аутентификация
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Сброс пароля (используем ваши шаблоны)
    path('password-reset/', views.custom_password_reset, name='password_reset'),
    path('password-reset/done/', 
         TemplateView.as_view(template_name='password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', 
         views.custom_password_reset_confirm, 
         name='password_reset_confirm'),
    path('password-reset/complete/', 
         TemplateView.as_view(template_name='password_reset_complete.html'), 
         name='password_reset_complete'),
    
    # Обратная связь
    path('contact/', views.contact, name='contact'),
]