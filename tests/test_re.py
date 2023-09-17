import re
url = 'https://www.autohome.com.cn/news/202309/1288654.html#pvareaid=102624'


print(re.search('/(\d+).html',url).group(1))