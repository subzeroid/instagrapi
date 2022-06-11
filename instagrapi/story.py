import tempfile
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from .types import StoryBuild, StoryMention, StorySticker

try:
    from moviepy.editor import CompositeVideoClip, ImageClip, TextClip, VideoFileClip
except ImportError:
    raise Exception("Please install moviepy==1.0.3 and retry")

try:
    from PIL import Image
except ImportError:
    raise Exception("You don't have PIL installed. Please install PIL or Pillow>=8.1.1")


class StoryBuilder:
    """
    Helpers for Story building
    """

    width = 720
    height = 1280

    def __init__(
        self,
        path: Path,
        caption: str = "",
        mentions: List[StoryMention] = [],
        bgpath: Path = None,
    ):
        """
        Initialization function

        Parameters
        ----------
        path: Path
            Path for a file
        caption: str, optional
            Media caption, default value is ""
        mentions: List[StoryMention], optional
            List of mentions to be tagged on this upload, default is empty list
        bgpath: Path
            Path for a background image, default value is ""

        Returns
        -------
        Void
        """
        self.path = Path(path)
        self.caption = caption
        self.mentions = mentions
        self.bgpath = Path(bgpath) if bgpath else None

    def build_main(self, clip, max_duration: int = 0, font: str = 'Arial', fontsize: int = 100, color: str = 'white', link: str = "") -> StoryBuild:
        """
        Build clip

        Parameters
        ----------
        clip: (VideoFileClip, ImageClip)
            An object of either VideoFileClip or ImageClip
        max_duration: int, optional
            Duration of the clip if a video clip, default value is 0
        font: str, optional
            Name of font for text clip
        fontsize: int, optional
            Size of font
        color: str, optional
            Color of text

        Returns
        -------
        StoryBuild
            An object of StoryBuild
        """
        clips = []
        stickers = []
        # Background
        if self.bgpath:
            assert self.bgpath.exists(), f"Wrong path to background {self.bgpath}"
            background = ImageClip(str(self.bgpath))
            clips.append(background)
        # Media clip
        clip_left = (self.width - clip.size[0]) / 2
        clip_top = (self.height - clip.size[1]) / 2
        if clip_top > 90:
            clip_top -= 50
        media_clip = clip.set_position((clip_left, clip_top))
        clips.append(media_clip)
        mention = self.mentions[0] if self.mentions else None
        # Text clip
        caption = self.caption
        if self.mentions:
            mention = self.mentions[0]
            if getattr(mention, 'user', None):
                caption = f"@{mention.user.username}"
        if caption:
            text_clip = TextClip(
                caption,
                color=color,
                font=font,
                kerning=-1,
                fontsize=fontsize,
                method="label",
            )
            text_clip_left = (self.width - 600) / 2
            text_clip_top = clip_top + clip.size[1] + 50
            offset = (text_clip_top + text_clip.size[1]) - self.height
            if offset > 0:
                text_clip_top -= offset + 90
            text_clip = (
                text_clip.resize(width=600)
                .set_position((text_clip_left, text_clip_top))
                .fadein(3)
            )
            clips.append(text_clip)
        if link:
            url = urlparse(link)
            link_clip = TextClip(
                url.netloc,
                color="blue",
                bg_color="white",
                font=font,
                kerning=-1,
                fontsize=32,
                method="label",
            )
            link_clip_left = (self.width - 400) / 2
            link_clip_top = clip.size[1] / 2
            link_clip = (
                link_clip.resize(width=400)
                .set_position((link_clip_left, link_clip_top))
                .fadein(3)
            )
            link_sticker = StorySticker(
                # x=160.0, y=641.0, z=0, width=400.0, height=88.0,
                x=round(link_clip_left / self.width, 7),  # e.g. 0.49953705
                y=round(link_clip_top / self.height, 7),  # e.g. 0.5
                z=0,
                width=round(link_clip.size[0] / self.width, 7),  # e.g. 0.50912
                height=round(link_clip.size[1] / self.height, 7),  # e.g. 0.06875
                rotation=0.0,
                # id="link_sticker_default",
                type="story_link",
                extra=dict(
                    link_type="web",
                    url=str(link),  # e.g. "https//github.com/"
                    tap_state_str_id="link_sticker_default",
                )
            )
            stickers.append(link_sticker)
            clips.append(link_clip)
        # Mentions
        mentions = []
        if mention:
            mention.x = 0.49892962  # approximately center
            mention.y = (text_clip_top + text_clip.size[1] / 2) / self.height
            mention.width = text_clip.size[0] / self.width
            mention.height = text_clip.size[1] / self.height
            mentions = [mention]
        duration = max_duration
        if getattr(clip, 'duration', None):
            if duration > int(clip.duration) or not duration:
                duration = int(clip.duration)
        destination = tempfile.mktemp(".mp4")
        cvc = CompositeVideoClip(clips, size=(self.width, self.height))\
            .set_fps(24)\
            .set_duration(duration)
        cvc.write_videofile(destination, codec="libx264", audio=True, audio_codec="aac")
        paths = []
        if duration > 15:
            for i in range(duration // 15 + (1 if duration % 15 else 0)):
                path = tempfile.mktemp(".mp4")
                start = i * 15
                rest = duration - start
                end = start + (rest if rest < 15 else 15)
                sub = cvc.subclip(start, end)
                sub.write_videofile(path, codec="libx264", audio=True, audio_codec="aac")
                paths.append(path)
        return StoryBuild(mentions=mentions, path=destination, paths=paths, stickers=stickers)

    def video(self, max_duration: int = 0, font: str = 'Arial', fontsize: int = 100, color: str = 'white', link: str = ''):
        """
        Build CompositeVideoClip from source video

        Parameters
        ----------
        max_duration: int, optional
            Duration of the clip if a video clip, default value is 0
        font: str, optional
            Name of font for text clip
        fontsize: int, optional
            Size of font
        color: str, optional
            Color of text

        Returns
        -------
        StoryBuild
            An object of StoryBuild
        """
        clip = VideoFileClip(str(self.path), has_mask=True)
        build = self.build_main(clip, max_duration, font, fontsize, color, link)
        clip.close()
        return build

    def photo(self, max_duration: int = 0, font: str = 'Arial', fontsize: int = 100, color: str = 'white', link: str = ''):
        """
        Build CompositeVideoClip from source video

        Parameters
        ----------
        max_duration: int, optional
            Duration of the clip if a video clip, default value is 0
        font: str, optional
            Name of font for text clip
        fontsize: int, optional
            Size of font
        color: str, optional
            Color of text

        Returns
        -------
        StoryBuild
            An object of StoryBuild
        """

        with Image.open(self.path) as im:
            image_width, image_height = im.size

        width_reduction_percent = (self.width / float(image_width))
        height_in_ratio = int((float(image_height) * float(width_reduction_percent)))

        clip = ImageClip(str(self.path)).resize(width=self.width, height=height_in_ratio)
        return self.build_main(clip, max_duration or 15, font, fontsize, color, link)
