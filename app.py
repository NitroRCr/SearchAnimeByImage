# -*- coding: utf-8 -*-
import time
from flask import Flask
from flask import request, url_for, abort
from frame_box import FrameBox
import init_conf
import json
import os
import re
import urllib.request
flask_app = None
class App:
            
    def __init__(self):
        self.req_num = 0
        self.hash_buffer = []
        self.IMAGE_SAVE_PATH = os.path.join("static", "img", "upload")
        self.IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
        self.STATE_PATH = "state.json"
        self.CONFIG_PATH = "config.json"
        self.RES_SAVE_PATH = os.path.join("static", "json", "response")
        self.PRE_URL = ""
        
        self.state = json.loads(open(self.STATE_PATH).read())
        self.frame_box = FrameBox()
        self.create_flask()

    def get_req_num(self):
        self.state['requestNum'] += 1;
        f = open(self.STATE_PATH, "w")
        f.write(json.dumps(self.state))
        f.close()
        return self.state['requestNum']

    def create_flask(self):
        flask = Flask(__name__, instance_relative_config=True, static_url_path='')

        @flask.route('/search', methods=['GET', 'POST'])
        def search():
            print(request.method)
            if (request.method == 'GET'):
                return "POST Only"
            if ("search-method" in request.form):
                method = request.form['search-method']
                if method == 'qid':
                    qid = int(request.form['qid'])
                    response = self.get_saved_res(qid)
                    if response == -1:
                        return {
                            "error_code": 404,
                            "error_msg": "Invalid qid"
                        }
                    else:
                        return response
                else:
                    response = {}
                    qid = self.get_req_num()
                    if "tags" in request.form:
                        try:
                            tags = json.loads(request.form['tags'])
                            if len(tags) == 0:
                                tags = None
                        except:
                            tags = None
                    else:
                        tags = None
                    response['qid'] = qid
                    if method == "pic":
                        image = request.files["pic"]
                        save_res = self.save_image(image, qid)
                        response['pic_url'] = save_res['pic_url']
                        response['result'] = self.search_pic(save_res['save_path'], tags)
                    elif method == "url":
                        matched = re.match(r'((https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|])',
                            request.form['url'])
                        if matched:
                            try:
                                save_path = os.path.join(self.IMAGE_SAVE_PATH, str(qid))
                                urllib.request.urlretrieve(matched.group(1), filename=save_path)
                            except urllib.error.HTTPError:
                                return {
                                    "error_code": 400,
                                    "error_msg": "无效的图像链接"
                                }
                            response['pic_url'] = "/img/upload/%d"%qid
                            response['result'] = self.search_pic(save_path)
                        else:
                            return {
                                "error_code": 400,
                                "error_msg": "无效的URL"
                            }
                    else:
                        abort(400)
                    self.save_res(response)
            return response

        @flask.route('/', methods = ['GET'])
        def getIndex():
            return flask.send_static_file('index.html')

        global flask_app
        flask_app = flask

    def search_pic(self, img_path, tags):
        self.frame_box.connect()
        ret = self.frame_box.search_with_info(img_path, tags)
        self.frame_box.close()
        return ret

    def get_saved_res(self, qid):
        try:
            f = open(os.path.join(self.RES_SAVE_PATH, "%d.json"%qid))
        except IOError:
            return -1
        response = json.loads(f.read())
        f.close()
        return response
    def save_res(self, response):
        try:
            f = open(os.path.join(self.RES_SAVE_PATH, "%d.json"%response['qid']), 'w')
            f.write(json.dumps(response))
            f.close()
        except FileNotFoundError as e:
            os.makedirs(self.RES_SAVE_PATH)
            self.save_res(response)
    

    def save_image(self, image, qid):
        extension = os.path.splitext(image.filename)[-1]
        if (extension not in self.IMAGE_EXTENSIONS):
            return -1
        now_num = qid
        save_path = os.path.join(self.IMAGE_SAVE_PATH, '%d'%(now_num))
        try:
            image.save(save_path)
            return {
                "pic_url": "/img/upload/%d"%(now_num),
                "save_path": save_path
            }
        except FileNotFoundError:
            os.makedirs(self.IMAGE_SAVE_PATH)
            return self.save_image(image)

app = App()

