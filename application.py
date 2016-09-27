import newrelic.agent
newrelic.agent.initialize('newrelic.ini', 'staging')

from flask import Flask, url_for, render_template, request, redirect, escape
import os
import enchant
import csv
from collections import Counter
from firebase import firebase
from flask.ext.mobility import Mobility
import urllib


# EB looks for an 'application' callable by default.
application = Flask(__name__)
Mobility(application)

# Determines the destination of the build. Only usefull if you're using Frozen-Flask
application.config['FREEZER_DESTINATION'] = os.path.dirname(os.path.abspath(__file__))+'/../build'

# Function to easily find your assets
# In your template use <link rel=stylesheet href="{{ static('filename') }}">
application.jinja_env.globals['static'] = (
                                            lambda filename: url_for('static', filename = filename)
                                            )

firebase = firebase.FirebaseApplication('https://slsearch.firebaseio.com', None)

opener = urllib.URLopener()
myurl = "https://s3.amazonaws.com/bulinksearch/URLsWithDomains.csv"

spellcheck = enchant.Dict("en_US")
mydict = {}

myfile = opener.open(myurl)
reader = csv.reader(myfile)
mydict = {rows[1].lower():rows[0] for rows in reader}

def searchDict(searchFor):
    results = [(k, v) for (k, v) in mydict.iteritems() if searchFor in k]
    if len(results) is 1:
        return results
    else:
        return results

def popular():
    elements = []
    try:
        r = firebase.get('/searches', None)
        return Counter(r.values()).most_common(5)
    except:
        return elements

@application.route('/')
def index():
    pop = popular()
    if request.MOBILE:
        return render_template('index.html', foundLink=False, popSearches=pop)
    return render_template('index.html', foundLink="http://www.bu.edu/link/bin/uiscgi_studentlink.pl", popSearches=pop)

@application.route('/', methods=['POST'])
def search():
    userSearch = request.form['searchtext'].lower()
    isMobile = request.MOBILE
    #tracker
    try:
        firebase.post('/searches', escape(userSearch))
    except:
        pass
    if not spellcheck.check(userSearch) and not 'fitrec':
        wordSuggestions = spellcheck.suggest(userSearch)
        if wordSuggestions:
            for word in wordSuggestions:
                wrodSearch = searchDict(word)
                if wrodSearch:
                    userSearch = word
                    break

    links = searchDict(userSearch)

    #print links
    pop = popular()
    if len(links) == 0:
        try:
            firebase.post('/noresults', {escape(userSearch): len(links)})
        except:
            pass
        return render_template('index.html', foundLink=(404), popSearches=pop)
    elif len(links) == 1:
        if request.MOBILE:
            return redirect(links[0][1])
        return render_template('index.html', foundLink=links[0][1], popSearches=pop)
    else:
        if isMobile:
            return render_template('index.html', links=links, foundLink=False, popSearches=pop)
        return render_template('index.html', links=links, foundLink="http://www.bu.edu/link/bin/uiscgi_studentlink.pl", popSearches=pop)
# run the app.
if __name__ == "__main__":
    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.
    application.debug = False
    application.run(host='0.0.0.0')
