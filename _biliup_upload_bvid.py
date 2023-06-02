identifier_perfix = 'BiliBili'



import json
import os
import time
from internetarchive import get_item
def upload_bvid(bvid):
    if not os.path.exists('biliup.home'):
        raise Exception('先创建 biliup.home 文件')
    access_key, secret_key = read_ia_keys(os.path.expanduser('~/.bili_ia_keys.txt'))
    # sample: BiliBili-BV1Zh4y1x7RL_p3
    videos_basepath = f'biliup/videos/{bvid}'
    for identifier in os.listdir(videos_basepath):
        if os.path.exists(f'{videos_basepath}/{identifier}/_uploaded.mark'):
            print(f'{identifier} 已经上传过了')
            continue
        pid = identifier.split('_')[-1][1:]
        file_basename = identifier[len(identifier_perfix)+1:]
        if not identifier.startswith(identifier_perfix):
            print(f'{identifier} 不是 {identifier_perfix} 的视频')
            continue
        if not os.path.exists(f'{videos_basepath}/{identifier}/_downloaded.mark'):
            print(f'{identifier} 没有下载完成')
            continue

        print(f'开始上传 {identifier}')
        item = get_item(identifier)
        if item.exists:
            print(f'{identifier} 已经存在')
        filedict = {} # "remote filename": "local filename"
        for filename in os.listdir(f'{videos_basepath}/{identifier}'):
            file = f'{videos_basepath}/{identifier}/{filename}'
            if os.path.isfile(file):
                if os.path.basename(file).startswith('_'):
                    continue
                if not os.path.isfile(file):
                    continue
                filedict[filename] = file
        
        for filename in os.listdir(f'{videos_basepath}/{identifier}/extra'):
            file = f'{videos_basepath}/{identifier}/extra/{filename}'
            if os.path.isfile(file):
                if file.startswith('_'):
                    continue
                filedict[filename] = file

        for file_in_item in item.files:
            if file_in_item["name"] in filedict:
                filedict.pop(file_in_item["name"])
                print(f"File {file_in_item['name']} already exists in {identifier}.")


        with open(f'{videos_basepath}/{identifier}/extra/{file_basename}.info.json', 'r', encoding='utf-8') as f:
            bv_info = json.load(f)
        with open(f'{videos_basepath}/videos_info.json', 'r', encoding='utf-8') as f:
            videos_info = json.load(f)

        tags = ['BiliBili', 'video']
        for tag in bv_info['data']['Tags']:
            tags.append(tag['tag_name'])
        pubdate = bv_info['data']['View']['pubdate']
        for page in bv_info['data']['View']['pages']:
            if page['page'] == int(pid):
                cid = page['cid']
                part = page['part']
                break
        
        md = {
            "mediatype": "web",
            "collection": 'opensource_movies',
            "title": bv_info['data']['View']['title'] + f' P{pid} ' + part ,
            "description": bv_info['data']['View']['desc'],
            'creator': bv_info['data']['View']['owner']['name'], # UP 主
            # UTC time
            'date': time.strftime("%Y-%m-%d", time.gmtime(pubdate)),
            'year': time.strftime("%Y", time.gmtime(pubdate)),
            'bvid': bvid,
            'aid': bv_info['data']['View']['aid'],
            'cid': cid,
            "subject": "; ".join(
                tags
            ),  # Keywords should be separated by ; but it doesn't matter much; the alternative is to set one per field with subject[0], subject[1], ...
            "upload-state": "uploading",
            'originalurl': f'https://www.bilibili.com/video/{bvid}?p={pid}',
            # 每日top100
            'scanner': 'bilibili top100 daily archive',
        }        
        print(filedict)
        print(md)

        r = item.upload(
            files=filedict,
            metadata=md,
            access_key=access_key,
            secret_key=secret_key,
            verbose=True,
            queue_derive=True,
        )

        tries = 30
        item = get_item(identifier) # refresh item
        while not item.exists and tries > 0:
            print(f"Waiting for item to be created ({tries})  ...", end='\r')
            time.sleep(30)
            item = get_item(identifier)
            tries -= 1

        new_md = {}
        if item.metadata.get("upload-state") != "uploaded":
            new_md.update({"upload-state": "uploaded"})
        if new_md:
            r = item.modify_metadata(
                metadata=new_md,
                access_key=access_key,
                secret_key=secret_key,
            )
            r.raise_for_status()
        with open(f'{videos_basepath}/{identifier}/_uploaded.mark', 'w', encoding='utf-8') as f:
            f.write('')
        print(f'{identifier} 上传完成')

def read_ia_keys(keysfile):
    ''' Return: tuple(`access_key`, `secret_key`) '''
    with open(keysfile, 'r', encoding='utf-8') as f:
        key_lines = f.readlines()

    access_key = key_lines[0].strip()
    secret_key = key_lines[1].strip()

    return access_key, secret_key