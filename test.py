from instagrapi import Client

c = Client()

# backup_codes = ['0861 9345', '6419 3572', '6219 8407', '5906 8714', '6571 3204']
# seed = 'OZULUOHPM6YCTCB7SNU7QXO5DBUVC5UG'
# code = c.totp_generate_code(seed)
# print(code)

proxy = "http://lum-customer-c_4c113dad-zone-workers-mobile-gip-18330c3b6210000b:zi78xfjkc4df@zproxy.lum-superproxy.io:22225"
c.set_proxy(proxy)

c.login(username="donnameulaay", password='SHeWA74FV')
c.challenge_code_handler = input