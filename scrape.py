from requests import Session
from bs4 import BeautifulSoup
import pandas as pd
from PIL import Image
import io,os
import threading



BASE_URL = 'https://www.shein.com/'
session = Session()
image_path='images/'

def log_d(message):
	print('[+]---- ',message,'----')

def get_header():
	return {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
		}
def get_soup(text_html):
	return BeautifulSoup(text_html,'html.parser')

def get_main_categories(soup):
	categories = {}
	div = soup.find('div',class_="first-cate-ctn")
	for a in div.findAll('a'):
		categories[a['title']]=a['href']
	return categories

def get_product_info(link):
	product = {}
	with session.request(method='GET',url=link,headers=get_header()) as response:
		text_html = response.text
		soup = get_soup(text_html)

		path = soup.find('div',class_="mgds-goodsd").find('ul').findChildren('li',recursive=False)
		
		# print(len(path))
		category_tree = ''
		for i in path[1:-2]:
			category_tree += i.text.replace('\r','').replace('\n','') + '|'

		product['category_tree'] = category_tree[:-1]


		img = soup.find('img',class_='j-change-main_image').get('data-src')
		product['image'] = img

		div = soup.find('div',class_='desc-con')
		list_div = get_soup(str(div)).findAll('div',class_='kv-row')
		description = ''
		for div in list_div:
			key = get_soup(str(div)).find('div',class_='key').text
			val = ' '.join(get_soup(str(div)).find('div',class_='val').text.replace(u'\n','').split())
			description += key+' '+val+' | '
		product['description'] = description[:-2]

	return product

def download_image(product):
	tmp_image=product['image']
	resp = session.request(method='GET',url='http:'+tmp_image,headers=get_header())
	product['image'] = product['id']+'_shein.'+tmp_image.split('.')[-1]
	file = io.BytesIO(resp.content)
	img = Image.open(file).convert("RGB")
	img.save(image_path+product['image'],'jpeg')

def get_product_thread(list_div,index,nb_thread,products):
	step = int(len(list_div)/nb_thread)
	
	for div in list_div[index*step:(index*step)+step]:
		product = dict()
		link = get_soup(str(div)).find('a',class_='j-item-msg')
		product['name'] = link.get('title')
		log_d('Thread '+str(index)+': getting product '+str(list(list_div).index(div)+1)+'/'+str(len(list(list_div)))+': '+product['name'])
		product['id'] = link.get('data-id')
		product['price'] = link.get('data-price')+'€'
		link_product = BASE_URL+link.get('href')
		product_info = get_product_info(link_product)
		product.update(product_info)
		download_image(product)

		# print(product)
		products.append(product)

	# return products

def get_products_by_page(page_link):
	products = list()
	with session.request(method='GET',url=page_link,headers=get_header()) as response:
		text_html = response.text
		soup = get_soup(text_html)
		div = soup.findAll('div',class_='row')[1]
		list_div = get_soup(str(div)).findAll('div',class_='c-goodsli')
		print (len(list_div))
	
		threads = list()
		nb_thread = 20
		for index in range(nb_thread):
		    # logging.info("Main    : create and start thread %d.", index)
		    x = threading.Thread(target=get_product_thread, args=(list_div,index,nb_thread,products,))
		    threads.append(x)
		    x.start()

		for thread in threads:
			thread.join()


	return products

def get_pages_link(link):
	link_pages = [link]
	with session.request(method='GET',url=link,headers=get_header()) as response:
		text_html = response.text
		soup = get_soup(text_html)
		nb_product = int(soup.find('span',class_='header-sum').text.replace('Products',''))
		nb_page = int(nb_product/120 + (0 if nb_product%120 == 0 else 1))
		for i in range(2,nb_page+1):
			link_page = link+'&page='+str(i)
			link_pages.append(link_page)	
	return link_pages

def get_all_products_by_cat(i):
	products = []

	with session.request(method='GET',url=BASE_URL,headers=get_header()) as response:
		text_html = response.text
		soup = get_soup(text_html)
		div = soup.findAll('div',class_="nav2-ctn2")[i]

		url_all_product = ""
		for a in div.findAll('a'):
			if 'Clothing' in a['title']:
				url_all_product = a['href']

		pages = get_pages_link(url_all_product)[0:1]
		for page in pages:
			log_d('\tgetting products from page '+str(pages.index(page)+1)+'/'+str(len(pages)))
			products += get_products_by_page(page)
	return products

def main():

	if not os.path.exists(image_path):
		os.mkdir(image_path)

	url = BASE_URL
	all_products = []
	with session.request(method='GET',url=url,headers=get_header()) as response:
		text_html = response.text
		soup = get_soup(text_html)
		log_d('getting main categories')
		categories = get_main_categories(soup)
		print(categories)
		log_d('getting main categories DONE')
		log_d('getting all products START')
		for name_cat,link_cat in list(categories.items())[1:2]:
			log_d('getting products of '+name_cat+' '+str(list(categories.keys()).index(name_cat)+1)+'/'+str(len(categories.keys())))

			products_cat = get_all_products_by_cat(list(categories.keys()).index(name_cat))
			df = pd.DataFrame(products_cat)
			df.to_csv('shein_products_'+name_cat+'.csv')
		# log_d('getting all products DONE')
	

if __name__ == '__main__':
	main()
