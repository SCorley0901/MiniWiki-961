import os
import urllib
import webapp2
import jinja2

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)



DEFAULT_SUBJECT = 'Python'
DEFAULT_TOPIC = 'General'

# This function uses the Google website that detects profanity in a string
def check_profanity(text_to_check):
    connection = urllib.urlopen("http://www.wdyl.com/profanity?q="+text_to_check)
    output = connection.read()
    connection.close()
    if "true" in output:
        return True
    if "false" in output:
        return False


def subject_key(subject_name):
 #   Constructs a Datastore key for a Subject entity. I use subject_name as the key.
      return ndb.Key('Subject', subject_name)

def topic_key(topic_name):
 #   Constructs a Datastore key for a Topic entity. I use topic_name as the key.
      return ndb.Key('Topic', topic_name)

def post_key(subject_name):
#    Constructs the Datastore key for a Post entity. I use the subject_name as the key kind.
      return ndb.Key('Post', subject_name)

class Subject(ndb.Model):
# model for representing a subject i.e. Python, CSS, etc.
    subject_name = ndb.StringProperty(indexed=True)

class Topic(ndb.Model):
# model for a topic within a particular subject i.e. Subject: Python ; Topic: For Loops
    subject_name = ndb.StringProperty(indexed=True)
    topic_name = ndb.StringProperty(indexed=False)

class Contributor(ndb.Model):
#  sub-model for representing a contributor.
    contributor_id = ndb.StringProperty(indexed=False)
    contributor_name = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)

