from common import Episode, Season, get_json, train_apply, sort_key
import os
import re
import sys
import time
import json

config = get_json('config.json')

CONF_TEMPLATES = {
    "config.json": {
        "milvus_host": "127.0.0.1",
        "milvus_port": 19530,
        "downloadDir": "download",
        "videoOutDir": os.path.join("static", "video"),
        "imgTmpDir": "tmp_images",
        "coverDir": os.path.join("static", "img", "cover"),
        "downloadBilibili": {
            "queue": {
                "seasons": []
            },
            "default": {
                "SESSDATA": "",
                "quality": 64,
                "presets": [
                    "Xception_PCA"
                ],
                "tag": "$seasonId",
                "episodes": "^:$",
                "override": False
            },
        },
        "process": {
            "rate": 5,
            "crf": 36,
            "resolution": 480,
            "removeVideo": True,
            "removeFrame": False,
            "filteSimlity": 0.85
        },
        "trainPCA": {
            "episodes": [],
            "selectNum": 512
        }
    }
}
DIRS = [
    'static',
    os.path.join('static', 'json'),
    os.path.join('static', 'img'),
    os.path.join('static', 'img', 'cover'),
    os.path.join('static', 'img', 'upload'),
    os.path.join('static', 'video'),
    'download',
    'tmp_images',
    'db',
    'pca'
]

def init():
    for i in DIRS:
        if not os.path.exists(i):
            print('mkdir', i)
            os.mkdir(i)

    for i in CONF_TEMPLATES:
        if not os.path.exists(i):
            print("init", i)
            f = open(i, 'w')
            f.write(json.dumps(CONF_TEMPLATES[i], indent=4))
            f.close()

init()

def download_bilibili():
    queue = config['downloadBilibili']['queue']
    default = config['downloadBilibili']['default']
    for s in queue['seasons']:
        bili_ssid = s['seasonId']
        settings = {
            'SESSDATA': s['SESSDATA'] if 'SESSDATA' in s else default['SESSDATA'],
            'quality': s['quality'] if 'quality' in s else default['quality'],
            'presets': s['presets'] if 'presets' in s else default['presets'],
            'tag': s['tag'] if 'tag' in s else default['tag'],
        }
        episodes_str = s['episodes'] if 'episodes' in s else default['episodes']
        override = s['override'] if 'override' in s else default['override']
        start, end = episodes_str.split(":")
        if start == '^':
            start = None
        else:
            start = int(start)
        if end == '$':
            end = None
        else:
            end = int(end)
        season = Season(bili_ssid=bili_ssid, settings=settings)
        season.load_episodes(start, end)
        if override:
            season.update_settings(settings)
        season.download()

def process():
    for dirname in sorted(os.listdir(config['imgTmpDir']), key=sort_key):
        season_dir = os.path.join(config['imgTmpDir'], dirname)
        if not os.path.isdir(season_dir):
            continue
        if not re.match(r'^\d+$', dirname):
            continue
        season = Season(from_id=dirname)
        for ep_dirname in os.listdir(season_dir):
            ep_dir = os.path.join(season_dir, ep_dirname)
            if not os.path.isdir(ep_dir):
                continue
            if not re.match(r'^\d+$', ep_dirname):
                continue
            if not os.path.exists(os.path.join(ep_dir, 'ready')):
                continue
            season.add_episode(ep_dirname)
        season.episodes.sort(key=lambda ep: sort_key(ep.id))
        season.process()
    for dirname in sorted(os.listdir(config['downloadDir']), key=sort_key):
        season_dir = os.path.join(config['downloadDir'], dirname)
        if not os.path.isdir(season_dir):
            continue
        if not re.match(r'^\d+$', dirname):
            continue
        season = Season(from_id=dirname)
        for ep_dirname in os.listdir(season_dir):
            ep_dir = os.path.join(season_dir, ep_dirname)
            if not os.path.isdir(ep_dir):
                continue
            if not re.match(r'^\d+$', ep_dirname):
                continue
            if not os.path.exists(os.path.join(ep_dir, 'done')):
                continue
            season.add_episode(ep_dirname)
        season.episodes.sort(key=lambda ep: sort_key(ep.id))
        season.process()

def train_pca():
    for epid in config['trainPCA']['episodes']:
        episode = Episode(from_id=str(epid))
        episode.train_add()
    train_apply()

def import_info(info):
    for i in info:
        if 'episode/' in i['type']:
            item = Episode(from_id=i['id'])
        elif 'season/' in i['type']:
            item = Season(from_id=i['id'])
        item.update_data(i)
    

def main():
    start_time = time.time()
    if len(sys.argv) <= 1:
        print('Must input arg')
        return
    if sys.argv[1] == 'download-bilibili':
        download_bilibili()
        end_time = time.time()
        if (end_time - start_time) > 500:
            restart()
    elif sys.argv[1] == 'process':
        process()
        end_time = time.time()
        if (end_time - start_time) > 500:
            restart()
    elif sys.argv[1] == 'train-pca':
        train_pca()
    elif sys.argv[1] == 'import-info':
        import_info(get_json(sys.argv[2]))
    else:
        print('Invalid arg')
        return

def restart():
    global config
    config = get_json('config.json')
    main()

if __name__ == '__main__':
    main()