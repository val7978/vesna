from django.contrib import admin
from .models import *

class ArtworkAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'category', 'price', 'is_featured', 'is_new')
    list_filter = ('category', 'is_featured', 'is_new')
    search_fields = ('title', 'artist__user__username', 'description')
    filter_horizontal = ('styles',)

class ArtistAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio_short')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'bio')
    
    def bio_short(self, obj):
        return obj.bio[:50] + '...' if len(obj.bio) > 50 else obj.bio
    bio_short.short_description = 'Bio'

admin.site.register(Category)
admin.site.register(Style)
admin.site.register(Artist, ArtistAdmin)
admin.site.register(Artwork, ArtworkAdmin)
admin.site.register(Favorite)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ContactMessage)
