from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sklearn.cluster import KMeans
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import nest_asyncio
from pyngrok import ngrok
import uvicorn
import json
import requests
import numpy as np
from multiprocessing import Pool
from tqdm import tqdm
app = FastAPI()

def similar(i,j,k):
    url = "https://www.myfitnesspal.com/food/search?page=1&search="
    search = i
    final_url = url + search
    soup = BeautifulSoup(requests.get(final_url).content,'lxml')    
    x = soup.find("div",class_="jss64")
    x = x.a    
    if SequenceMatcher(None,i, x.text).ratio() > 0.4:
        new_url = x.get('href')
        new_url = "https://www.myfitnesspal.com" + new_url  
        soup = BeautifulSoup(requests.get(new_url).content,'lxml') 
        x = soup.find("div",class_="root-1W4Ez") 
        a = (x.find("span",class_="title-cgZqW").text)
        b = (x.find_all("div",class_=" macro-block-3O_MW")[0].text.split("%")[1].split("C")[0])
        c = (x.find_all("div",class_=" macro-block-3O_MW")[1].text.split("%")[1].split("F")[0])
        d = (x.find_all("div",class_=" macro-block-3O_MW")[2].text.split("%")[1].split("P")[0])  
        return new_url,i,j,k,a,b,c,d
    else:
        return None,i,j,k
templates = Jinja2Templates(directory="templates")

@app.get("/",response_class=HTMLResponse)
async def index(request: Request):
     # client_host = request.client.host # get unique ip
     # print(client_host)
     return templates.TemplateResponse("index.html",{"request":request})
@app.post("/", response_class=HTMLResponse)
async def location(request: Request):
     return templates.TemplateResponse("location.html",{"request": request})
@app.post("/location", response_class=HTMLResponse)
async def location(request: Request):
     client_host = request.client.host 
     form_data  = await request.form()
     keys = [k for k, v in form_data.items() if v == 'NEXT']
     x = keys[0].split(",")
     longitude = float(x[1])
     latitude = float(x[0])
     url = 'https://disco.deliveryhero.io/search/api/v1/feed'
     headers = {
    'content-type': "application/json",
     }
     payload = {
     'location': {
          'point': {
               'longitude':longitude ,  # 經度
               'latitude':latitude   # 緯度
          }
     },
     'config': 'Variant17',
     'vertical_types': ['restaurants'],
     'include_component_types': ['vendors'],
     'include_fields': ['feed'],
     'language_id': '6',
     'opening_type': 'delivery',
     'platform': 'web',
     'language_code': 'zh',
     'customer_type': 'regular',
     'limit': 100,  # 一次最多顯示幾筆(預設 48 筆)
     'offset': 0,  # 偏移值，想要獲取更多資料時使用
     'dynamic_pricing': 0,
     'brand': 'foodpanda',
     'country_code': 'tw',
     'use_free_delivery_label': False
     }

     rest, name, longitude, latitude, budget, cusine, promo, rating, code, link= list(),list(),list(),list(),list(),list(),list(),list(),list(),list()
     r = requests.post(url=url, data=json.dumps(payload), headers=headers)
     if r.status_code == requests.codes.ok:
          data = r.json()
          restaurants = data['feed']['items'][0]['items']
          for restaurant in restaurants:
               name.append(restaurant['name'])
               longitude.append(restaurant['longitude'])
               latitude.append(restaurant['latitude'])
               budget.append(restaurant['budget'])
               cusine.append(restaurant['cuisines'][0]['name'])
               promo.append(restaurant['tag'])
               rating.append(restaurant['rating'])
               # print(restaurant)
               code.append(restaurant['code'])
               link.append(restaurant['hero_listing_image'])
     else:
          print('請求失敗')
     rest = np.stack(np.array([name,longitude,latitude,budget,cusine,promo,rating,code,link]),axis=-1)
     np.savetxt(client_host+"_rest.txt",rest,delimiter=",",fmt="%s")
     return templates.TemplateResponse("foodtype.html",{"request": request})
@app.post("/foodtype", response_class=HTMLResponse)
async def foodtype(request: Request):
     # filter between main and desert
     client_host = request.client.host 
     form_data = await request.form()
     rest = np.loadtxt(client_host+"_rest.txt",delimiter=",",dtype=str)
     filter_desert = ['小吃','甜點','飲料','咖啡輕食']
     remove = list()
     if "left_button" in form_data:
          for i in range(len(rest)):
               for j in filter_desert:
                    if rest[i][4] == j: # if it is desert delete
                        remove.append(i)
                        break
     else:
          for i in range(len(rest)):
               check = 0 
               for j in filter_desert:
                    if rest[i][4] == j:
                         check=1
               if check == 0: # if its no desert delete
                    remove.append(i)
     rest = np.delete(rest,remove,0)
     np.savetxt(client_host+"_filtered.txt",rest,delimiter=",",fmt="%s")
     if "left_button" in form_data:
          return templates.TemplateResponse("type.html",{"request":request})
     else:
          return templates.TemplateResponse("budget.html",{"request": request}) 
