from django.contrib import admin

from .models import (
    BurialSubscription,
    CareSubscription,
    ChatMessage,
    Donation,
    ExecutorServiceOffer,
    Notification,
    Order,
    OrderPhoto,
    OrderReview,
    PowerOfAttorneyDocument,
    ServiceType,
)

admin.site.register(ServiceType)
admin.site.register(Order)
admin.site.register(OrderPhoto)
admin.site.register(OrderReview)
admin.site.register(PowerOfAttorneyDocument)
admin.site.register(ChatMessage)
admin.site.register(Notification)
admin.site.register(BurialSubscription)
admin.site.register(Donation)
admin.site.register(CareSubscription)
admin.site.register(ExecutorServiceOffer)
