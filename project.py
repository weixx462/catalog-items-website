from flask import Flask, render_template, request, \
        redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import SingletonThreadPool
from database_setup import Base, Catalog, CatalogItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Item App"


# Connect to Database and create database session
engine = create_engine('sqlite:///catalogitemswithusers.db',
                       poolclass=SingletonThreadPool)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?' \
        + 'grant_type=fb_exchange_token&client_id=%s&client_'  \
        + 'secret=%s&fb_exchange_token=%s' % (
           app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the
        server token exchange we have to
        split the token first on commas and select
        the first index which gives us the key : value
        for the server access token then we split it on
        colons to pull out the actual token value
        and replace the remaining quotes with nothing so
        that it can be used directly in the graph
        api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,'\
        + 'id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?' \
        + 'access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/'
    + 'permissions?access_token=%s' % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: ' \
        + '150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Catalog Information
@app.route('/catalog.json')
def catalogItemsJSON():
    catalog = session.query(Catalog).all()
    Category = []
    for c in catalog:
        rawCatalogItems = session.query(
            CatalogItem).filter_by(catalog_id=c.id).all()
        catalogItems = [r.serialize for r in rawCatalogItems]
        if not catalogItems:
            Category.append(c.serialize.copy())
        else:
            tempCategory = c.serialize.copy()
            tempCategory.update({'Item': catalogItems})
            Category.append(tempCategory.copy())

    return jsonify(Category=Category)


@app.route('/catalog/<int:catalog_id>/items/JSON')
def catalogJSON(catalog_id):
    items = session.query(CatalogItem).filter_by(
        catalog_id=catalog_id).all()
    return jsonify(Items=[i.serialize for i in items])


@app.route('/catalog/<int:catalog_id>/items/<int:item_id>/JSON')
def itemJSON(catalog_id, item_id):
    item = session.query(CatalogItem).filter_by(id=item_id).one()
    return jsonify(Item=item.serialize)


# Show all catalogs
@app.route('/')
@app.route('/catalog')
def showCatalog():
    catalogs = session.query(Catalog).order_by(asc(Catalog.name))
    catalogItems = session.query(
        CatalogItem).order_by(desc(CatalogItem.id)).limit(10)
    if 'username' not in login_session:
        return render_template(
            'publiccatalog.html', catalogs=catalogs, catalogItems=catalogItems)
    else:
        return render_template(
            'catalog.html', catalogs=catalogs, catalogItems=catalogItems)


# Create a new item

@app.route('/catalog/new/', methods=['GET', 'POST'])
def newCatalog():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        catalog = session.query(
            Catalog).filter_by(id=request.form['catalog']).one()
        catalogItem = CatalogItem(user_id=login_session['user_id'],
                                  name=request.form['name'],
                                  description=request.form['description'],
                                  catalog=catalog)
        session.add(catalogItem)
        flash('New Item %s Successfully Created' % catalogItem.name)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        catalogs = session.query(Catalog).order_by(asc(Catalog.name))
        return render_template('newCatalog.html', catalogs=catalogs)

# Show items for a catalog


@app.route('/catalog/<catalog_name>/')
@app.route('/catalog/<catalog_name>/items/')
def showItem(catalog_name):
    catalogs = session.query(Catalog).order_by(asc(Catalog.name))
    catalog_id = session.query(Catalog).filter_by(name=catalog_name).one().id
    items = session.query(CatalogItem).filter_by(catalog_id=catalog_id).all()
    if 'username' not in login_session:
        return render_template(
            'publicitems.html',
            catalogs=catalogs, items=items,
            catalog_name=catalog_name, item_number=len(items))
    else:
        return render_template('items.html',
                               catalogs=catalogs, items=items,
                               catalog_name=catalog_name,
                               item_number=len(items))

# Show details for an item


@app.route('/catalog/<catalog_name>/<item_name>')
def showItemDetails(catalog_name, item_name):
    catalog_id = session.query(Catalog).filter_by(name=catalog_name).one().id
    item = session.query(
                   CatalogItem).filter_by(
                   catalog_id=catalog_id).filter_by(name=item_name).one()
    if 'username' not in login_session:
        return render_template(
            'itemdetails.html',
            item_name=item_name, item_description=item.description)
    else:
        return render_template(
            'privateitemdetails.html',
            item_name=item_name, item_description=item.description,
            catalog_name=catalog_name)

# Edit an item


@app.route('/catalog/<catalog_name>/<item_name>/edit', methods=['GET', 'POST'])
def editItem(catalog_name, item_name):
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    editedItem = session.query(
            CatalogItem).filter_by(
            catalog_id=catalog.id).filter_by(name=item_name).one()
    if login_session['user_id'] != editedItem.user_id:
        return "<script>function myFunction() {alert('You are not\
    authorized to edit items to this catalog. It belongs to others');}\
    </script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['catalog']:
            catalogAfterEdit = session.query(
                Catalog).filter_by(id=request.form['catalog']).one()
            editedItem.catalog = catalogAfterEdit
        session.add(editedItem)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(url_for('showItem', catalog_name=catalog_name))
    else:
        catalogs = session.query(Catalog).order_by(asc(Catalog.name))
        return render_template(
            'edititem.html', catalogs=catalogs,
            item_catalog=editedItem.catalog.name,
            item_name=editedItem.name, item_description=editedItem.description)


# Delete a item


@app.route('/catalog/<catalog_name>/<item_name>/delete',
           methods=['GET', 'POST'])
def deleteItem(catalog_name, item_name):
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    itemToDelete = session.query(
            CatalogItem).filter_by(
            catalog_id=catalog.id).filter_by(name=item_name).one()
    if login_session['user_id'] != itemToDelete.user_id:
        return "<script>function myFunction() {alert('You are not\
    authorized to delete items to this catalog. It belongs to others');}\
    </script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Catalog Item Successfully Deleted')
        return redirect(url_for('showItem', catalog_name=catalog_name))
    else:
        return render_template('deleteItem.html', item=itemToDelete)

# Disconnect based on provider


@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCatalog'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
