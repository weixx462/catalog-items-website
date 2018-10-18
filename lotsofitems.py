from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Catalog, Base, CatalogItem, User

engine = create_engine('sqlite:///catalogitemswithusers.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Jinchuan Wei", email="weixx462@umn.edu",
             picture='https://pbs.twimg.com/profile_images\
             /2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()

# Catalog for Soccer
catalog1 = Catalog(name="Soccer")

session.add(catalog1)
session.commit()

catalogItem11 = CatalogItem(user_id=1, name="Like new soccer",
                            description="a used like new soccer, $50",
                            catalog=catalog1)

session.add(catalogItem11)
session.commit()

catalogItem12 = CatalogItem(user_id=1, name="2008 used soccer",
                            description="a used 2008 soccer $10",
                            catalog=catalog1)

session.add(catalogItem12)
session.commit()

catalogItem13 = CatalogItem(user_id=1,
                            name="FIFA limited edition soccer",
                            description="2008 limited edition soccer",
                            catalog=catalog1)

session.add(catalogItem13)
session.commit()

# Catalog for Basketball
catalog2 = Catalog(name="Basketball")

session.add(catalog2)
session.commit()

catalogItem21 = CatalogItem(user_id=1,
                            name="New Basketball",
                            description="a brand new Basketball, $100",
                            catalog=catalog2)

session.add(catalogItem21)
session.commit()

# Catalog for Baseball
catalog3 = Catalog(name="Baseball")

session.add(catalog3)
session.commit()

catalogItem31 = CatalogItem(user_id=1, name="Like new Baseball",
                            description="a used like new soccer, $50",
                            catalog=catalog3)

session.add(catalogItem31)
session.commit()

# Catalog for Frisbee
catalog4 = Catalog(name="Frisbee")

session.add(catalog4)
session.commit()

catalogItem41 = CatalogItem(user_id=1, name="used Frisbee",
                            description="a used Frisbee price negotiable",
                            catalog=catalog4)

session.add(catalogItem41)
session.commit()

# Catalog for Snowboarding
catalog5 = Catalog(name="Snowboarding")

session.add(catalog5)
session.commit()

catalogItem51 = CatalogItem(user_id=1, name="like new snowboard",
                            description="used a couple of times,\
                            bought $600, ask for $400",
                            catalog=catalog5)

session.add(catalogItem51)
session.commit()

# Catalog for Rock climbing
catalog6 = Catalog(name="Rock Climbing")

session.add(catalog6)
session.commit()

catalogItem61 = CatalogItem(user_id=2, name="new harness for men2",
                            description="new rock climbing\
                            harness for men, $70",
                            catalog=catalog6)

catalogItem62 = CatalogItem(user_id=2, name="new harness for men22",
                            description="new rock climbing\
                            harness for men, $70",
                            catalog=catalog6)

session.add(catalogItem61)
session.add(catalogItem62)
session.commit()

# Catalog for Skiing
catalog7 = Catalog(name="Skiing")

session.add(catalog7)
session.commit()


print "added menu items!"
