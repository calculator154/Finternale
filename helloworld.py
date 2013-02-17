import cgi, datetime, urllib, webapp2
import jinja2, os
import itertools,logging

from google.appengine.ext import db
from google.appengine.api import users

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class Track(db.Model):
   title    = db.StringProperty(required=True)
   artist   = db.StringProperty(required=True)
   album    = db.StringProperty()
   year     = db.IntegerProperty()
   revisions= db.ListProperty(db.Key)

   # def __repr__(self):
   def addRevision(self,rev):
      self.revisions.append(rev.key())



class Revision(db.Model):
   content  = db.TextProperty(required=True)
   date     = db.DateTimeProperty(auto_now_add=True)

def searchTrack(search_query):
   result_artist = Track.all().filter('artist =', search_query).fetch(5)
   result_title  = Track.all().filter('title  =', search_query).fetch(5)
   search_result = list(itertools.chain(result_artist,result_title))
   if len(search_result)==0:
      search_result = None
   return search_result

def TRparser(content):
   """ Parse the raw content in text file into (track,revision) pair """
   lines = iter(content.splitlines(True))
   
   new_title   = None
   new_artist  = None
   new_album   = None

   # TODO: Support Thai
   for line in lines:
      if line.startswith('title'):
         new_title = line.split()[1]
      elif line.startswith('artist'):
         new_artist = line.split()[1]
      elif line.startswith('album'):
         new_album = line.split()[1]
      else:
         break
   
   # assert: must have title/artist/rev

   revision_content = "".join(list(lines))

   revision = Revision(content=revision_content)
   track = Track(title=new_title, artist=new_artist)

   return (track,revision)


def fetchTrack(track):
   """ For a track that existed already, fetch it up."""
   ts = Track.all()
   ts.filter('title = ', track.title)
   ts.filter('artist =', track.artist)
   return ts.get()


def isTrackExisted(track):
   """ Boolean: return true if given track already existed """
   return fetchTrack(track) is not None


#=====================================================================================

class MainPage(webapp2.RequestHandler):
   def get(self):
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
         'url': url,
         'url_linktext': url_linktext,
      }

      template = jinja_environment.get_template('index.html')
      self.response.out.write(template.render(template_values))


class TrackPage(webapp2.RequestHandler):
   def get(self):

      # TODO: foolproof str-to-key conversion from naked URL
      track_key = db.Key(self.request.get('key'))
      track = Track.all().filter('__key__ = ', track_key).get()

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

      new_artist = None
      new_title = None

      # Support Thai
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

class Upload(webapp2.RequestHandler):
   def post(self):
      file = unicode(self.request.get('file'),'utf-8')

      # file = self.request.get('file')
      # file = self.request.POST.get("file",None)
      # logging.info(file.value)
      # logging.info(file.value)
      # logging.info(file)

      t,r = TRparser(file)
      r.put()

      logging.info(isTrackExisted(t))


      if isTrackExisted(t):
         track = fetchTrack(t)
         track.addRevision(r)
         track.put()
      else:
         t.addRevision(r)
         t.put()

      self.redirect('/')

      # logging.info(t)
      # logging.info(r)

      # entity = DatastoreFile(data=file.value, mimetype=file.type)
      # entity.put()
      # file_url = "http://%s/%d/%s" % (self.request.host, entity.key().id(), file.name)
      # self.response.out.write("Your uploaded file is now available at %s" % (file_url,))

      # self.redirect('/')


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/sign', Guestbook),
                               ('/upload', Upload),
                               ('/track', TrackPage)],
                              debug=True)