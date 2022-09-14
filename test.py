from instagrapi import Client

c = Client()

# backup_codes = ['0861 9345', '6419 3572', '6219 8407', '5906 8714', '6571 3204']
# seed = 'OZULUOHPM6YCTCB7SNU7QXO5DBUVC5UG'
# code = c.totp_generate_code(seed)
# print(code)

proxy = "http://lum-customer-c_4c113dad-zone-workers_residential-gip-18331618a3c00000:kkbysh4q7nyx@zproxy.lum-superproxy.io:22225"
c.set_proxy(proxy)

c.login(username="marypireaper", password='HQYtbh9F8')
c.challenge_code_handler = input