from instagrapi import Client

cl = Client()
cl.login("YOUR_LOGIN", "YOUR_PASSWORD")

cl.photo_upload("example.jpg"," 😀 😃 😄 😁 😆 😅 😂 🤣 ", True)