from django.http import JsonResponse
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from .models import *
from .forms import *

def index(request):
    categories = Category.objects.all()
    new_artworks = Artwork.objects.filter(is_new=True)[:8]
    featured_artworks = Artwork.objects.filter(is_featured=True)[:4]
    
    context = {
        'categories': categories,
        'new_artworks': new_artworks,
        'featured_artworks': featured_artworks,
    }
    return render(request, 'general.html', context)

def modern_art(request):
    modern_artworks = Artwork.objects.filter(
        Q(category__name='Живопись') | 
        Q(styles__name='Современное')
    ).distinct()
    
    context = {
        'modern_artworks': modern_artworks,
        'user_favorites': request.user.favorites.all() if request.user.is_authenticated else []
    }
    return render(request, 'modern.html', context)

def summer_art(request):
    summer_artworks = Artwork.objects.filter(
        Q(styles__name='Летнее') | 
        Q(description__icontains='лето')
    ).distinct()
    
    context = {
        'summer_artworks': summer_artworks,
        'user_favorites': request.user.favorites.all() if request.user.is_authenticated else []
    }
    return render(request, 'letnee.html', context)

def geometric_art(request):
    geometric_artworks = Artwork.objects.filter(
        styles__name='Геометрическая абстракция'
    )
    
    context = {
        'geometric_artworks': geometric_artworks,
        'user_favorites': request.user.favorites.all() if request.user.is_authenticated else []
    }
    return render(request, 'geometric.html', context)

def new_arrivals(request):
    new_artworks = Artwork.objects.filter(is_new=True)
    
    context = {
        'new_artworks': new_artworks,
        'user_favorites': request.user.favorites.all() if request.user.is_authenticated else []
    }
    return render(request, 'novinki.html', context)

def artwork_detail(request, pk):
    artwork = get_object_or_404(Artwork, pk=pk)
    is_favorite = False
    in_cart = False
    
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, artwork=artwork).exists()
        in_cart = Cart.objects.filter(user=request.user, artwork=artwork).exists()
    
    context = {
        'artwork': artwork,
        'is_favorite': is_favorite,
        'in_cart': in_cart,
    }
    return render(request, 'image_page.html', context)

@login_required
def toggle_favorite(request, artwork_id):
    artwork = get_object_or_404(Artwork, id=artwork_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, artwork=artwork)
    
    if not created:
        favorite.delete()
        return JsonResponse({'status': 'removed'})
    return JsonResponse({'status': 'added'})

@login_required
def favorites(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('artwork')
    return render(request, 'likes.html', {'favorites': favorites})

@login_required
def add_to_cart(request, artwork_id):
    artwork = get_object_or_404(Artwork, id=artwork_id)
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        artwork=artwork,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    messages.success(request, "Added to cart")
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)
    cart_item.delete()
    messages.success(request, "Removed from cart")
    return redirect('cart')

@login_required
def cart(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('artwork')
    total_price = sum(item.artwork.price * item.quantity for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'korzina.html', context)

@login_required
def checkout(request):
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            cart_items = Cart.objects.filter(user=request.user)
            total_price = sum(item.artwork.price * item.quantity for item in cart_items)
            
            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
                shipping_address=form.cleaned_data['shipping_address'],
                payment_method=form.cleaned_data['payment_method']
            )
            
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    artwork=item.artwork,
                    quantity=item.quantity,
                    price=item.artwork.price
                )
                item.artwork.is_sold = True
                item.artwork.save()
            
            cart_items.delete()
            
            messages.success(request, "Your order has been placed successfully!")
            return redirect('order_detail', order_id=order.id)
    else:
        form = CheckoutForm()
    
    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items:
        messages.warning(request, "Your cart is empty")
        return redirect('index')
    
    total_price = sum(item.artwork.price * item.quantity for item in cart_items)
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'checkout.html', context)

