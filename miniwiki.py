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
def check_Profanity(text_to_check):
    connection = urllib.urlopen("http://www.wdyl.com/profanity?q="+text_to_check)
    output = connection.read()
    connection.close()
    if "true" in output:
        return True
    if "false" in output:
        return False


def subject_Key(subject_Name):
 #   Constructs a Datastore key for a Subject entity. I use subject_Name as the key.
      return ndb.Key('Subject', subject_Name)

def topic_Key(topic_Name):
 #   Constructs a Datastore key for a Topic entity. I use topic_Name as the key.
      return ndb.Key('Topic', topic_Name)

def post_Key(subject_Name):
#    Constructs the Datastore key for a Post entity. I use the subject_Name as the key kind.
      return ndb.Key('Post', subject_Name)

class Subject(ndb.Model):
# model for representing a subject i.e. Python, CSS, etc.
    subject_Name = ndb.StringProperty(indexed=True)

class Topic(ndb.Model):
# model for a topic within a particular subject i.e. Subject: Python ; Topic: For Loops
    subject_Name = ndb.StringProperty(indexed=True)
    topic_Name = ndb.StringProperty(indexed=False)

class Contributor(ndb.Model):
#  sub-model for representing a contributor.
    contributor_Id = ndb.StringProperty(indexed=False)
    contributor_Name = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)

class Post(ndb.Model):
#   A main model for representing a contributor's post entry.
    contributor = ndb.StructuredProperty(Contributor)
    subject_Name = ndb.StringProperty(indexed=True)
    topic_Name = ndb.StringProperty(indexed=True)        
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
def topic_List(subject):
        topic_List = []
        sub_topics = Topic.query()        
        for t in sub_topics:
            if t.subject_Name == subject:
                topic_List.append(t.topic_Name)
        return topic_List
# This function puts together a list of subjects that have been entered
def subject_list():
    subject_List = []
    subjects = Subject.query()
    for s in subjects:
        subject_List.append(s.subject_Name)
    # If the subject list is empty then put the default subject in
    if subject_List == []:
        subject_List = [DEFAULT_SUBJECT]
        post_Subject(DEFAULT_SUBJECT)
    return subject_List

# This function posts the Topic entity
def post_Topic(subject,topic):
    post = Topic(parent = topic_Key(topic))    
    post.subject_Name = subject
    post.topic_Name = topic
    post.put()
# This function posts the Subject entity
def post_Subject(subject):
    post = Subject(parent = subject_Key(subject))
    post.subject_Name = subject
    post.put()

# This function checks to see if the new subject entered is a duplicate of one already entered
def duplicate_Subject(subject):
    subjects = Subject.query(ancestor = subject_Key(subject))
    for s in subjects:
        if s.subject_Name.lower() == subject.lower():
            return True
    return False

# This function checks to see if the new topic entered is a duplicate of one already entered
def duplicate_Topic(subject,topic):
    sub_topics = Topic.query(Topic.subject_Name == subject)
    for t in sub_topics:
        if t.subject_Name.lower() == subject.lower():
            if t.topic_Name.lower() == topic.lower():
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
        new_Subject = self.request.get('new_Subject')

        # Set up the argumwents to pass to the topic page
        arguments = {'subject': subject, 'alert':"",'topic':DEFAULT_TOPIC,'subjects':subject_list()}
        

        # Check if the subject is new or not
        if new_Subject != "":      

            # If the subject is new then check to see if there is profanity or it is a duplicate      
            if check_Profanity(new_Subject) == True: 
                arguments['alert'] = "Profanity Alert! - enter again"
                self.render("main_page.html", **arguments)
            else:                               
                if duplicate_Subject(new_Subject): 
                    arguments['alert'] = "Duplicate Subject! - enter again"            
                    self.render("main_page.html", **arguments)           
                else:
                    # If the subject has passed the two checks above then we set up the arguments and lists to pass to the topics page       
                    post_Subject(new_Subject)                                       
                    subject = new_Subject
                    arguments['subject'] = new_Subject 
                    new_Subject = ""    # Set new_Subject to "" to allow the next section of code to process and then render the topics page                   
                    
        if new_Subject == "": 
            # finish the arguments needed to render the topics page         
            topic_List = topic_List(subject)
            if topic_List == []: 
                topic_List = [DEFAULT_TOPIC]
                post_Topic(subject,DEFAULT_TOPIC)                
            arguments['topics'] = topic_List 

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
            arguments['contributor_Name'] = contributor
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

        topic_List = topic_List(subject) #  Put together the list of saved topics for this subject   
        arguments ['topics'] = topic_List    
        arguments['alert'] = "" #  Used if a duplicate entry or profanity is entered in the new topic field
        new_Topic = self.request.get('new_Topic')

        #  Check to see if there is an entry for a new sub topic
        if new_Topic != "":
            #  Since we have a new sub-topic we need to check to make sure there is no profanity
            if check_Profanity(new_Topic):
                # The new sub-topic entry had profanity in it. Back to the user for another try...
                arguments['alert'] = "Profanity Alert! - enter again"
                self.render("topic_page.html", **arguments)
            else:
                #  Since there is no profanity we need to make sure it is not a duplicate
                if duplicate_Topic(subject, new_Topic):                
                    arguments ['alert'] = "Duplicate Topic Entry"
                    self.render("topic_page.html", **arguments)
            
                else:            
                #  Now lets post the topic to the Datastore and add it to our list to render
                    post_Topic(subject,new_Topic)                    
                    topic_List.append(new_Topic)
                    arguments ['topic'] = new_Topic
                    topic = new_Topic
                    arguments ['topics'] = topic_List #  This is the the topic list including the current new topic
                    new_Topic = ""

        if new_Topic == "":           

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
            arguments['contributor_Name'] = contributor
            arguments['url'] = url
            arguments['url_linktext'] = url_linktext
            
            # Write Out Content Page

            posts_query = Post.query(ancestor = post_Key(subject)).order(-Post.date)            
            postsubject_List = posts_query.filter(Post.subject_Name == subject, Post.topic_Name == topic)            
            arguments['posts'] = postsubject_List
          
            self.render("content_page.html", **arguments)

class Content(Handler):
   def post(self):
        # get the parameters fromt he content page and the post the content
        # then redirect back to the main page
        subject = self.request.get('subject')
        topic = self.request.get('topic')
    
        post = Post(parent = post_Key(subject))

        post.subject_Name = subject
        post.topic_Name = topic

        if users.get_current_user():
            #post.contributor_Id = users.get_current_user().user_id() 
            post.contributor = Contributor(
                    contributor_Id = users.get_current_user().user_id(),
                    contributor_Name = users.get_current_user().nickname(),
                    email = users.get_current_user().email())

       
        content = self.request.get('content')

        # Check to see if the content contains profanity. 
        # If it does then send the message back to user and render the content page again
        if check_Profanity(content):
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


        

app = webapp2.WSGIApplication([('/', MainPage),('/set_subject', Main_Subject), 
    ('/set_topic', Sub_Topic), ('/post_content', Content)], debug=True)
