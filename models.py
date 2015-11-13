from google.appengine.ext import ndb

class Event(ndb.Model):
    name = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    slug = ndb.StringProperty()


class Attendee(ndb.Model):

    name = ndb.StringProperty()
    event_name = ndb.StringProperty(indexed=True)
    is_checked = ndb.BooleanProperty(default=False)
    is_imprompto = ndb.BooleanProperty(default=False)
