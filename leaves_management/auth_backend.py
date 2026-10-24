from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

def normalize_arabic(text):
    if not text:
        return text
    text = text.strip()
    # Normalize Alef variations
    text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    # Normalize Ya / Alef Maksura
    text = text.replace('ى', 'ي')
    # Normalize Ta Marbuta
    text = text.replace('ة', 'ه')
    return text

class ArabicNormalizedAuthBackend(ModelBackend):
    """
    Allows login with Arabic username even if differences in ى/ي or أ/ا occur.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # 1. Try exact match first
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass

        # 2. Try normalized match
        norm_input = normalize_arabic(username)
        for user in User.objects.all():
            if normalize_arabic(user.username) == norm_input:
                if user.check_password(password):
                    return user
                # If password was also typed with normalized variation (e.g. مدني instead of مدنى)
                for alt_pass in [password, password.replace('ي', 'ى'), password.replace('ى', 'ي')]:
                    if user.check_password(alt_pass):
                        return user

        return None
