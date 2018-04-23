import datetime

def verify_user(request_data, user, context):
    assert not request_data
    user.is_verified = True
    user.verified_at = datetime.datetime.utcnow()
    user.save()
