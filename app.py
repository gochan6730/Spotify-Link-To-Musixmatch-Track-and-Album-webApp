from flask import Flask, request, render_template, make_response
from asgiref.wsgi import WsgiToAsgi
from mxm import MXM
from spotify import Spotify
import re
import aiohttp
import datetime

class StartAiohttp:
    session = None
    def __init__(self,limit, limit_per_host) -> None:
        self.limit = limit
        self.limit_per_host = limit_per_host
        

    def start_session(self):
        connector = aiohttp.TCPConnector(limit=self.limit, limit_per_host=self.limit_per_host)
        self.session = aiohttp.ClientSession(connector=connector)

    def get_session(self):
        return self.session


    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

client = StartAiohttp(7,7)


app = Flask(__name__)
sp = Spotify()

@app.route('/', methods=['GET'])
async def index():
    link = request.args.get('link')
    if link:
        key = request.cookies.get("api_key",None)
        client.start_session()
        mxm = MXM(key,session=client.get_session())
        try:
            if(len(link) < 12): return render_template('index.html', tracks_data= ["Wrong Spotify Link Or Wrong ISRC"])
            elif re.search(r'artist/(\w+)', link): return render_template('index.html',artist=sp.artist_albums(link,[]))
            else: sp_data = sp.get_isrc(link) if len(link) > 12 else [{"isrc": link, "image": None}]
        except Exception as e:
            return render_template('index.html', tracks_data= [str(e)])
            
        mxmLinks = await mxm.Tracks_Data(sp_data)
        if isinstance(mxmLinks, str):
            return mxmLinks
        
        await client.close_session()

        return render_template('index.html', tracks_data= mxmLinks)

    return render_template('index.html')


@app.route('/split', methods=['GET'])
async def split():
    link = request.args.get('link')
    link2 = request.args.get('link2')
    if link and link2:
        key = request.cookies.get("api_key",None)
        client.start_session()
        mxm = MXM(key,session=client.get_session())
        match = re.search(r'open.spotify.com', link) and re.search(r'track', link)
        match =  match and re.search(r'open.spotify.com', link2) and re.search(r'track', link2)
        if match:
            sp_data1 = sp.get_isrc(link)
            sp_data2 = sp.get_isrc(link2)
            track1 = await mxm.Tracks_Data(sp_data1,True)
            track1 = track1[0]
            if isinstance(track1,str): return render_template('split.html', error= "track1: " + track1)
            track2 = await mxm.Tracks_Data(sp_data2,True)
            track2 = track2[0]
            if isinstance(track2,str): return render_template('split.html', error= "track2: " + track1)
            await client.close_session()
            track1["track"] = sp_data1[0]["track"]
            track2["track"] = sp_data2[0]["track"]
            try:
                if track1["isrc"] != track2["isrc"] and track1["commontrack_id"] == track2["commontrack_id"]:
                    message = f"""Can be splitted </br>
                                you can c/p:</br>
                                :mxm: <a href="{track1["track_share_url"]}" target="_blank">MXM Page</a> </br>
                                :spotify: <a href="{link}" target="_blank">{track1["track"]["name"]}</a>,
                                :isrc: {track1["isrc"]} </br>
                                :spotify: <a href="{link2}" target="_blank">{track2["track"]["name"]}</a>,
                                :isrc: {track2["isrc"]}
                                """
                elif track1["isrc"] == track2["isrc"] and track1["commontrack_id"] == track2["commontrack_id"]:
                    message = "Can not be splitted as they have the Same ISRC"
                else:
                    message=  "They have different Pages"
            except:
                return render_template('split.html', error = "Something went wrong")
            
            return render_template('split.html', split_result ={"track1":track1, "track2":track2}
                                    ,message = message)
        else: 
            return render_template('split.html', error= "Wrong Spotify Link")
        
    else:
        return render_template('split.html')

@app.route('/spotify', methods=['GET'])
def isrc():
    link = request.args.get('link')
    if link:
        match = re.search(r'open.spotify.com', link) and re.search(r'track|album', link)
        if match:
            return render_template('isrc.html', tracks_data= sp.get_isrc(link))
        
        else: 
            return render_template('isrc.html', tracks_data= ["Wrong Spotify Link"])
    else: 
        return render_template('isrc.html')


@app.route('/api', methods=['GET'])
async def setAPI():
    key = request.args.get('key')
    delete = request.args.get("delete_key")
    if key:
        # check the key
        client.start_session()
        mxm = MXM(key,session=client.get_session())
        sp_data = [{"isrc": "DGA072332812", "image": None}]
        mxmLinks = await mxm.Tracks_Data(sp_data)
        client.close_session()
        if isinstance(mxmLinks[0],str):
            return render_template("api.html",error = "Please Enter A Vaild Key")
        resp = make_response(render_template("api.html", key = key))
        expire_date = datetime.datetime.now() + datetime.timedelta(days=360)
        resp.set_cookie("api_key",key,expires = expire_date)
        return resp
    elif delete:
        resp = make_response(render_template("api.html"))
        resp.delete_cookie("api_key")
        return resp
    else:
        key = request.cookies.get('api_key')
        print(key)
        if key: return render_template("api.html", key = key)
        return render_template("api.html")


asgi_app = WsgiToAsgi(app)
if __name__ == '__main__':
    import asyncio
    from hypercorn.config import Config
    from hypercorn.asyncio import serve
    asyncio.run(serve(app, Config()))
    #app.run(debug=True)
    