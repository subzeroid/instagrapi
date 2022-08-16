from instagrapi import Client

c = Client()

backup_codes = ['0861 9345', '6419 3572', '6219 8407', '5906 8714', '6571 3204']



seed = 'OZULUOHPM6YCTCB7SNU7QXO5DBUVC5UG'

code = c.totp_generate_code(seed)
print(code)

c.login(username="jennifermcdonaldlerd", password='jennifermcdonaldld171',verification_code=str(code))