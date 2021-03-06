from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
from random import randint
from random import choice
import json
import requests
import re
import datetime
import config as conf
import region as reg
import image_link as imgl

app = Flask(__name__)

# Channel Access Token
line_bot_api = LineBotApi(conf.access_token)
# Channel Secret
handler = WebhookHandler(conf.token_secret)
news_api_key = (conf.news_key)

greetings = "Terima kasih telah menambahkan kami ke dalam grup " + chr(0x10008D) + "\nSilakan pilih menu yang tersedia untuk mulai menggunakan."
frame = """{"type": "carousel", "contents": []}"""

# Rich Menu
main_menu = RichMenu(
    size=RichMenuSize(width=800, height=540),
    selected=False,
    name="covid_richmenu",
    chat_bar_text="Menu",
    areas=[
        RichMenuArea(bounds=RichMenuBounds(x=0, y=0, width=265, height=270),
        action=MessageAction(label="Data", text="/data_cases")),
        RichMenuArea(bounds=RichMenuBounds(x=270, y=0, width=265, height=270),
        action=MessageAction(label="Informasi", text="/info")),
        RichMenuArea(bounds=RichMenuBounds(x=536, y=0, width=265, height=270),
        action=MessageAction(label="Call Center", text="/hotline")),
        RichMenuArea(RichMenuBounds(x=0, y=270, width=265, height=270),
        action=MessageAction(label="News", text="/news")),
        RichMenuArea(bounds=RichMenuBounds(x=270, y=270, width=265, height=270),
        action=MessageAction(label="Hoax", text="/hoax")),
        RichMenuArea(bounds=RichMenuBounds(x=536, y=270, width=265, height=270),
        action=MessageAction(label="FAQ", text="/faqs"))
    ]
)
rich_menu_id = line_bot_api.create_rich_menu(rich_menu=main_menu)
print("rich menu id:" + rich_menu_id)
with open('img/menu_bot.png', 'rb') as f:
    line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)
line_bot_api.set_default_rich_menu(rich_menu_id)

# Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Number grouping
# Works in integer type only
# Output are string
def group(number):
    s = '%d' % number
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))

