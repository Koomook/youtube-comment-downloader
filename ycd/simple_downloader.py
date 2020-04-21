from typing import List, Dict

from .downloader import *


def search_comments(youtube_id: str, sleep=1) -> List[Dict]:
    # Use the new youtube API to download some comments
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    response = session.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id))
    html = response.text
    session_token = find_value(html, 'XSRF_TOKEN', 3)

    data = json.loads(find_value(
        html, 'window["ytInitialData"] = ', 0, '\n').rstrip(';'))
    ncd = next(search_dict(data, 'nextContinuationData'))
    continuations = [(ncd['continuation'], ncd['clickTrackingParams'])]

    ret = []
    while continuations:
        continuation, itct = continuations.pop()
        response = ajax_request(session, YOUTUBE_COMMENTS_AJAX_URL_NEW,
                                params={'action_get_comments': 1,
                                        'pbj': 1,
                                        'ctoken': continuation,
                                        'continuation': continuation,
                                        'itct': itct},
                                data={'session_token': session_token},
                                headers={'X-YouTube-Client-Name': '1',
                                         'X-YouTube-Client-Version': '2.20200207.03.01'})

        if not response:
            break
        if list(search_dict(response, 'externalErrorMessage')):
            raise RuntimeError('Error returned from server: ' +
                               next(search_dict(response, 'externalErrorMessage')))

        # Ordering matters. The newest continuations should go first.
        continuations = [(ncd['continuation'], ncd['clickTrackingParams'])
                         for ncd in search_dict(response, 'nextContinuationData')] + continuations

        ret.append(response)

    return ret


def get_comments_from_data(response_list: List[Dict]) -> List[Dict]:
    ret = []
    for response in response_list:
        for comment in search_dict(response, 'commentRenderer'):
            data = {'cid': comment['commentId'],
                    'text': ''.join([c['text'] for c in comment['contentText']['runs']]),
                    'time': comment['publishedTimeText']['runs'][0]['text'],
                    'author': comment.get('authorText', {}).get('simpleText', ''),
                    'votes': int(comment.get('voteCount', {}).get('simpleText', '0')),
                    'photo': comment['authorThumbnail']['thumbnails'][-1]['url']}
            ret.append(data)
    return ret
