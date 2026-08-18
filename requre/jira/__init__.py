from requre import cassette
from requre.cassette import StorageKeysInspectSimple
from requre.helpers.requests_response import RequestResponseHandling
from requests import sessions

# Intercept all outgoing HTTP calls (Jira REST API via requests)
sessions.Session.send = RequestResponseHandling.decorator(item_list=[1])(
    sessions.Session.send
)

# Use simple key strategy so cassette keys don't embed full call stacks
cassette.StorageKeysInspectDefault = StorageKeysInspectSimple