@handler.add(JoinEvent)
def handle_join(event):
    line_bot_api.reply_message(event.reply_token,TextSendMessage(text=greetings))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print(event)
    msg_from_user = event.message.text.strip()
    
    if msg_from_user.lower() == '/data_cases':
        menu = open("menu/menu_data.json", "r").read()
        bubble_string = json.loads(menu)
        message = FlexSendMessage(alt_text="Flex Message", contents=bubble_string)
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/global_cases':
        #add Country
        region, death, confirm, recover, rate = [], [], [], [], []
        try:
            response = requests.get('https://corona.lmao.ninja/v2/countries?sort=cases')
            data = json.loads(response.text)
            for i in range(len(data)):
                region.append(data[i]['country'])
                confirm.append(group(data[i]['cases']))
                death.append(group(data[i]['deaths']))
                recover.append(group(data[i]['recovered']))
                try:
                    res = int(data[i]['deaths'])/int(data[i]['cases'])*100
                    rate.append(str(round(res, 2)))
                except Exception as e:
                    rate.append(0)
            response = requests.get('https://corona.lmao.ninja/v2/all/')
            all_ = json.loads(response.text)
            total = "Total positif: " + group(all_['cases']) +"\nTotal meninggal: " + group(all_['deaths']) + \
            "\nTotal sembuh: " + group(all_['recovered'])

            carousel = open("carousel_template.json", "r").read()
            bubble_string = carousel
            dictionary = json.loads(bubble_string)
            item = dictionary['contents'][0]['body']['contents'][4]['contents']
            # Insert data
            # Dictionary index based on json file
            for i in range(len(item)):
                country = region[i].split(',')
                item[i]['contents'][0]['text'] = country[0]
                item[i]['contents'][2]['text'] = confirm[i]
                item[i]['contents'][4]['text'] = recover[i]
                item[i]['contents'][6]['text'] = death[i]
                item[i]['contents'][8]['text'] = rate[i]

            # Convert dictionary to json
            bubble_string = json.dumps(dictionary)
            message = [FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string)), TextSendMessage(text=total)]
        except Exception as e:
            print(e)
            message = TextSendMessage(text="Mohon maaf, saat ini data tidak dapat dimuat. Silakan coba beberapa saat lagi.")
        finally:
            line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/today_cases':
        region = [] 
        today_cases = []
        today_deaths = []
        try:
            response = requests.get('https://corona.lmao.ninja/v2/countries?sort=todayCases')
            data = json.loads(response.text)
            for i in range(len(data)):
                region.append(data[i]['country'])
                today_cases.append(data[i]['todayCases'])
                today_deaths.append(data[i]['todayDeaths'])

            zipped = list(zip(today_cases, today_deaths, region))
            zipped.sort(reverse=True)

            var = """{"type": "bubble", "body": {"type": "box", "layout": "vertical", "contents": []} }"""
            header = """{"type": "text", "text": "Data COVID-19 Hari Ini", "weight": "bold", "wrap": true, "align": "center", "color": "#0a0a0a", "margin": "md"}, {"type": "separator", "color" : "#424242"},{"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "Negara", "weight": "bold", "margin": "xs", "color": "#0a0a0a", "size": "xs", "flex": 6, "gravity": "center", "align": "center"}, {"type": "separator", "color" : "#424242", "margin": "xs"}, {"type": "text", "text": "Jumlah Positif", "weight": "bold", "margin": "xs", "color": "#0a0a0a", "size": "xs", "flex": 5, "gravity": "center", "wrap": true, "align": "center"}, {"type": "separator", "color" : "#424242", "margin": "xs"}, {"type" : "text", "text" : "Jumlah Meninggal", "weight" : "bold", "margin" : "xs", "color" : "#0a0a0a", "size" : "xs", "flex" : 5, "gravity" : "center", "wrap": true, "align" : "center"}] }, {"type": "separator", "color" : "#424242"},"""
            box_item = """{"type": "box", "layout": "vertical", "margin": "none", "contents": []}"""
            item = """{"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "region", "wrap": false, "color": "#0a0a0a", "margin": "xs", "size": "xs", "flex": 6 }, {"type": "separator", "color" : "#424242", "margin": "xs"}, {"type": "text", "text": "positive", "align": "end", "wrap": false, "color": "#0a0a0a", "margin": "xs", "size": "xs", "flex": 5 }, {"type": "separator", "color" : "#424242", "margin": "xs"}, {"type": "text", "text": "???", "align": "end", "wrap": false, "color": "#0a0a0a", "margin": "xs", "size": "xs", "flex": 5 }]}"""
            items = ""
            loop = len(zipped)
            for i in zipped:
                if i[0] == 0:
                    loop-=1
            
            loop = 25 if loop > 25 else loop
            for i in range(loop):
                items += item
                if i < loop-1:
                    items += ','

            box_full = box_item[:-2] + items + box_item[-2:]
            results = frame[:-2] + var[:-4] + header + box_full + var[-4:] + frame[-2:]
            dictionary = json.loads(results)
            item = dictionary['contents'][0]['body']['contents'][4]['contents']
            # Insert data
            # Dictionary index based on json file
            for i in range(len(item)):
                item[i]['contents'][0]['text'] = zipped[i][2]
                item[i]['contents'][2]['text'] = group(zipped[i][0])
                item[i]['contents'][4]['text'] = group(zipped[i][1])

            total_cases = sum(today_cases)
            total_deaths = sum(today_deaths)
            # Convert dictionary to json
            total_all = "Total Positif: " + group(total_cases) + "\nTotal Meninggal: " + group(total_deaths)
            bubble_string = json.dumps(dictionary)
            message = [FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string)), TextSendMessage(text=total_all)]
        except Exception as e:
            print(e)
            message = TextSendMessage(text="Mohon maaf, saat ini data tidak dapat dimuat. Silakan coba beberapa saat lagi."+e)
        finally:
            line_bot_api.reply_message(event.reply_token, message)
    
    elif msg_from_user.lower() == '/prov_cases':
        try:
            response = requests.get('https://api.kawalcorona.com/indonesia/provinsi/')
            data = json.loads(response.text)
            var = """{"type": "bubble", "size": "giga", "body": {"type": "box", "layout": "vertical", "contents": []} }"""
            header = """{"type": "text", "text": "Data COVID-19 Per-Provinsi Di Indonesia", "weight": "bold", "wrap": true, "align": "center", "color": "#0a0a0a", "margin": "md"}, {"type": "separator", "color" : "#424242", "margin": "md"}, {"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "Provinsi", "weight": "bold", "margin": "xs", "color": "#0a0a0a", "size": "xs", "flex": 7, "gravity": "center", "align": "center"}, {"type": "separator", "color" : "#424242", "margin": "xs"}, {"type": "text", "text": "Jumlah Positif", "weight": "bold", "margin": "xs", "color": "#0a0a0a", "size": "xs", "flex": 5, "gravity": "center", "wrap": true, "align": "center"}, {"type": "separator", "color" : "#424242", "margin": "xs"}, {"type": "text", "text": "Jumlah Meninggal", "weight": "bold", "margin": "xs", "color": "#0a0a0a", "size": "xs", "flex": 5, "gravity": "center", "wrap": true, "align": "center"}, {"type": "separator", "color" : "#424242", "margin": "xs"}, {"type": "text", "text": "Jumlah Sembuh", "flex": 5, "margin": "xs", "wrap": true, "gravity": "center", "align": "center", "size": "xs", "weight": "bold", "color": "#0a0a0a"} ] }, {"type": "separator", "color" : "#424242", "margin": "none"},"""
            box_item = """{"type": "box", "layout": "vertical", "margin": "none", "contents": []}"""
            item = """{"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "region", "wrap": true, "color": "#0a0a0a", "margin": "xs", "size": "xs", "flex": 7 }, {"type": "separator", "color" : "#424242", "margin": "xs"}, {"type": "text", "text": "positive", "align": "end", "wrap": true, "color": "#0a0a0a", "margin": "xs", "size": "xs", "flex": 5, "gravity": "center"}, {"type": "separator", "color" : "#424242", "margin": "xs"}, {"type": "text", "text": "???", "align": "end", "wrap": true, "color": "#0a0a0a", "margin": "xs", "size": "xs", "flex": 5, "gravity": "center"}, {"type": "separator", "color" : "#424242", "margin": "xs"}, {"type": "text", "text": "???", "flex": 5, "margin": "xs", "color": "#0a0a0a", "size": "xs", "align": "end", "gravity": "center", "wrap": true }]}"""
            items = ""
            prov = []
            positif = []
            sembuh = []
            meninggal = []

            for i in range(len(data)):
                prov.append(data[i]['attributes']['Provinsi'])
                positif.append(data[i]['attributes']['Kasus_Posi'])
                sembuh.append(data[i]['attributes']['Kasus_Semb'])
                meninggal.append(data[i]['attributes']['Kasus_Meni'])

            zipped = list(zip(prov, positif, meninggal, sembuh))
            loop = len(zipped)
            for i in range(loop):
                items += item
                if i < loop-1:
                    items += ','

            box_full = box_item[:-2] + items + box_item[-2:]
            results = frame[:-2] + var[:-4] + header + box_full + var[-4:] + frame[-2:]
            dictionary = json.loads(results)
            
            item = dictionary['contents'][0]['body']['contents'][4]['contents']
            # Insert data
            # Dictionary index based on json file
            for i in range(len(item)):
                item[i]['contents'][0]['text'] = zipped[i][0]
                item[i]['contents'][2]['text'] = group(zipped[i][1])
                item[i]['contents'][4]['text'] = group(zipped[i][2])
                item[i]['contents'][6]['text'] = group(zipped[i][3])

            total_pos = sum(positif)
            total_semb = sum(sembuh)
            total_meni = sum(meninggal)
            total_all = "Total positif: " + group(total_pos) + "\nTotal sembuh: " + group(total_semb) + "\nTotal meninggal: " + group(total_meni)
            bubble_string = json.dumps(dictionary)
            message = [FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string)), TextSendMessage(text=total_all)]
        except Exception as e:
            print(e)
            message = TextSendMessage(text="Mohon maaf, saat ini data tidak dapat dimuat. Silakan coba beberapa saat lagi.")
        finally:
            line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/news':
        try:
            query = ['virus corona', 'covid-19', 'corona']
            query = choice(query)
            print("Berita pilihan:", query)
            url = 'http://newsapi.org/v2/top-headlines?country=id&q='+query+'&apiKey='+news_api_key
            response = requests.get(url)
            results = json.loads(response.text)
            titles = []
            sources = []
            descs = []
            authors = []
            urls = []
            urlsToImage = []

            news = len(results['articles'])
            news = 5 if news > 5 else news

            for i in range(news):
                titles.append(results['articles'][i]['title'])
                sources.append(results['articles'][i]['source']['name'])
                descs.append(results['articles'][i]['description'])
                authors.append(results['articles'][i]['author'])
                urls.append(results['articles'][i]['url'])
                if results['articles'][i]['urlToImage'] == None:
                    urlsToImage.append("https://scdn.line-apps.com/n/channel_devcenter/img/fx/01_1_cafe.png")
                else:
                    urlsToImage.append(results['articles'][i]['urlToImage'])

            zipped = list(zip(titles, descs, sources, authors, urls, urlsToImage))
            # Flex message dynamic json
            # ==========================================================================================
            flex = """{"type": "bubble", "hero": {"type": "image", "url": "url_image", "size": "full", "aspectMode": "cover", "aspectRatio": "16:9"}, "body": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "JUDUL BERITA", "weight": "bold", "size": "md", "wrap": true }, {"type": "text", "text": "lorem ipsum dolor sit amet", "wrap": true, "size": "sm", "style": "normal", "weight": "regular"}, {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [{"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "Penulis", "color": "#aaaaaa", "size": "sm", "flex": 2 }, {"type": "text", "text": "Author Name", "wrap": true, "color": "#666666", "size": "sm", "flex": 7 } ] }, {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "Sumber", "color": "#aaaaaa", "size": "sm", "flex": 2 }, {"type": "text", "text": "example.com", "wrap": true, "color": "#666666", "size": "sm", "flex": 7 } ] } ] } ] }, "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [{"type": "button", "style": "link", "height": "sm", "action": {"type": "uri", "label": "Buka Tautan", "uri": "https://example.com"}, "color": "#fafafa"}, {"type": "spacer", "size": "sm"} ], "flex": 0, "backgroundColor": "#68829e"} }"""
            results = ""
            for i in range(news):
                results += flex
                if i < news-1:
                    results += ","

            carousel = frame[0:-2] + results + frame[-2:]
            dictionary = json.loads(carousel)
            item = dictionary['contents']
            # ==========================================================================================
            # Add title, desc, source, author, url, urlImage
            for i in range(news):
                news_title = re.split("\s-\s", zipped[i][0])
                item[i]['body']['contents'][0]['text'] = news_title[0]
                item[i]['body']['contents'][1]['text'] = zipped[i][1]
                item[i]['body']['contents'][2]['contents'][1]['contents'][1]['text'] = zipped[i][2]
                item[i]['body']['contents'][2]['contents'][0]['contents'][1]['text'] = zipped[i][3]
                # LINE's thumbnails only eat https, not eat http!
                item[i]['footer']['contents'][0]['action']['uri'] = zipped[i][4]
                item[i]['hero']['url'] = zipped[i][5]

            bubble_string = json.dumps(dictionary)
            dict_replace = {'http://' : '"https://"', 'null' : '"-"'}
            
            for i, j in dict_replace.items():
                bubble_string = bubble_string.replace(i, j)

            message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string))
        except Exception as e:
            print(e)
            message = TextSendMessage(text="Mohon maaf, tidak ada berita terbaru tentang Covid-19.")
        finally:
            line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/hotline':
        file = open("info/hotline.json", "r").read()
        txt = "Sentuh atau klik pada no. telepon untuk langsung menghubungi"
        message = [FlexSendMessage(alt_text="Hotline Covid-19", contents=json.loads(file)), TextSendMessage(text=txt)]
        line_bot_api.reply_message(event.reply_token,message)

    elif msg_from_user.lower() == '/info':
        file = open("menu/info.json" , "r").read()
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(file))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/tips':
        tips = open("info/tips.json", "r").read()
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(tips))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/hoax':
        file = open("info/hoax.json", "r").read()
        message = FlexSendMessage(alt_text="HOAX", contents=json.loads(file))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/istilah':
        file = open("info/istilah.json", "r").read()
        message = FlexSendMessage(alt_text="Istilah", contents=json.loads(file))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/istilah_hal_2':
        file = open("info/istilah_2.json", "r").read()
        message = FlexSendMessage(alt_text="Istilah2", contents=json.loads(file))
        line_bot_api.reply_message(event.reply_token, message)
    
    elif msg_from_user.lower() == '/tidak':
        message = TextSendMessage(text="Baik, terima kasih")
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/rujukan':
        file = open("info/wilayah.json", "r").read()
        response = "Silahkan pilih wilayah anda"
        message = [TextSendMessage(text=response), FlexSendMessage(alt_text="Flex Message", contents=json.loads(file))]
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/faqs':
        file = open("faq/faq.json", "r").read()
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(file))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == '/tips_anti_hoax':
        file = open("info/tips_anti_hoax.json", "r").read()
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(file))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user.lower() == 'insight_followers':
        today = datetime.date.today().strftime("%Y%m%d")
        response = line_bot_api.get_insight_followers(today)
        if response.status == 'ready':
            messages = [
                TextSendMessage(text='followers: ' + str(response.followers)),
                TextSendMessage(text='targetedReaches: ' + str(response.targeted_reaches)),
                TextSendMessage(text='blocks: ' + str(response.blocks)),
            ]
        else:
            messages = [TextSendMessage(text='status: ' + response.status)]
        line_bot_api.reply_message(event.reply_token, messages)
    
    elif msg_from_user.lower() == 'insight_demographic':
        response = line_bot_api.get_insight_demographic()
        if response.available:
            messages = ["{gender}: {percentage}".format(gender=it.gender, percentage=it.percentage)
                        for it in response.genders]
        else:
            messages = [TextSendMessage(text='available: false')]
        line_bot_api.reply_message(event.reply_token, messages)

    elif msg_from_user in reg.provinsi.keys():
        keyword = msg_from_user
        key_prov = []
        value_prov = []
        if keyword.lower() in reg.provinsi.keys():
            wilayah = keyword.lower()
        #tampilkan provinsi tiap pulau
        for i, j in reg.provinsi[wilayah].items():
            key_prov.append(i)
            value_prov.append(j)
            
        zipped = list(zip(key_prov, value_prov))

        if msg_from_user == "sumatera":
            image = imgl.img_sumatera
        elif msg_from_user == "jawa":
            image = imgl.img_jawa
        elif msg_from_user == "kalimantan":
            image = imgl.img_kalimantan
        elif msg_from_user == "sulawesi":
            image = imgl.img_sulawesi
        elif msg_from_user == "nusa_tenggara":
            image = imgl.img_nt
        elif msg_from_user == "maluku":
            image = imgl.img_maluku
        elif msg_from_user == "papua":
            image = imgl.img_papua

        flex_item = ""
        item = """{"type": "bubble","size": "kilo", "hero": { "type": "image", "url": "https://scdn.line-apps.com/n/channel_devcenter/img/fx/01_1_cafe.png", "size": "full", "aspectRatio": "1:1", "aspectMode": "cover" }, "footer": { "type": "box", "layout": "vertical", "spacing": "sm", "contents": [ { "type": "button", "style": "link", "height": "sm", "action": { "type": "message", "label": "nama_provinsi", "text": "nama_provinsi" }, "color": "#fafafa" }, { "type": "spacer", "size": "sm" } ], "flex": 0, "backgroundColor": "#68829e" } }"""
        loop = len(reg.provinsi[wilayah])
        for i in range(loop):
            flex_item += item
            if i < loop-1:
                flex_item += ","
        
        flex_message = frame[0:-2] + flex_item + frame[-2:]
        dictionary = json.loads(flex_message)

        # for i,j in provinsi_result.items():
        for i in range(loop):
            dictionary['contents'][i]['footer']['contents'][0]['action']['label'] = zipped[i][1]
            dictionary['contents'][i]['footer']['contents'][0]['action']['text'] = zipped[i][0]
            dictionary['contents'][i]['hero']['url'] = image[i]

        choose = "Pilih provinsi anda"
        message = [TextSendMessage(text=choose), FlexSendMessage(alt_text="Flex message", contents=dictionary)]
        line_bot_api.reply_message(event.reply_token, message)

    # Display rumah sakit
    elif msg_from_user in json.loads(open("provinsi/kalimantan.json", "r").read()):
        nama_rs = []
        no_hp = []
        label = []
        file = open("provinsi/kalimantan.json", "r").read()
        data = json.loads(file)
        item = data[msg_from_user]['rumah_sakit']
        jumlah_rs = len(item)
        for i in range(jumlah_rs):
            nama_rs.append(item[i]['nama'])
            no_hp.append(item[i]['telp']['text'])
            label.append(item[i]['telp']['no'])

        zipped = list(zip(nama_rs, no_hp, label))
        item = """{"type": "bubble", "size": "kilo", "hero": {"type": "image", "url": "https://raw.githubusercontent.com/xstreamx/LINE-Bot-COVID-19/master/img/medical_center.png", "size": "full", "aspectRatio": "16:9", "aspectMode": "fit", "action": {"type": "uri", "uri": "http://linecorp.com/"} }, "body": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "Nama_RS", "weight": "bold", "size": "md", "gravity": "center", "wrap": true }, {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [{"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "No. telp", "color": "#424242", "size": "sm", "flex": 2 }, {"type": "text", "text": "082122222222", "wrap": true, "color": "#424242", "size": "sm", "flex": 5 } ] } ] } ] }, "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [{"type": "button", "style": "link", "height": "sm", "action": {"type": "uri", "label": "Hubungi", "uri": "tel://888"} }, {"type": "spacer", "size": "sm"} ], "flex": 0 } }"""
        items = ""
        loop = len(zipped)
        
        for i in range(loop):
            items += item
            if i < loop-1:
                items += ','

        results = frame[:-2] + items + frame[-2:]
        dictionary = json.loads(results)
        item = dictionary['contents']
        # Insert data
        # Dictionary index based on json file
        for i in range(len(item)):
            item[i]['body']['contents'][0]['text'] = zipped[i][0]
            item[i]['body']['contents'][1]['contents'][0]['contents'][1]['text'] = zipped[i][2]
            item[i]['footer']['contents'][0]['action']['uri'] = "tel://"+ zipped[i][1]

        bubble_string = json.dumps(dictionary)
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user in json.loads(open("provinsi/sumatera.json", "r").read()):
        nama_rs = []
        no_hp = []
        label = []
        file = open("provinsi/sumatera.json", "r").read()
        data = json.loads(file)
        item = data[msg_from_user]['rumah_sakit']
        jumlah_rs = len(item)
        for i in range(jumlah_rs):
            nama_rs.append(item[i]['nama'])
            no_hp.append(item[i]['telp']['text'])
            label.append(item[i]['telp']['no'])

        zipped = list(zip(nama_rs, no_hp, label))
        item = """{"type": "bubble", "size": "kilo", "hero": {"type": "image", "url": "https://raw.githubusercontent.com/xstreamx/LINE-Bot-COVID-19/master/img/medical_center.png", "size": "full", "aspectRatio": "16:9", "aspectMode": "fit", "action": {"type": "uri", "uri": "http://linecorp.com/"} }, "body": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "Nama_RS", "weight": "bold", "size": "md", "gravity": "center", "wrap": true }, {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [{"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "No. telp", "color": "#424242", "size": "sm", "flex": 2 }, {"type": "text", "text": "082122222222", "wrap": true, "color": "#424242", "size": "sm", "flex": 5 } ] } ] } ] }, "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [{"type": "button", "style": "link", "height": "sm", "action": {"type": "uri", "label": "Hubungi", "uri": "tel://888"} }, {"type": "spacer", "size": "sm"} ], "flex": 0 } }"""
        items = ""
        loop = len(zipped)
        
        for i in range(loop):
            items += item
            if i < loop-1:
                items += ','

        results = frame[:-2] + items + frame[-2:]
        dictionary = json.loads(results)
        item = dictionary['contents']
        # Insert data
        # Dictionary index based on json file
        for i in range(len(item)):
            item[i]['body']['contents'][0]['text'] = zipped[i][0]
            item[i]['body']['contents'][1]['contents'][0]['contents'][1]['text'] = zipped[i][2]
            item[i]['footer']['contents'][0]['action']['uri'] = "tel://"+ zipped[i][1]

        bubble_string = json.dumps(dictionary)
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user in json.loads(open("provinsi/sulawesi.json", "r").read()):
        nama_rs = []
        no_hp = []
        label = []
        file = open("provinsi/sulawesi.json", "r").read()
        data = json.loads(file)
        item = data[msg_from_user]['rumah_sakit']
        jumlah_rs = len(item)
        for i in range(jumlah_rs):
            nama_rs.append(item[i]['nama'])
            no_hp.append(item[i]['telp']['text'])
            label.append(item[i]['telp']['no'])

        zipped = list(zip(nama_rs, no_hp, label))
        item = """{"type": "bubble", "size": "kilo", "hero": {"type": "image", "url": "https://raw.githubusercontent.com/xstreamx/LINE-Bot-COVID-19/master/img/medical_center.png", "size": "full", "aspectRatio": "16:9", "aspectMode": "fit", "action": {"type": "uri", "uri": "http://linecorp.com/"} }, "body": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "Nama_RS", "weight": "bold", "size": "md", "gravity": "center", "wrap": true }, {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [{"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "No. telp", "color": "#424242", "size": "sm", "flex": 2 }, {"type": "text", "text": "082122222222", "wrap": true, "color": "#424242", "size": "sm", "flex": 5 } ] } ] } ] }, "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [{"type": "button", "style": "link", "height": "sm", "action": {"type": "uri", "label": "Hubungi", "uri": "tel://888"} }, {"type": "spacer", "size": "sm"} ], "flex": 0 } }"""
        items = ""
        loop = len(zipped)
        
        for i in range(loop):
            items += item
            if i < loop-1:
                items += ','

        results = frame[:-2] + items + frame[-2:]
        dictionary = json.loads(results)
        item = dictionary['contents']
        # Insert data
        # Dictionary index based on json file
        for i in range(len(item)):
            item[i]['body']['contents'][0]['text'] = zipped[i][0]
            item[i]['body']['contents'][1]['contents'][0]['contents'][1]['text'] = zipped[i][2]
            item[i]['footer']['contents'][0]['action']['uri'] = "tel://"+ zipped[i][1]

        bubble_string = json.dumps(dictionary)
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user in json.loads(open("provinsi/jawa.json", "r").read()):
        nama_rs = []
        no_hp = []
        label = []
        file = open("provinsi/jawa.json", "r").read()
        data = json.loads(file)
        item = data[msg_from_user]['rumah_sakit']
        jumlah_rs = len(item)
        for i in range(jumlah_rs):
            nama_rs.append(item[i]['nama'])
            no_hp.append(item[i]['telp']['text'])
            label.append(item[i]['telp']['no'])

        zipped = list(zip(nama_rs, no_hp, label))
        item = """{"type": "bubble", "size": "kilo", "hero": {"type": "image", "url": "https://raw.githubusercontent.com/xstreamx/LINE-Bot-COVID-19/master/img/medical_center.png", "size": "full", "aspectRatio": "16:9", "aspectMode": "fit", "action": {"type": "uri", "uri": "http://linecorp.com/"} }, "body": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "Nama_RS", "weight": "bold", "size": "md", "gravity": "center", "wrap": true }, {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [{"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "No. telp", "color": "#424242", "size": "sm", "flex": 2 }, {"type": "text", "text": "082122222222", "wrap": true, "color": "#424242", "size": "sm", "flex": 5 } ] } ] } ] }, "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [{"type": "button", "style": "link", "height": "sm", "action": {"type": "uri", "label": "Hubungi", "uri": "tel://888"} }, {"type": "spacer", "size": "sm"} ], "flex": 0 } }"""
        items = ""
        loop = len(zipped)
        
        for i in range(loop):
            items += item
            if i < loop-1:
                items += ','

        results = frame[:-2] + items + frame[-2:]
        dictionary = json.loads(results)
        item = dictionary['contents']
        # Insert data
        # Dictionary index based on json file
        for i in range(len(item)):
            item[i]['body']['contents'][0]['text'] = zipped[i][0]
            item[i]['body']['contents'][1]['contents'][0]['contents'][1]['text'] = zipped[i][2]
            item[i]['footer']['contents'][0]['action']['uri'] = "tel://"+ zipped[i][1]

        bubble_string = json.dumps(dictionary)
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user in json.loads(open("provinsi/nusa_tenggara.json", "r").read()):
        nama_rs = []
        no_hp = []
        label = []
        file = open("provinsi/nusa_tenggara.json", "r").read()
        data = json.loads(file)
        item = data[msg_from_user]['rumah_sakit']
        jumlah_rs = len(item)
        for i in range(jumlah_rs):
            nama_rs.append(item[i]['nama'])
            no_hp.append(item[i]['telp']['text'])
            label.append(item[i]['telp']['no'])

        zipped = list(zip(nama_rs, no_hp, label))
        item = """{"type": "bubble", "size": "kilo", "hero": {"type": "image", "url": "https://raw.githubusercontent.com/xstreamx/LINE-Bot-COVID-19/master/img/medical_center.png", "size": "full", "aspectRatio": "16:9", "aspectMode": "fit", "action": {"type": "uri", "uri": "http://linecorp.com/"} }, "body": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "Nama_RS", "weight": "bold", "size": "md", "gravity": "center", "wrap": true }, {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [{"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "No. telp", "color": "#424242", "size": "sm", "flex": 2 }, {"type": "text", "text": "082122222222", "wrap": true, "color": "#424242", "size": "sm", "flex": 5 } ] } ] } ] }, "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [{"type": "button", "style": "link", "height": "sm", "action": {"type": "uri", "label": "Hubungi", "uri": "tel://888"} }, {"type": "spacer", "size": "sm"} ], "flex": 0 } }"""
        items = ""
        loop = len(zipped)
        
        for i in range(loop):
            items += item
            if i < loop-1:
                items += ','

        results = frame[:-2] + items + frame[-2:]
        dictionary = json.loads(results)
        item = dictionary['contents']
        # Insert data
        # Dictionary index based on json file
        for i in range(len(item)):
            item[i]['body']['contents'][0]['text'] = zipped[i][0]
            item[i]['body']['contents'][1]['contents'][0]['contents'][1]['text'] = zipped[i][2]
            item[i]['footer']['contents'][0]['action']['uri'] = "tel://"+ zipped[i][1]

        bubble_string = json.dumps(dictionary)
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user in json.loads(open("provinsi/maluku.json", "r").read()):
        nama_rs = []
        no_hp = []
        label = []
        file = open("provinsi/maluku.json", "r").read()
        data = json.loads(file)
        item = data[msg_from_user]['rumah_sakit']
        jumlah_rs = len(item)
        for i in range(jumlah_rs):
            nama_rs.append(item[i]['nama'])
            no_hp.append(item[i]['telp']['text'])
            label.append(item[i]['telp']['no'])

        zipped = list(zip(nama_rs, no_hp, label))
        item = """{"type": "bubble", "size": "kilo", "hero": {"type": "image", "url": "https://raw.githubusercontent.com/xstreamx/LINE-Bot-COVID-19/master/img/medical_center.png", "size": "full", "aspectRatio": "16:9", "aspectMode": "fit", "action": {"type": "uri", "uri": "http://linecorp.com/"} }, "body": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "Nama_RS", "weight": "bold", "size": "md", "gravity": "center", "wrap": true }, {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [{"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "No. telp", "color": "#424242", "size": "sm", "flex": 2 }, {"type": "text", "text": "082122222222", "wrap": true, "color": "#424242", "size": "sm", "flex": 5 } ] } ] } ] }, "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [{"type": "button", "style": "link", "height": "sm", "action": {"type": "uri", "label": "Hubungi", "uri": "tel://888"} }, {"type": "spacer", "size": "sm"} ], "flex": 0 } }"""
        items = ""
        loop = len(zipped)
        
        for i in range(loop):
            items += item
            if i < loop-1:
                items += ','

        results = frame[:-2] + items + frame[-2:]
        dictionary = json.loads(results)
        item = dictionary['contents']
        # Insert data
        # Dictionary index based on json file
        for i in range(len(item)):
            item[i]['body']['contents'][0]['text'] = zipped[i][0]
            item[i]['body']['contents'][1]['contents'][0]['contents'][1]['text'] = zipped[i][2]
            item[i]['footer']['contents'][0]['action']['uri'] = "tel://"+ zipped[i][1]

        bubble_string = json.dumps(dictionary)
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string))
        line_bot_api.reply_message(event.reply_token, message)

    elif msg_from_user in json.loads(open("provinsi/papua.json", "r").read()):
        nama_rs = []
        no_hp = []
        label = []
        file = open("provinsi/papua.json", "r").read()
        data = json.loads(file)
        item = data[msg_from_user]['rumah_sakit']
        jumlah_rs = len(item)
        for i in range(jumlah_rs):
            nama_rs.append(item[i]['nama'])
            no_hp.append(item[i]['telp']['text'])
            label.append(item[i]['telp']['no'])

        zipped = list(zip(nama_rs, no_hp, label))
        item = """{"type": "bubble", "size": "kilo", "hero": {"type": "image", "url": "https://raw.githubusercontent.com/xstreamx/LINE-Bot-COVID-19/master/img/medical_center.png", "size": "full", "aspectRatio": "16:9", "aspectMode": "fit", "action": {"type": "uri", "uri": "http://linecorp.com/"} }, "body": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "Nama_RS", "weight": "bold", "size": "md", "gravity": "center", "wrap": true }, {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [{"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "No. telp", "color": "#424242", "size": "sm", "flex": 2 }, {"type": "text", "text": "082122222222", "wrap": true, "color": "#424242", "size": "sm", "flex": 5 } ] } ] } ] }, "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [{"type": "button", "style": "link", "height": "sm", "action": {"type": "uri", "label": "Hubungi", "uri": "tel://888"} }, {"type": "spacer", "size": "sm"} ], "flex": 0 } }"""
        items = ""
        loop = len(zipped)
        
        for i in range(loop):
            items += item
            if i < loop-1:
                items += ','

        results = frame[:-2] + items + frame[-2:]
        dictionary = json.loads(results)
        item = dictionary['contents']
        # Insert data
        # Dictionary index based on json file
        for i in range(len(item)):
            item[i]['body']['contents'][0]['text'] = zipped[i][0]
            item[i]['body']['contents'][1]['contents'][0]['contents'][1]['text'] = zipped[i][2]
            item[i]['footer']['contents'][0]['action']['uri'] = "tel://"+ zipped[i][1]

        bubble_string = json.dumps(dictionary)
        message = FlexSendMessage(alt_text="Flex Message", contents=json.loads(bubble_string))
        line_bot_api.reply_message(event.reply_token, message)

    else:
        message = TextSendMessage(text="Saya tidak mengerti apa yang anda maksud, silahkan gunakan menu yang tersedia")
        line_bot_api.reply_message(event.reply_token, message)

import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)