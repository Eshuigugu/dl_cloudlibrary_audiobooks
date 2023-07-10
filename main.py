#!/usr/bin/python3
import requests
import json
import os
import re
import argparse

session = requests.Session()
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json;charset=UTF-8',
    'Origin': 'https://ebook.yourcloudlibrary.com',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-GPC': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="112", "Brave";v="112", "Not:A-Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


def log_in(library: str, username: str, password: str):
    headers = HEADERS.copy()
    for k, v in {
        'content-type': 'application/x-www-form-urlencoded',
        'authority': 'ebook.yourcloudlibrary.com',
                }.items():
        headers[k] = v
    data = {
        'action': 'login',
        'barcode': username,
        'pin': password,
    }

    response = session.post(
        f'https://ebook.yourcloudlibrary.com/library/{library}/',
        params={'_data': 'root'},
        headers=headers,
        data=data,
    )

    return response


def list_loaned_books(library: str, form_data: dict = None):
    headers = {
        'authority': 'ebook.yourcloudlibrary.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://ebook.yourcloudlibrary.com',
        'referer': f'https://ebook.yourcloudlibrary.com/library/{library}/mybooks/current',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Brave";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    }
    if not form_data:
        form_data = {'format':'', 'sort': 'BorrowedDateDescending'}
    return session.post(f'https://ebook.yourcloudlibrary.com/library/{library}/mybooks/current?_data=routes%2Flibrary%2F%24name%2Fmybooks%2Fcurrent',
                       json=form_data,
                       headers=headers).json()['patronItems']


def return_book(book_id, library):
    headers = {
        'authority': 'ebook.yourcloudlibrary.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'referer': f'https://ebook.yourcloudlibrary.com/library/{library}/detail/{book_id}',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Brave";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    }
    params = {
        'action': 'return',
        'itemId': book_id,
        '_data': 'routes/library/$name/detail/$id',
    }
    return session.get(
        f'https://ebook.yourcloudlibrary.com/library/{library}/detail/{book_id}',
        params=params,
        headers=headers,
    )


def borrow_book(book_id: str, library: str):
    headers = {
        'authority': 'ebook.yourcloudlibrary.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'referer': f'https://ebook.yourcloudlibrary.com/library/{library}/detail/{book_id}',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Brave";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    }
    params = {
        'action': 'borrow',
        'itemId': book_id,
        '_data': 'routes/library/$name/detail/$id',
    }
    return session.get(
        f'https://ebook.yourcloudlibrary.com/library/{library}/detail/{book_id}',
        params=params,
        headers=headers,
    ).json()


def filter_loaned_books(media_ids: list, library: str):
    loaned_books = list_loaned_books(library)
    return [x for x in loaned_books if x['itemId'] in media_ids]


def get_book_metadata_brief(library: str, media_id: str):
    return session.get(f'https://ebook.yourcloudlibrary.com/library/{library}/detail/{media_id}?_data=routes%2Flibrary%2F%24name%2Fdetail%2F%24id',
            headers=HEADERS).json()['book']


def download_book(loaned_book: dict, library: str, dump_json=False):
    book_id = loaned_book['itemId']
    audiobook_meta_brief = get_book_metadata_brief(library, book_id)
    title = audiobook_meta_brief['title']

    fulfillment_url = f'https://audio.yourcloudlibrary.com/listen/{book_id}?_data=routes/listen.$id'

    headers = {
        'authority': 'audio.yourcloudlibrary.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.5',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': 'https://ebook.yourcloudlibrary.com/',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Brave";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-site',
        'sec-fetch-user': '?1',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    }
    audiobook_loan = session.get(fulfillment_url, headers=headers).json()['audiobook']
    fulfillment_id = audiobook_loan['fulfillmentId']

    metadata_url = f'https://api.findawayworld.com/v4/accounts/{audiobook_loan["accountId"]}/audiobooks/{fulfillment_id}'

    cross_site_headers = HEADERS.copy()
    for k,v in {
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Sec-Fetch-Site': 'cross-site',
                'Session-Key': audiobook_loan['sessionKey'],
                }.items():
        cross_site_headers[k] = v

    audiobook_metadata = session.get(metadata_url,
                                     headers=cross_site_headers).json()['audiobook']


    audiobook_playlist = session.post(f'https://api.findawayworld.com/v4/audiobooks/{fulfillment_id}/playlists',
                                      headers=cross_site_headers, data=json.dumps(
            {"license_id": audiobook_loan['licenseId']})).json()['playlist']

    if audiobook_metadata["authors"]:
        first_author = audiobook_metadata["authors"][0]
    else:
        first_author = ''
    output_directory = f'{book_id} - {first_author} - {title}'
    # make it a valid file name
    output_directory = re.sub('[^\w\-_. ]', '', output_directory).strip()[:100]
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    max_chapter_idx_length = len(str(len(audiobook_loan['items'])))
    chapter_idx = 1
    # download all the audio files
    for chapter, chapter_info in zip(audiobook_playlist, audiobook_loan['items']):
        file_ext = chapter['url'][::-1].split('.')[0][::-1]
        output_filename = f'%0{max_chapter_idx_length}d - ' % chapter_idx + chapter_info['title']
        chapter_idx += 1
        output_filename += f'.{file_ext}'

        output_filepath = os.path.join(output_directory, output_filename)
        if os.path.exists(output_filepath):
            print(output_filepath, 'exists. skipping')
            continue
        r = session.get(chapter['url'], headers=cross_site_headers)
        print(f'downloading to {output_filepath}')
        with open(output_filepath, 'wb') as f:
            f.write(r.content)

    # convert json to JSON fast fillout
    # see if it should add a subtitle
    if 'SubTitle' in audiobook_meta_brief and audiobook_meta_brief['SubTitle'].lower() != 'a novel':
        subtitle = audiobook_meta_brief['SubTitle']
    else:
        subtitle = None

    series = []
    for series_string in audiobook_metadata['series']:
        re_match = re.search(' #\d+$', series_string)
        if re_match:
            series_number = series_string[re_match.span()[0]:].lstrip(' #')
            series_string = series_string[:re_match.span()[0]]
        else:
            series_number = ''
        series.append({'name': series_string, 'number': series_number})


    fast_fillout = {
        'authors': audiobook_metadata['authors'],
        'title': f'{title}: {subtitle}' if subtitle else title,
        'isbn': audiobook_meta_brief['isbn'],
        'description': audiobook_meta_brief['description'],
        'narrator': audiobook_metadata['narrators'],
        'language': audiobook_metadata['language'],
        'thumbnail': audiobook_metadata['cover_url'],
        'series': series,
    }

    print('Fast Fillout JSON:\n' + json.dumps(fast_fillout))

    # dump metadata to file in JSON format
    if dump_json:
        merged_metadata = audiobook_meta_brief
        for k,v in audiobook_metadata.items():
            merged_metadata[k]=v
        merged_metadata['chapters'] = audiobook_loan['items']
        with open(f'{book_id}.json', 'w') as f:
            json.dump(merged_metadata, f, indent='\t')
    return output_directory


def download_books(library, username, password, return_books=False, dump_json=False, media_id=None):
    if media_id:
        media_meta_brief = get_book_metadata_brief(library, media_id)
        if media_meta_brief['mediaType'] != 'Mp3': raise Exception(f"MediaType != Mp3 {media_meta_brief['mediaType']}")

    # log in
    login_json = log_in(library=library, username=username, password=password).json()
    if "stack" in login_json:
       raise Exception(login_json["stack"])

    # if user gave a media id, download that one. otherwise download all loaned books.
    if media_id:
        # repeat this because now we can see if it can be loaned
        media_meta_brief = get_book_metadata_brief(library, media_id)
        # list loaned books
        books_to_download = filter_loaned_books([media_id], library)
        if not books_to_download:
            print(f'borrowing book {media_id}')
            if media_meta_brief['status'] != 'CAN_LOAN': raise Exception("Can't borrow book")
            borrow_book(book_id=media_id, library=library)
            books_to_download = filter_loaned_books([media_id], library)
    else:
        books_to_download = [x for x in list_loaned_books(library) if x['mediaType'] == 'Mp3']

    for book_to_download in books_to_download:
        yield download_book(book_to_download, library, dump_json=dump_json)
        if return_books:
            return_book(book_to_download['itemId'], library)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--library', type=str, help='library name')
    parser.add_argument('-u', '--username', nargs='?', type=str, help='The username/barcode to use to log in')
    parser.add_argument('-p', '--password', nargs='?', type=str, help='The password to use to log in')
    parser.add_argument('--prompt_password', nargs='?', default=False, type=bool, help='Whether or not to prompt the user to input a password')
    parser.add_argument('-t', '--title', nargs='?', type=str, help='ID of the title to download')
    parser.add_argument('--dump_json', action='store_true', help='Dump data in JSON format to file')
    parser.add_argument('--release', action='store_true', help='Return selected books')

    args = parser.parse_args()

    if args.username:
        username = args.username
    else:
        username = input('Input username:')

    if args.prompt_password:
        password = input('Input password:')
    else:
        password = args.password
    media_id = args.title
    dump_json = args.dump_json
    return_books = args.release
    for download in download_books(library=args.library, username=username, password=password, return_books=return_books,
            dump_json=dump_json, media_id=media_id):
        print(f'downloaded {download}')

