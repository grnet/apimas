from django.contrib import admin
from .models import UserProfile
from .models import Country
from .models import City
from .models import Product
from .models import Cart
from .models import Order
from .models import Manufacturer


admin.site.register(UserProfile)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(Country)
admin.site.register(City)
admin.site.register(Manufacturer)
# Register your models here.
