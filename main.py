"""`main` is the top level module for your Flask application."""
from __future__ import absolute_import
import logging
import slugify

# Import the Flask Framework
import flask
from flask import Flask
from flask_wtf import Form
from flask_wtf.file import FileField
from flask_wtf.file import FileAllowed
from wtforms import BooleanField
from wtforms import StringField
from wtforms.validators import DataRequired
from google.appengine.api import users
from google.appengine.api import memcache
from werkzeug import secure_filename

from util import login
import models


logger = logging.getLogger(__name__)


app = Flask(__name__)
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

APP_NAME = 'fork_please'


@app.route('/me')
@login.login_required
def me():
    return flask.render_template(
        'me.html',
        title=APP_NAME,
        user=users.get_current_user(),
    )

class EventUploadForm(Form):

    event_name = StringField('Event Name', validators=[DataRequired()])
    names_csv = FileField(
        'Names File',
        validators=[
            FileAllowed(
                ('csv',),
                'Only csv',
            ),
        ],
    )

class ToggleForm(Form):

    event = StringField('Event Name', validators=[DataRequired()])
    attendee_name = StringField(
        'Name',
    )
    is_checked = BooleanField()

def upsert_event(name):
    event_slug = slugify.slugify(name)
    event = models.Event.get_or_insert(
        event_slug,
        name=name,
        slug=event_slug,
    )
    event.name = name
    event.put()
    return event

def upsert_attendee(event_name, attendee_name):
    attendee = models.Attendee.get_or_insert(
        event_name + '=' + attendee_name,
        name=attendee_name,
        event_name=event_name,
    )
    attendee.put()


@app.route('/', methods=('GET',))
def home():
    return flask.render_template(
        'events.html',
        events=models.Event.query().order(-models.Event.date).fetch(),
    )


@app.route('/upload/', methods=('GET', 'POST'))
@login.login_required
@login.company_login_required
@login.admin_required
def upload():
    form = EventUploadForm()
    if form.validate_on_submit():
        filename = secure_filename(form.names_csv.data.filename)
        whole_file = form.names_csv.data.stream.read()
        if '\r' in whole_file:
            names = [name for name in whole_file.split('\r\n') if name]
        else:
            names = [name for name in whole_file.split('\n') if name]

        event = upsert_event(form.event_name.data)
        for name in names:
            upsert_attendee(
                event.slug,
                name,
            )
    else:
        filename = None
    return flask.render_template(
        'upload.html',
        form=form,
        filename=filename,
    )

@app.route('/event/<event_slug>/', methods=('GET', ))
@login.login_required
@login.company_login_required
def event_page(event_slug):
    attendees = models.Attendee.query(models.Attendee.event_name==event_slug).order(models.Attendee.name).fetch()
    total_attendees = len(attendees)
    checked_attendees = sum(attendee.is_checked for attendee in attendees)
    return flask.render_template(
        'event.html',
        toggle_form=ToggleForm(),
        event_slug=event_slug,
        attendees=attendees,
        total_attendees=total_attendees,
        checked_attendees=checked_attendees,
    )

@app.route('/event/toggle_attendance/', methods=('POST', ))
def toggle_attendance():
    form = ToggleForm()
    if form.validate_on_submit():
        attendees = models.Attendee.query(
            models.Attendee.event_name == form.event.data,
            models.Attendee.name == form.attendee_name.data,
        ).fetch()
        attendee = attendees[0]
        attendee.is_checked = form.is_checked.data
        attendee.put()
    else:
        print form.errors
    return flask.redirect('event/%s' % form.event.data)


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def page_not_found(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500

app.secret_key = 'Change me.'