def search(request):
    query = request.GET.get('q', '')
    price_ranges = request.GET.getlist('price_range')
    width_min = request.GET.get('width_min')
    width_max = request.GET.get('width_max')
    height_min = request.GET.get('height_min')
    height_max = request.GET.get('height_max')
    categories = request.GET.getlist('category')
    styles = request.GET.getlist('style')
    
    artworks = Artwork.objects.all()
    
    if query:
        artworks = artworks.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(artist__user__username__icontains=query) |
            Q(artist__user__first_name__icontains=query) |
            Q(artist__user__last_name__icontains=query)
        )
    
    if price_ranges:
        price_filters = Q()
        for pr in price_ranges:
            if pr == '0-10000':
                price_filters |= Q(price__lt=10000)
            elif pr == '10000-50000':
                price_filters |= Q(price__gte=10000, price__lt=50000)
            elif pr == '50000-100000':
                price_filters |= Q(price__gte=50000, price__lt=100000)
            elif pr == '100000-':
                price_filters |= Q(price__gte=100000)
        artworks = artworks.filter(price_filters)
    
    if width_min:
        artworks = artworks.filter(dimensions__contains=f'ширина: {width_min}см')
    if width_max:
        artworks = artworks.filter(dimensions__contains=f'ширина: {width_max}см')
    if height_min:
        artworks = artworks.filter(dimensions__contains=f'высота: {height_min}см')
    if height_max:
        artworks = artworks.filter(dimensions__contains=f'высота: {height_max}см')
    
    if categories:
        artworks = artworks.filter(category__id__in=categories)
    
    if styles:
        artworks = artworks.filter(styles__id__in=styles).distinct()
    
    all_categories = Category.objects.all()
    all_styles = Style.objects.all()
    
    context = {
        'artworks': artworks,
        'query': query,
        'categories': all_categories,
        'styles': all_styles,
    }
    return render(request, 'search.html', context)

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            message = form.save()
            
            send_mail(
                f"New contact message: {form.cleaned_data['subject']}",
                form.cleaned_data['message'],
                form.cleaned_data['email'],
                [settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
            
            messages.success(request, "Your message has been sent successfully!")
            return redirect('contact')
    else:
        form = ContactForm()
    
    return render(request, 'contact.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            if form.cleaned_data.get('is_artist'):
                Artist.objects.create(user=user, bio='')
            
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('index')
    else:
        form = UserRegisterForm()
    
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect('index')
    else:
        form = UserLoginForm()
    
    return render(request, 'login.html', {'form': form})

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('index')

@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ArtistProfileForm(
            request.POST, 
            request.FILES, 
            instance=request.user.artist
        ) if hasattr(request.user, 'artist') else None
        
        if user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            user_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, "Your profile has been updated!")
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ArtistProfileForm(
            instance=request.user.artist
        ) if hasattr(request.user, 'artist') else None
    
    return render(request, 'kabinet.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@login_required
def delivery_info(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Delivery information updated!")
            return redirect('delivery')
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'dastavka.html', {'form': form})

@login_required
def work_registration(request):
    if not hasattr(request.user, 'artist'):
        messages.warning(request, "Only artists can register works")
        return redirect('index')
    
    if request.method == 'POST':
        form = ArtworkForm(request.POST, request.FILES)
        if form.is_valid():
            artwork = form.save(commit=False)
            artwork.artist = request.user.artist
            artwork.save()
            form.save_m2m()
            
            messages.success(request, "Artwork registered successfully!")
            return redirect('artwork_detail', pk=artwork.id)
    else:
        form = ArtworkForm()
    
    return render(request, 'work_registration.html', {'form': form})

def ideas(request):
    gift_ideas = Artwork.objects.filter(
        Q(price__lt=20000) |
        Q(category__name='Керамика') |
        Q(description__icontains='подарок')
    ).distinct()[:12]
    
    context = {
        'gift_ideas': gift_ideas,
        'user_favorites': request.user.favorites.all() if request.user.is_authenticated else []
    }
    return render(request, 'ideas.html', context)

@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user)
    total_price = sum(item.artwork.price * item.quantity for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'cart.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})

@login_required
def favorites_view(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('artwork')
    return render(request, 'favorites.html', {'favorites': favorites})

def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    artworks = Artwork.objects.filter(category=category)
    
    context = {
        'category': category,
        'artworks': artworks,
    }
    return render(request, 'category.html', context)







def index(request):
    categories = Category.objects.all()
    new_artworks = Artwork.objects.order_by('-created_at')[:8]
    featured_artworks = Artwork.objects.filter(is_featured=True)[:4]
    
    context = {
        'categories': categories,
        'new_artworks': new_artworks,
        'featured_artworks': featured_artworks,
    }
    return render(request, 'index.html', context)

def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    artworks = Artwork.objects.filter(category=category)
    
    context = {
        'category': category,
        'artworks': artworks,
    }
    return render(request, 'category.html', context)

def artwork_detail(request, slug):
    artwork = get_object_or_404(Artwork, slug=slug)
    is_favorite = False
    in_cart = False
    
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, artwork=artwork).exists()
        in_cart = Cart.objects.filter(user=request.user, artwork=artwork).exists()
    
    context = {
        'artwork': artwork,
        'is_favorite': is_favorite,
        'in_cart': in_cart,
    }
    return render(request, 'artwork_detail.html', context)

@login_required
def toggle_favorite(request, artwork_id):
    artwork = get_object_or_404(Artwork, id=artwork_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, artwork=artwork)
    
    if not created:
        favorite.delete()
        messages.success(request, "Removed from favorites")
    else:
        messages.success(request, "Added to favorites")
    
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@login_required
def add_to_cart(request, artwork_id):
    artwork = get_object_or_404(Artwork, id=artwork_id)
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        artwork=artwork,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    messages.success(request, "Added to cart")
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@login_required
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(Cart, id=cart_item_id, user=request.user)
    cart_item.delete()
    messages.success(request, "Removed from cart")
    return redirect('cart')

@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user)
    total_price = sum(item.artwork.price * item.quantity for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'cart.html', context)

@login_required
def checkout(request):
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Создаем заказ
            cart_items = Cart.objects.filter(user=request.user)
            total_price = sum(item.artwork.price * item.quantity for item in cart_items)
            
            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
                shipping_address=form.cleaned_data['shipping_address'],
                payment_method=form.cleaned_data['payment_method']
            )
            
            # Добавляем товары в заказ
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    artwork=item.artwork,
                    quantity=item.quantity,
                    price=item.artwork.price
                )
                # Помечаем товар как проданный
                item.artwork.is_sold = True
                item.artwork.save()
            
            # Очищаем корзину
            cart_items.delete()
            
            messages.success(request, "Your order has been placed successfully!")
            return redirect('order_detail', order_id=order.id)
    else:
        form = CheckoutForm()
    
    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items:
        messages.warning(request, "Your cart is empty")
        return redirect('index')
    
    total_price = sum(item.artwork.price * item.quantity for item in cart_items)
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'checkout.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})

