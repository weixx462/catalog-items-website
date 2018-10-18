# catalog-items-website

# Project description
An application that provides a list of items within a variety of categories as well as provide a user registration and authentication system (through Google OAuth API). Registered users will have the ability to post, edit and delete their own items.

# Prerequisites & Set up

You'll need vagrant VM to run the web application and a Google account to log into the website.

This project makes use of the same Linux-based virtual machine (VM) as the preceding lessons in Udacity Full Stack Nanodegree.

If you need to bring the virtual machine back online (with vagrant up), do so now. Then log into it with vagrant ssh.

Clone the catalog-items-website repo into vagrant folder so it could be synced with VM folder.

To setup sqlite database for the website, run "python database_setup.py". To initialize the database with default items, run "python lotsofitems.py".

# Usage

To spin up the web server, run "python project.py". A localhost server will be up and running listening to port 8000.

The application provides a JSON endpoint: http://localhost:8000/catalog.json

To retrieve arbitrary catalog: http://localhost:8000/catalog/<int:catalog_id>/items/JSON

To retrieve arbitrary item: http://localhost:8000/catalog/<int:catalog_id>/items/<int:item_id>/JSON

To access homepage: http://localhost:8000/ or http://localhost:8000/catalog

Selecting a specific category shows you all the items available for that category.

Selecting a specific item shows you specific information of that item.

You need a Google account to log in. After logging in, you have the ability to add, update, or delete item info.
