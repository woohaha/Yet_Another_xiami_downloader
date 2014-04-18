#!/usr/bin/env python

import re
import os
import sys
import json
import urllib
import requests
import concurrent.futures

DEBUG=False

class song_info():
    '''
    找出一首歌的信息
    例：http://www.xiami.com/song/1772432927?spm=a1z1s.6659513.0.0.eCXGhY
    '''
    # album: 'http://www.xiami.com/song/playlist/id/497547065/type/1/cat/json?_ksTS=1397783765633_689&callback=jsonp690'
    # collection: 'http://www.xiami.com/song/playlist/id/30070469/type/3/cat/json?_ksTS=1397784599970_689&callback=jsonp690'
    def __init__(self,page):
        self.page_id=re.findall(r'\d+',page)[0]
        header={'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
                'referer':'http://www.xiami.com'} #play?ids=/song/playlist/id/{}/object_name/default/object_id/0'.format(self.song_id)}
        self.album_name_of_collection=False
        if 'album' in page:
            self.json_url='http://www.xiami.com/song/playlist/id/{}/type/1/cat/json?_ksTS=1397783765633_689&callback=json'.format(self.page_id)
        elif 'showcollect' in page:
            self.json_url='http://www.xiami.com/song/playlist/id/{}/type/3/cat/json?_ksTS=1397783765633_689&callback=json'.format(self.page_id)
            self.album_name_of_collection='Collection_'+self.page_id
        elif 'song' in page:
            self.json_url='http://www.xiami.com/song/playlist/id/{}/object_name/default/object_id/0/cat/json?callback=json'.format(self.page_id)
        else:
            raise Exception('Not a Vaild URL')
        req=requests.get(self.json_url,headers=header)
        self.page_json=json.loads(req.text[6:-1])
        self.songs=[]

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

        try:

            for song in self.page_json['data']['trackList']:
                self.album_name_of_song=song['album_name'].replace(' ','_')
                self.artist=song['artist'].replace(' ','_')
                self.song_title=song['title'].replace(' ','_')
                self.url=caesar(song['location'])
                self.filename=str(self.page_json['data']['trackList'].index(song)+1)+'.'+self.song_title+'-'+self.album_name_of_song
                self.songs.append((self.filename,self.url))

            if self.album_name_of_collection:
                self.album_name=self.album_name_of_collection
            else:
                self.album_name=self.album_name_of_song
        except TypeError:
            print('The Album Has Been Deleted.')


def MT_download(download_dir, song_addrs, classified, workers=3):
    def download(song_addr, filename):# 真正工作的下載函數

        PATH = ''.join((classified_PATH,
                        filename,'.mp3')) # 構造保存地址
        if DEBUG:
            print('{},{}'.format(PATH,song_addr))
            sys.exit(0)
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
            download, item[1], item[0]): item[0] for item in song_addrs}
        for future in concurrent.futures.as_completed(futureIteams):
            url = futureIteams[future]
            try:
                data = future.result()
                if url in failed:
                    failed.remove(url)
            except Exception as exc:
                print('{} generated an exception: {}'.format(url, exc))
                failed.add(url) # 多線程執行下載函lvok

failed=set()

if __name__=='__main__':
    try:
        url=sys.argv[1]
    except IndexError:
        url=input('Xiami URL:')

    a=song_info(url)
    download_dir=os.path.expanduser('~')+'/Music/'
    MT_download(download_dir,a.songs,a.album_name)
