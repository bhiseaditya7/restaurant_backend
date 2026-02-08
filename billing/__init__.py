from django.db.models.signals import post_migrate
from django.dispatch import receiver
# # from .models import User

@receiver(post_migrate)
def create_default_user(sender, **kwargs):
    from django.contrib.auth import get_user_model
#     User = get_user_model()
    # from .models import User
    from .models import User


    if not User.objects.filter(name="adityaa").exists():
        user = User(
            name="adityaa",
            email="bhiseaditya874@gmail.com",
            phone_number="+918605423238",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        user.set_password("Ronaldo@11")  # 🔐 hash here
        user.save()

    if not User.objects.filter(name="saishwar").exists():
        user = User(
            name="saishwar",
            email="saishwar@example.com",
            phone_number="+919049572207",
            is_active=True,
            is_staff=True,
            # is_superuser=True,
        )
        user.set_password("saishwar@11")  # 🔐 hash here
        user.save()
