import cgi, datetime, urllib, webapp2
import jinja2, os
import itertools,logging

from google.appengine.ext import db
from google.appengine.api import users


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class Greeting(db.Model):
  """Models an individual Guestbook entry with an author, content, and date."""
  author = db.StringProperty()
  content = db.StringProperty(multiline=True)
  date = db.DateTimeProperty(auto_now_add=True)


def guestbook_key(guestbook_name=None):
  """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
  return db.Key.from_path('Guestbook', guestbook_name or 'default_guestbook')

class Track(db.Model):
   artist   = db.StringProperty()
   title    = db.StringProperty()


#=====================================================================================

class MainPage(webapp2.RequestHandler):
   def get(self):
      guestbook_name=self.request.get('guestbook_name')
      greetings_query = Greeting.all().ancestor(
         guestbook_key(guestbook_name)).order('-date')
      greetings = greetings_query.fetch(10)

      search_query = self.request.get('search_query')
      result_artist = Track.all().filter('artist =', search_query).fetch(5)
      result_title  = Track.all().filter('title  =', search_query).fetch(5)
      search_result = list(itertools.chain(result_artist,result_title))
      if len(search_result)==0:
         search_result = None

      logging.info("search_query: %s" % search_query)
      logging.info("result_artist: %s" % result_artist)
      logging.info("result_title: %s" % result_title)

      if users.get_current_user():
         url = users.create_logout_url(self.request.uri)
         url_linktext = 'Logout'
      else:
         url = users.create_login_url(self.request.uri)
         url_linktext = 'Login'

      template_values = {
         'search_result': search_result,
         'greetings': greetings,
         'url': url,
         'url_linktext': url_linktext,
         'guestbook_name': cgi.escape(guestbook_name),
      }

      template = jinja_environment.get_template('index.html')
      self.response.out.write(template.render(template_values))


class Guestbook(webapp2.RequestHandler):
  def post(self):
    # We set the same parent key on the 'Greeting' to ensure each greeting is in
    # the same entity group. Queries across the single entity group will be
    # consistent. However, the write rate to a single entity group should
    # be limited to ~1/second.
    guestbook_name = self.request.get('guestbook_name')
    greeting = Greeting(parent=guestbook_key(guestbook_name))

    if users.get_current_user():
      greeting.author = users.get_current_user().nickname()

    greeting.content = self.request.get('content')
    greeting.put()
    self.redirect('/?' + urllib.urlencode({'guestbook_name': guestbook_name}))


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/sign', Guestbook)],
                              debug=True)