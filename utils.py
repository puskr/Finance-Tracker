from itsdangerous import URLSafeTimedSerializer

# Secret key used for encoding and decoding tokens
SECRET_KEY = "your-super-secret-key"
SECURITY_PASSWORD_SALT = "some-random-salt"

def generate_reset_token(username, expires_sec=1800):
    """Generate a password reset token."""
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(username, salt=SECURITY_PASSWORD_SALT)

def verify_reset_token(token, expires_sec=1800):
    """Verify the token and extract the username if valid."""
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    try:
        username = serializer.loads(token, salt=SECURITY_PASSWORD_SALT, max_age=expires_sec)
    except Exception:
        return None
    return username
