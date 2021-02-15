import argparse, logging
from csv import DictWriter
from pytube import YouTube, exceptions, helpers
from os import makedirs, path
from time import sleep
from sys import argv


def write_captions(captions, video, position, group=None, convert_srt=False, include_title=False, include_channel=False):
    """Write Caption object to a file. If an output folder is not specified, captions will be placed in a folder corresponding to the name of the video's author (i.e. channel).

    :param captions: The Caption track to download
    :param position: Channel-wise position of the video in the url list
    :param group: The folder to output the caption track to (default None)
    :param convert_srt: Convert captions from XML to SRT format (default False)
    :param include_title: Include video title in caption filename (default True)
    :param include_channel: Save file to channel subfolder (default False)

    :return success: 1 if captions were downloaded successfully, 0 otherwise
    """

    safe_title = helpers.safe_filename(video.title)
    safe_author = helpers.safe_filename(video.author)
    out_path = ""

    out_path = path.join("corpus", "raw_subtitles")
    if group is not None:
        out_path = path.join(out_path, group)

    if "a." in captions.code:
        out_path = path.join(out_path, "auto", captions.code.split(".")[1])
    else:
        out_path = path.join(out_path, "manual", captions.code)

    if(include_channel):
        out_path = path.join(out_path, video.author)

    if not path.exists(out_path):
        makedirs(out_path)

    try:
        if include_title:
            captions.download(helpers.safe_filename(safe_title), srt=convert_srt, output_path=out_path, filename_prefix="{0}_{1}_".format(safe_author, position))
        else:
            captions.download(str(position), srt=convert_srt, output_path=out_path, filename_prefix="{0}_".format(safe_author))
            return 1
    except:
        logging.critical("Video {0}: Could not download caption track for video {0} from channel {1} ({2})".format(position, video.author, video.title))
        return 0


def write_audio(audio, video, position, group=None, include_title=False, include_channel=False):
    """Write audio Stream object to a file. If an output folder is not specified, audio will be placed in a folder corresponding to the name of the video's author (i.e. channel).

    :param audio: The audio Stream to download
    :param position: Channel-wise position of the video in the url list
    :param group: The folder to output the audio stream to (default None)
    :param include_title: Include video title in audio filename (default True)
    :param include_channel: Save file to channel subfolder (default False)
    """

    safe_title = helpers.safe_filename(video.title)
    safe_author = helpers.safe_filename(video.author)

    out_path = path.join("corpus", "raw_audio")
    if group is not None:
        out_path = path.join(out_path, group)

    if(include_channel):
        out_path = path.join(out_path, video.author)

    if not path.exists(out_path):
        makedirs(out_path)

    try:
        if include_title:
            audio.download(filename=safe_title, output_path=out_path, filename_prefix="{0}_{1}_".format(safe_author, position), skip_existing=True)
        else:
            audio.download(filename=str(position), output_path=out_path, filename_prefix="{0}_".format(safe_author), skip_existing=True)

    except:
        logging.critical("Video {0}: Could not save audio stream for video {0} from channel {1} ({2})".format(position, video.author, video.title))


def write_captions_by_language(video, position, language=None, group=None, include_auto=False, convert_srt=False, include_title=False, include_channel=False):
    """Filter captions by language and write each caption track to a file. If no language is specified, all caption tracks will be downloaded.

    :param video: The YouTube object to download caption tracks from
    :param position: Channel-wise position of the video in the url list
    :param language: The language to download caption tracks for (default None)
    :param group: The folder to output the caption track to (default None)
    :param convert_srt: Convert captions from XML to SRT format (default False)
    :param include_title: Include video title in caption filename (default False)
    :param include_channel: Download caption tracks to channel subfolder (default False)

    :return caption_list: list of metadata for all successfully-downloaded caption tracks
    """

    caption_list = []
    for track in video.captions:
        if language is None or (language in track.name and (include_auto or "a." not in track.code)):
            success = write_captions(track, video, position, group, convert_srt, include_title, include_channel)
            if success:
                caption_list.append((track.code, track.name))
            sleep(1)
    return caption_list


def write_metadata(video, position, caption_list, log_writer):
    """Write video metadata to log file.

    :param video: The YouTube object to log
    :param position: Channel-wise position of the video in the url list
    :param caption_list: A list of successfully-downloaded captions
    :param log_writer: DictWriter to use for writing metadata
    """

    metadata = {
        "position": position,
        "author": video.author,
        "title": video.title,
        "description": video.description.replace('\n', ' '),
        "keywords": video.keywords,
        "length": video.length,
        "publish_date": video.publish_date,
        "views": video.views,
        "rating": video.rating,
        "captions": caption_list
    }

    log_writer.writerow(metadata)


