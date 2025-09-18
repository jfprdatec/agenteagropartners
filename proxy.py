import json

# global variables

PERMITTED_CHANNELS = (
    "Channel::Email"
)


# main

def is_request_allowed(request):

    body = request.get_json(silent=True)
    
    if body is None:
        return False

    request_channel = body.get("conversation", {}).get("channel")

    return request_channel in PERMITTED_CHANNELS