class Post(ndb.Model):
#   A main model for representing a contributor's post entry.
    contributor = ndb.StructuredProperty(Contributor)
    subject_name = ndb.StringProperty(indexed=True)
    topic_name = ndb.StringProperty(indexed=True)        
    content = ndb.StringProperty(indexed=False)
    link = ndb.StringProperty(indexed=False)    
    date = ndb.DateTimeProperty(auto_now_add=True)


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(**params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

# This function puts together a list of topics entered under a particular subject
def topic_list(subject):
        t2 = []
        sub_topics = Topic.query()        
        for t in sub_topics:
            if t.subject_name == subject:
                t2.append(t.topic_name)
        return t2
# This function puts together a list of subjects that have been entered
def subject_list():
    s2 = []
    subjects = Subject.query()
    for s in subjects:
        s2.append(s.subject_name)
    # If the subject list is empty then put the default subject in
    if s2 == []:
        s2 = [DEFAULT_SUBJECT]
        post_Subject(DEFAULT_SUBJECT)
    return s2

# This function posts the Topic entity
def post_Topic(subject,topic):
    post = Topic(parent = topic_key(topic))    
    post.subject_name = subject
    post.topic_name = topic
    post.put()
# This function posts the Subject entity
def post_Subject(subject):
    post = Subject(parent = subject_key(subject))
    post.subject_name = subject
    post.put()

# This function checks to see if the new subject entered is a duplicate of one already entered
def duplicate_subject(subject):
    subjects = Subject.query(ancestor = subject_key(subject))
    for s in subjects:
        if s.subject_name.lower() == subject.lower():
            return True
    return False

# This function checks to see if the new topic entered is a duplicate of one already entered
def duplicate_topic(subject,topic):
    sub_topics = Topic.query(Topic.subject_name == subject)
    for t in sub_topics:
        if t.subject_name.lower() == subject.lower():
            if t.topic_name.lower() == topic.lower():
                return True
    return False


class MainPage(Handler):
    def get(self):
        # Set up the argumets that will be passed to the main page
        arguments = {}        
        arguments['subjects'] = subject_list()
        self.render("main_page.html", **arguments)

class Main_Subject(Handler): # The handler for the main page - determine if the subject is new or not and set up the topic page  
    def get(self):
        subject = self.request.get('subject', DEFAULT_SUBJECT)
        new_subject = self.request.get('new_subject')

        # Set up the argumwents to pass to the topic page
        arguments = {'subject': subject}
        arguments['alert'] = ""                
        arguments['topic'] = DEFAULT_TOPIC
        arguments['subjects'] = subject_list()

        # Check if the subject is new or not
        if new_subject != "":      

            # If the subject is new then check to see if there is profanity or it is a duplicate      
            if check_profanity(new_subject) == True: 
                arguments['alert'] = "Profanity Alert! - enter again"
                self.render("main_page.html", **arguments)
            else:                               
                if duplicate_subject(new_subject): 
                    arguments['alert'] = "Duplicate Subject! - enter again"            
                    self.render("main_page.html", **arguments)           
                else:
                    # If the subject has passed the two checks above then we set up the arguments and lists to pass to the topics page       
                    post_Subject(new_subject)                                       
                    subject = new_subject
                    arguments['subject'] = new_subject 
                    new_subject = ""    # Set new_subject to "" to allow the next section of code to process and then render the topics page                   
                    
        if new_subject == "": 
            # finish the arguments needed to render the topics page         
            t2 = topic_list(subject)
            if t2 == []: 
                t2 = [DEFAULT_TOPIC]
                post_Topic(subject,DEFAULT_TOPIC)                
            arguments['topics'] = t2 

            # Add to an arguments dictionary to pass onto the jinja2 templates.
            # These are the arguments that pertain to the contributor
            contributor = users.get_current_user()
            if contributor:
                url = users.create_logout_url(self.request.uri)
                url_linktext = 'Logout'
            else:
                contributor = 'Anonymous Poster'
                url = users.create_login_url(self.request.uri)
                url_linktext = 'Login'
            arguments['contributor_name'] = contributor
            arguments['url'] = url
            arguments['url_linktext'] = url_linktext
            self.render("topic_page.html", **arguments)

class Sub_Topic(Handler):
    def get(self):
        # This handler get the parameters from the main page (subject selection) and then allows the user to pick a topic
        subject = self.request.get('subject')
        arguments = {'subject':subject}
        topic = self.request.get('topic')
        arguments['topic'] = topic

        t2 = topic_list(subject) #  Put together the list of saved topics for this subject   
        arguments ['topics'] = t2    
        arguments['alert'] = "" #  Used if a duplicate entry or profanity is entered in the new topic field
        new_topic = self.request.get('new_topic')

        #  Check to see if there is an entry for a new sub topic
        if new_topic != "":
            #  Since we have a new sub-topic we need to check to make sure there is no profanity
            if check_profanity(new_topic):
                # The new sub-topic entry had profanity in it. Back to the user for another try...
                arguments['alert'] = "Profanity Alert! - enter again"
                self.render("topic_page.html", **arguments)
            else:
                #  Since there is no profanity we need to make sure it is not a duplicate
                if duplicate_topic(subject, new_topic):                
                    arguments ['alert'] = "Duplicate Topic Entry"
                    self.render("topic_page.html", **arguments)
            
                else:            
                #  Now lets post the topic to the Datastore and add it to our list to render
                    post_Topic(subject,new_topic)                    
                    t2.append(new_topic)
                    arguments ['topic'] = new_topic
                    topic = new_topic
                    arguments ['topics'] = t2 #  This is the the topic list including the current new topic
                    new_topic = ""

        if new_topic == "":           

            # If a user(contributor) is logged in to Google's Services
            contributor = users.get_current_user()
            if contributor:
                url = users.create_logout_url(self.request.uri)
                url_linktext = 'Logout'
            else:
                contributor = 'Anonymous Poster'
                url = users.create_login_url(self.request.uri)
                url_linktext = 'Login'

            # Other needed arguments for the template
            arguments['contributor_name'] = contributor
            arguments['url'] = url
            arguments['url_linktext'] = url_linktext
            
            # Write Out Content Page

            posts_query = Post.query(ancestor = post_key(subject)).order(-Post.date)            
            posts2 = posts_query.filter(Post.subject_name == subject, Post.topic_name == topic)            
            arguments['posts'] = posts2
          
            self.render("content_page.html", **arguments)

class Content(Handler):
   def post(self):
        # get the parameters fromt he content page and the post the content
        # then redirect back to the main page
        subject = self.request.get('subject')
        topic = self.request.get('topic')
    
        post = Post(parent = post_key(subject))

        post.subject_name = subject
        post.topic_name = topic

        if users.get_current_user():
            #post.contributor_id = users.get_current_user().user_id() 
            post.contributor = Contributor(
                    contributor_id = users.get_current_user().user_id(),
                    contributor_name = users.get_current_user().nickname(),
                    email = users.get_current_user().email())

       
        content = self.request.get('content')

        # Check to see if the content contains profanity. 
        # If it does then send the message back to user and render the content page again
        if check_profanity(content):
            arguments = {'alert': 'The content contains profanity - please re-enter'}
            arguments['content'] = content
            arguments['subject'] = subject
            arguments['topic'] = topic
            self.render("content_page.html", **arguments)
        else:
        
            if type(content) != unicode:
                post.content = unicode(self.request.get('content'),'utf-8')
            else:
                post.content = self.request.get('content')

            if content != "":
                post.put()

            # Redirect the site
            arguments = {'Subject': subject}
            self.redirect('/?' + urllib.urlencode(arguments))


        

app = webapp2.WSGIApplication([('/', MainPage),('/set_subject', Main_Subject), ('/set_topic', Sub_Topic), ('/post_content', Content)], debug=True)