@app.post("/type",response_class=HTMLResponse)
async def type(request: Request):
     client_host = request.client.host
     form_data = await request.form()
     types = int(list(form_data)[0])
     filter_main = ['台式','麵食','便當','素食','粥','火鍋','早餐']
     rest = np.loadtxt(client_host+"_filtered.txt",delimiter=",",dtype=str)
     all = list()
     remove = list()
     # 0 : other 1 : chinese
     for i in range(len(rest)):
          all.append(i)
          for j in filter_main:
               if rest[i][4] == j:
                    remove.append(i)
                    break
     if types == 0 :
          rest = np.delete(rest,remove,0)
          # print(remove)
          np.savetxt(client_host+"_filtered.txt",rest,delimiter=",",fmt="%s")
     else:
          for i in remove:
               if i in all:
                    all.remove(i)
          # print(all)
          rest = np.delete(rest,all,0)
          np.savetxt(client_host+"_filtered.txt",rest,delimiter=",",fmt="%s")
     return templates.TemplateResponse("budget.html",{"request":request})
@app.post("/budget", response_class=HTMLResponse)
async def budget(request: Request):
     client_host = request.client.host 
     form_data = await request.form()
     budget = int(list(form_data)[0])
     print(budget) # budget has 0,1,2 according to foodpanda filtering method
     rest = np.loadtxt(client_host+"_filtered.txt",delimiter=",",dtype=str)
     remove = list()
    #  for i in range(len(rest)):
    #       if int(rest[i][3]) != budget:
    #            print(rest[i][3],budget)
    #            remove.append(i)
    #  rest = np.delete(rest,remove,0)
     np.savetxt(client_host+"_filtered.txt",rest,delimiter=",",fmt="%s")
     return templates.TemplateResponse("cal.html",{"request": request}) 
@app.post("/cal", response_class=HTMLResponse)
async def calories(request: Request):
     client_host = request.client.host 
     form_data = await request.form()
     cal = int(list(form_data)[0])
     f = open(client_host+".txt","w")
     f.write(str(cal))
     f.close()
     rest = np.loadtxt(client_host+"_filtered.txt",delimiter=",",dtype=str)
     names = rest[:10,0] # name of restaurant
     links = rest[:10,-1] # link of image
     promo = rest[:10,-4]
     rating = rest[:10,-3]
     np.savetxt(client_host+"_filtered.txt",rest,delimiter=",",fmt="%s")
     return templates.TemplateResponse("restaurant.html", {"request": request ,"names":names,"links":links,"size": "400","promo":promo,"rating":rating})
