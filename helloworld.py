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
   revisions= db.ListProperty(db.Key)

class Revision(db.Model):
   content  = db.TextProperty()
   date     = db.DateTimeProperty(auto_now_add=True)

def searchTrack(search_query):
   result_artist = Track.all().filter('artist =', search_query).fetch(5)
   result_title  = Track.all().filter('title  =', search_query).fetch(5)
   search_result = list(itertools.chain(result_artist,result_title))
   if len(search_result)==0:
      search_result = None
   return search_result

#=====================================================================================

class MainPage(webapp2.RequestHandler):
   def get(self):
      guestbook_name=self.request.get('guestbook_name')
      greetings_query = Greeting.all().ancestor(
         guestbook_key(guestbook_name)).order('-date')
      greetings = greetings_query.fetch(10)

      search_query = self.request.get('search_query')
      search_result = searchTrack(search_query)

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


class TrackPage(webapp2.RequestHandler):
   def get(self):

      # TODO: foolproof str-to-key conversion from naked URL
      track_key = db.Key(self.request.get('key'))
      track = Track.all().filter('__key__ = ', track_key).get()

      #rev_keys = [db.Key(k) for k in track.revisions]
      list_revision = list(Revision.all().filter('__key__ IN', track.revisions).run(limit=10))

      for rev in list_revision:
         for line in rev.content:
            logging.info(line)

      template_values = {
         'track': track,
         'list_revision': list_revision
      }

      template = jinja_environment.get_template('track.html')
      self.response.out.write(template.render(template_values))



class Guestbook(webapp2.RequestHandler):
   def post(self):

      # TODO: Data validation
      
      val = self.request.get('revision')
      
      l = val.splitlines(True)

      list_header = ('artist', 'title')

      new_artist = None
      new_title = None

      iterable = iter(l)
      for line in iterable:
         if line.startswith('artist'):
            new_artist = line.split()[1]
         elif line.startswith('title'):
            new_title = line.split()[1]
         else:
            break
      
      revision = Revision()
      revision.content = "".join(list(iterable))
      revision.put()

      logging.info(revision.key())

      ts = Track.all()
      ts.filter('artist =', new_artist)
      ts.filter('title = ', new_title)
      
      # If not existed, create a new Track for it
      if not ts.get():
         logging.info('Track not existed. Creating new track')
         track = Track()
         track.artist = new_artist
         track.title = new_title
      else:
         logging.info('Track existed. Appending revision.')
         track = ts.get()
      track.revisions.append(revision.key())
      track.put()


      self.redirect('/')

    # We set the same parent key on the 'Greeting' to ensure each greeting is in
    # the same entity group. Queries across the single entity group will be
    # consistent. However, the write rate to a single entity group should
    # be limited to ~1/second.
    # guestbook_name = self.request.get('guestbook_name')
    # greeting = Greeting(parent=guestbook_key(guestbook_name))

    # if users.get_current_user():
    #   greeting.author = users.get_current_user().nickname()

    # greeting.content = self.request.get('content')
    # greeting.put()
      # self.redirect('/?' + urllib.urlencode({'guestbook_name': guestbook_name}))


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/sign', Guestbook),
                               ('/track', TrackPage)],
                              debug=True)