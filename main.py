#!/usr/bin/env python

import requests
import re
import os
import json
import urllib
import concurrent.futures

class song_info():
    '''
    找出一首歌的信息
    例：http://www.xiami.com/song/1772432927?spm=a1z1s.6659513.0.0.eCXGhY
    '''
    def __init__(self,song_url):
        self.song_id=re.findall(r'\d+',song_url)[0]
        header={'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
                'referer':'http://www.xiami.com/play?ids=/song/playlist/id/{}/object_name/default/object_id/0'.format(self.song_id)}
        self.json_url='http://www.xiami.com/song/playlist/id/{}/object_name/default/object_id/0/cat/json?callback=json'.format(self.song_id)
        req=requests.get(self.json_url,headers=header)
        self.song_info_json=json.loads(req.text[6:-1])

        self.album_name=self.song_info_json['data']['trackList'][0]['album_name']
        self.artist=self.song_info_json['data']['trackList'][0]['artist']
        self.song_title=self.song_info_json['data']['trackList'][0]['title']

        def caesar(location):
            '''
            從location中解密出真實地址
            via: http://lazynight.me/3392.html
            '''
            num = int(location[0])
            avg_len, remainder = int(len(location[1:]) / num), int(len(location[1:]) % num)
            result = [location[i * (avg_len + 1) + 1: (i + 1) * (avg_len + 1) + 1] for i in range(remainder)]
            result.extend([location[(avg_len + 1) * remainder:][i * avg_len + 1: (i + 1) * avg_len + 1] for i in
                           range(num - remainder)])
            url = urllib.parse.unquote(''.join([''.join([result[j][i] for j in range(num)]) for i in range(avg_len)]) + \
                                 ''.join([result[r][-1] for r in range(remainder)])).replace('^', '0')
            return url

        self.url=caesar(self.song_info_json['data']['trackList'][0]['location'])
        self.song={self.song_title+'_'+self.artist:self.url}

def MT_download(download_dir, song_addrs, classified, workers=3):
    def download(song_addr, img_index):# 真正工作的下載函數

        PATH = ''.join((classified_PATH,
                        str(img_index + 1).zfill(2), '_',
                        os.path.basename(song_addr))) # 構造保存地址
        try:
            img_status = os.stat(PATH).st_size
        except FileNotFoundError:
            img_status = 0 # 取得已下載文件的大小,大小與請求頭一致則不下載
        try:
            header={'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
                    'referer':'http://www.xiami.com/play?ids=/song/playlist/id/{}/object_name/default/object_id/0'.format(re.findall(r'/(\d+)_',song_addr))}
            r = requests.get(song_addr, headers=header, stream=True)
            if r.ok and img_status != int(r.headers['content-length']):
                with open(PATH, 'wb') as f:
                    for chunk in r.iter_content():
                        f.write(chunk)
                print('{} Finished'.format(song_addr), end='\r')
        except Exception as Exc:
            print(Exc)

    classified_PATH = ''.join((download_dir, classified, '/'))
    if not os.path.exists(classified_PATH):
        os.makedirs(classified_PATH)
    else:
        go_on = input('Folder exist containing {} files, go ahead?[Y/n]:'
                      .format(len(os.listdir(classified_PATH))))
        if go_on.lower() == 'n':
            print('Downloading Abort.')
            exit(0) # 構建分類目錄

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futureIteams = {executor.submit(
            download, item, song_addrs.index(item)): item for item in song_addrs}
        for future in concurrent.futures.as_completed(futureIteams):
            url = futureIteams[future]
            try:
                data = future.result()
                if url in failed:
                    failed.remove(url)
            except Exception as exc:
                print('{} generated an exception: {}'.format(url, exc))
                failed.add(url) # 多線程執行下載函

failed={}
if __name__=='__main__':
    a=song_info('http://www.xiami.com/song/1769544090?spm=a1z1s.3061781.0.0.JRatOo&from=similar_song')
    print(a.song)
