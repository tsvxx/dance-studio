from django.contrib.auth.decorators import user_passes_test
def role_required(*roles):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_superuser or u.role in roles))