@app.post("/restaurant", response_class=HTMLResponse)
async def restaurant(request: Request):
     client_host = request.client.host 
     form_data = await request.form()
     print(list(form_data)[0]) # name of the restaurant
     index = int(form_data.get(list(form_data)[0]))
     print(index)
     rest = np.loadtxt(client_host+"_filtered.txt",delimiter=",",dtype=str)
     longitude = rest[index][1]
     latitude = rest[index][2]
     code = rest[index][7]
     url = 'https://tw.fd-api.com/api/v5/vendors/'+code
     query = {
     'include': 'menus',
     'language_id': '6',
     'dynamic_pricing': '0',
     'opening_type': 'delivery',
     'longitude': longitude,  # 經度
     'latitude': latitude,  # 緯度
     }
     name = list()
     food_name = list()
     food_price = list()
     food_pic = list()
     food_avail = list()
     r = requests.get(url=url, params=query)
     if r.status_code == requests.codes.ok:
          data = r.json()
          pool = Pool(processes=8)
          x_all = data['data']['menus'][0]
          for i in range(len(x_all['menu_categories'])):
               all = x_all['menu_categories'][i]
          # print()
          for i in range(len(all['products'][:])):
               food_name.append(all['products'][:][i]['name'])
               food_price.append(all['products'][:][i]['product_variations'][0]['price'])
               if all['products'][:][i]['file_path'] == "":
                    food_pic.append("none")
               else:
                    food_pic.append(all['products'][:][i]['file_path'])
          final_food = list()
          final_price = list()
          final_pic = list()
          data_url = list()
          pooler = list()
          cal = list()
          carb = list()
          fat =list()
          protein = list()
          for i in tqdm(range(len(food_name))):
               if food_price[i] !=0:
                    pooler.append(pool.apply_async(similar, (food_name[i],food_pic[i],food_price[i])))# percentage of similarities 
          for t in tqdm(pooler):
               b = t.get()
               if b[0] != None:
                    data_url.append(b[0])
                    final_food.append(b[1])
                    final_price.append(b[3]) # for consistensy
                    if b[2] == 'none':
                      final_pic.append("empty")
                    else:
                      final_pic.append(b[2])
                    cal.append(int(b[4].replace(',', '')))
                    if b[5] == "--":
                      carb.append(0)
                    else:
                      carb.append(int(b[5][:-1]))
                    if b[6] == "--":
                      fat.append(0)
                    else:
                      fat.append(int(b[6][:-1]))
                    if b[7] == "--":
                      protein.append(0)
                    else:
                      protein.append(int(b[7][:-1]))
               else:
                    continue

     else:
          print('請求失敗')
     final_food = np.array(final_food)
     final_pic = np.array(final_pic)
     listing = list()
     for i in range(len(final_food)):
        listing.append(i)
     listing = np.array(listing)
     final_price = np.array(final_price)
     cal = np.array(cal)
     carb = np.array(carb)
     fat = np.array(fat)
     protein = np.array(protein)
     print(len(protein))
     if len(protein) <=1 :
      rest = np.loadtxt(client_host+"_filtered.txt",delimiter=",",dtype=str)
      names = rest[:10,0] # name of restaurant
      links = rest[:10,-1] # link of image
      promo = rest[:10,-4]
      rating = rest[:10,-3]
      np.savetxt(client_host+"_filtered.txt",rest,delimiter=",",fmt="%s")
      return templates.TemplateResponse("restaurant.html", {"request": request ,"names":names,"links":links,"size": "400","promo":promo,"rating":rating})
     total = np.stack((final_price,cal,carb,fat,protein), axis=-1)
     kmeans = KMeans(n_clusters=2, random_state=0).fit(total)
    #  print(kmeans.labels_)
     total = np.stack((final_price,cal,carb,fat,protein,kmeans.labels_,listing), axis=-1)
     total = total[np.argsort(total[:,5])] # sort them by labels
     total = np.split(total, np.where(np.diff(total[:,5]))[0]+1) # split them into 2 different arrays based on labels
     total[0] = total[0][np.argsort(-total[0][:,4])] # negative to have descending order
     total[1] = total[1][np.argsort(total[1][:,4])]
    #  print(total[0])
    #  print(total[1])
     price = list()
     name = list()
     pic = list()
     pic_2 = list()
     cal = list()
     carb = list()
     fat = list() 
     protein = list()
     done_a = list()
     done_b = list()
     max_cal = 1500
     for i in range(len(total[0])):
        for j in range(len(total[1])):
          check = total[0][i][1] + total[1][j][1]
          if len(done_a) < 5:      
            done_a.append(i)
            done_b.append(j)
        # print(done_a)
        # print(done_b)
    #  print(final_pic)
     for i in range(len(done_a)):
        price.append(str(total[0][done_a[i],0]+total[1][done_b[i],0]))
        cal.append(str(total[0][done_a[i],1]+total[1][done_b[i],1]))
        carb.append(str(total[0][done_a[i],2]+total[1][done_b[i],2]))
        fat.append(str(total[0][done_a[i],3]+total[1][done_b[i],3]))
        protein.append(str(total[0][done_a[i],4]+total[1][done_b[i],4]))
        pic.append(final_pic[total[0][done_a[i],-1]])
        pic_2.append(final_pic[total[1][done_b[i],-1]])
        name.append(final_food[total[0][done_a[i],-1]]+","+final_food[total[1][done_b[i],-1]])
    #  print(pic)
    #  print(pic_2)
     np.savetxt(client_host+"_filtered.txt",rest,delimiter=",",fmt="%s")
     return templates.TemplateResponse("food.html", {"request": request,"names": name,"pic":pic,"pic_2":pic_2,"price":price,"cal":cal,"carb":carb,"protein":protein,"fat":fat})
ngrok_tunnel = ngrok.connect(8000,bind_tls=True)
print('Public Url:',ngrok_tunnel.public_url)
nest_asyncio.apply()
uvicorn.run(app,port=8000)