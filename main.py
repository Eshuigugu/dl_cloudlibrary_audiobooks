#!/usr/bin/python3
import requests
import base64
import json
import os
import re
import pickle
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
    json_data = {
        'UserId': username,
        'Password': password,
    }

    response = session.post(
        f'https://ebook.yourcloudlibrary.com/uisvc/{library}/Patron/LoginPatron',
        headers=HEADERS,
        json=json_data,
    )
    return response


def list_loaned_books():
    return session.get(
        f'https://ebook.yourcloudlibrary.com/uisvc/{library}/Patron/Borrowed',
        headers=HEADERS,
    ).json()


def borrow_book(book_id: str):
    return session.post(f'https://ebook.yourcloudlibrary.com/uisvc/{library}/Item/Borrow', headers=HEADERS,
                        data=json.dumps({"CatalogItemId": book_id})).json()


def filter_loaned_books(media_ids: list):
    loaned_books = list_loaned_books()
    return [x for x in loaned_books if x['Id'] in media_ids]


def get_book_metadata_brief(library: str, media_id: str):
    return session.get(f'https://ebook.yourcloudlibrary.com/uisvc/{library}/Item/GetItem?id={media_id}',
                                       headers=HEADERS).json()


def download_book(loaned_book):
    audiobook_meta_brief = get_book_metadata_brief(library, loaned_book["Id"])
    title = audiobook_meta_brief['Title']

    fulfillment_url = loaned_book['fulfillmentTokenUrl'] + f'&token={text_session_id}'

    audiobook_loan = session.get(fulfillment_url, headers=HEADERS).json()
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
    output_directory = f'{loaned_book["Id"]} - {first_author} - {title}'
    # make it a valid file name
    output_directory = re.sub('[^\w\-_\. ]', '', output_directory).strip()[:100]
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # download all the audio files
    for chapter, chapter_info in zip(audiobook_playlist, audiobook_loan['items']):
        file_ext = chapter['url'][::-1].split('.')[0][::-1]
        output_filename = chapter_info['title']
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
        'isbn': audiobook_meta_brief['ISBN'],
        'description': audiobook_meta_brief['Description'],
        'narrator': audiobook_metadata['narrators'],
        'language': audiobook_metadata['language'],
        'thumbnail': audiobook_metadata['cover_url'],
        'series': series,
    }

    print('Fast Fillout JSON:\n' + json.dumps(fast_fillout))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--library', type=str, help='library name')
    parser.add_argument('-u', '--username', nargs='?', type=str, help='The username/barcode to use to log in')
    parser.add_argument('-p', '--password', nargs='?', type=str, help='The password to use to log in')
    parser.add_argument('--prompt_password', nargs='?', default=False, type=bool, help='Whether or not to prompt the user to input a password')
    parser.add_argument('-t', '--title', nargs='?', type=str, help='ID of the title to download')
    args = parser.parse_args()

    library = args.library
    if args.username:
        username = args.username
    else:
        username = input('Input username:')

    if args.prompt_password:
        password = input('Input password:')
    else:
        password = args.password
    media_id = args.title


    if media_id:
        media_meta_brief = get_book_metadata_brief(library, media_id)
        if media_meta_brief['MediaType'] != 'audio': raise Exception("MediaType != audio")

    # log in
    login_json = log_in(library=library, username=username, password=password).json()
    if not login_json["Success"]:
        raise Exception(login_json["FailureReason"])

    obfuscated_session_id = login_json['Osi']
    if obfuscated_session_id.startswith('x-'):
        obfuscated_session_id = obfuscated_session_id[2:]
    text_session_id = base64.b64decode(obfuscated_session_id).decode()

    # if user gave a media id, download that one. otherwise download all loaned books.
    if media_id:
        # list loaned books
        books_to_download = filter_loaned_books([media_id])
        if not books_to_download:
            print(f'borrowing book {media_id}')
            if media_meta_brief['ReaktorPatronAction'] != 'CAN_LOAN': raise Exception("Can't borrow book")
            borrow_book(book_id=media_id)
            books_to_download = filter_loaned_books([media_id])
    else:
        books_to_download = [x for x in list_loaned_books() if x['MediaType'] == 'audio']

    for book_to_download in books_to_download:
        download_book(book_to_download)