@login_required
def favorites_view(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('artwork')
    return render(request, 'favorites.html', {'favorites': favorites})

def search(request):
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    
    artworks = Artwork.objects.all()
    
    if query:
        artworks = artworks.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(artist__user__username__icontains=query) |
            Q(artist__user__first_name__icontains=query) |
            Q(artist__user__last_name__icontains=query)
        )
    
    if category_slug:
        artworks = artworks.filter(category__slug=category_slug)
    
    categories = Category.objects.all()
    
    context = {
        'artworks': artworks,
        'query': query,
        'categories': categories,
        'selected_category': category_slug,
    }
    return render(request, 'search.html', context)

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Сохраняем сообщение в базу данных
            message = ContactMessage.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                subject=form.cleaned_data['subject'],
                message=form.cleaned_data['message']
            )
            
            # Отправляем email
            send_mail(
                f"New contact message: {form.cleaned_data['subject']}",
                form.cleaned_data['message'],
                form.cleaned_data['email'],
                [settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
            
            messages.success(request, "Your message has been sent successfully!")
            return redirect('contact')
    else:
        form = ContactForm()
    
    return render(request, 'contact.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Создаем профиль художника, если отмечена соответствующая галочка
            if form.cleaned_data.get('is_artist'):
                Artist.objects.create(user=user, bio='')
            
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('index')
    else:
        form = UserRegisterForm()
    
    return render(request, 'registration/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect('index')
    else:
        form = UserLoginForm()
    
    return render(request, 'registration/login.html', {'form': form})

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('index')

@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ArtistProfileForm(request.POST, request.FILES, instance=request.user.artist)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated!")
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ArtistProfileForm(instance=request.user.artist)
    
    return render(request, 'profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

def custom_password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                email_template_name='sbros1.html',
                subject_template_name='password_reset_subject.txt'
            )
            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()
    
    return render(request, 'sbros1.html', {'form': form})

def custom_password_reset_confirm(request, uidb64, token):
    if request.method == 'POST':
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return redirect('password_reset_complete')
    else:
        form = SetPasswordForm(request.user)
    
    return render(request, 'sbros2.html', {'form': form})