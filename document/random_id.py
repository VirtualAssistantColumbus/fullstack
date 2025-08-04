import secrets
import string


def random_id(length=24):
    # Create a sequence of letters and digits
    characters = string.ascii_letters + string.digits
    # Generate a random string of the specified length
    random_id = ''.join(secrets.choice(characters) for i in range(length))
    return random_id