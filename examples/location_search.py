from instagrapi import Client

cl = Client()
cl.login("YOUR_LOGIN", "YOUR_PASSWORD")

loc=cl.location_search(59.93318, 30.30605)
print(loc)
print("-")
print("-")

loc1=cl.location_search_pk(107617247320879)
print(loc1)
print("-")
print("-")


loc2=cl.location_search_name("Choroni")
print(loc2)