def process_video(video, channel_dict, log_writer, language=None, group=None, include_audio=False, include_auto=False, convert_srt=False, include_title=False, include_channels=False):
    """Download captions, audio (optional), and metadata for a given video.

    :param video: The YouTube object to process
    :param position: Channel-wise position of the video in the url list
    :param language: The language to download caption tracks for (default None)
    :param group: The folder to output the caption track to (default None)
    :param convert_srt: Convert captions from XML to SRT format (default False)
    :param include_title: Include video title in caption filename (default False)

    :return caption_dict: list of metadata for all successfully-downloaded caption tracks
    """

    if video.author not in channel_dict.keys():
        channel_dict.update({video.author: 0})
    channel_dict[video.author] = channel_dict[video.author] + 1

    position = channel_dict[video.author]

    caption_list = write_captions_by_language(video, position, language, group, include_auto, convert_srt, include_title, include_channels)

    if include_audio:
        audio = video.streams.filter(mime_type="audio/mp4").first()
        write_audio(audio, video, position, group, include_title, include_channels)

    if len(caption_list):
        write_metadata(video, position, caption_list, log_writer)

    return channel_dict


def process_videos(urls_path, language=None, group=None, include_audio=False, include_auto=False, convert_srt=False, include_titles=False, include_channels=False, resume_from=0, limit_to=-1):
    """Download captions, audio (optional), and metadata for a list of videos.

    :param video: Path to a file containing the list of URLs to process
    :param language: The language to download caption tracks for (default None)
    :param group: The subfolder to output the caption and audio tracks to (default None)
    :param include_audio: Download audio in addition to captions (default False)
    :param include_auto: Download automatically-generated captions (default False)
    :param convert_srt: Convert captions from XML to SRT format (default False)
    :param include_titles: Include video titles in caption filenames (default False)
    :param resume_from: Start from the Nth entry in the URL list (default 0)
    :param limit_to: Download captions (and audio) from only N files (default -1)
    """

    channel_dict = {}
    video_count = 0

    if group is None:
        log_fn = "{0}_log.csv".format(path.splitext(path.split(urls_path)[1])[0])
    else:
        log_fn = "{0}_log.csv".format(group)

    with open(urls_path, "r") as urls_in, open(path.join("corpus", "logs", log_fn), 'w') as log_out:

        # Prepare writer for writing video data
        log_writer = DictWriter(log_out, fieldnames=["author", "position", "title", "description", "keywords", "length", "publish_date", "views", "rating", "captions"])
        log_writer.writeheader()

        for url_data in urls_in:

            video_count += 1

            if(video_count < resume_from):
                continue

            # Get URL and title
            # TODO: Fix Rachel Kim problem
            try:
                (url, channel_name, channel_id) = url_data.strip('\n').split('\t')
            except:
                url = url_data.strip('\n')

            # Try to load the video
            try:
                video = YouTube(url)
            except KeyError as e:
                logging.warning("Video {0}: Could not retrieve URL ({1})".format(id, url))
                continue
            except exceptions.VideoUnavailable as e:
                logging.warning("Video {0}: Video unavailable ({1})".format(id, url))
                continue
            except:
                logging.critical("Video {0}: An unexpected error occured ({1})".format(id, url))
                continue

            process_video(video, channel_dict, log_writer, language, group, include_audio, include_auto, convert_srt, include_titles, include_channels)

            if limit_to != -1 and video_count == resume_from + limit_to:
                print("Limit reached; halting")
                break

            # Be considerate!
            sleep(1)


def main(args):

    if not path.isfile(args.urls_in):
        logging.error("url_list must be a file")
        return 1

    if not path.exists(path.join("corpus", "logs")):
        makedirs(path.join("corpus", "logs"))

    if(args.resume):
        print("Resuming from video {0}".format(args.resume))

    process_videos(args.urls_in, args.language, args.group, args.audio, args.auto, args.srt, args.titles, args.channels, args.resume, args.limit)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Download available subtitles and audio from a list of YouTube video urls.')

    parser.add_argument('urls_in', type=str, help='path to a file containing the URLs to scrape')

    parser.add_argument('--language', '-l', default=None, type=str, help='filter captions by language name (e.g. "Korean"); if unspecified, all captions will be downloaded')
    parser.add_argument('--group',  '-n', default=None, metavar='NAME', type=str, help='a name for the group; if unspecified, channel names will be used')

    parser.add_argument('--auto',     '-a', action='store_true', default=False, help='include automatically-generated captions')
    parser.add_argument('--audio',    '-s', action='store_true', default=False, help='download audio')
    parser.add_argument('--titles',   '-t', action='store_true', default=False, help='include video titles in caption and audio filenames')
    parser.add_argument('--channels', '-c', action='store_true', default=False, help='organize captions and audio into folders by channel')
    parser.add_argument('--srt',            action='store_true', default=False, help='download captions in SRT format')

    parser.add_argument('--resume', '-res', type=int, metavar='N', nargs=1, default=0,  help='resume downloading from Nth video')
    parser.add_argument('--limit',  '-lim', type=int, metavar='N', nargs=1, default=-1, help='limit processing to N videos')

    args = parser.parse_args()

    main(args)
