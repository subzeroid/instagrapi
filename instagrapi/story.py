import os
import tempfile

from moviepy.editor import TextClip, CompositeVideoClip, VideoFileClip, ImageClip

from .types import StoryBuild, StoryMention


class StoryBuilder:
    width = 720
    height = 1280

    def __init__(self, filepath: str, caption: str = "", usertags: list = [], bgpath: str = ""):
        """Init params
        :filepath: path to cource video or photo file
        :caption: text caption for story
        :usertags: list of dicts with tags of users
        :bgpath: path to background image (recommend jpg and 720x1280)
        """
        self.filepath = filepath
        self.caption = caption
        self.usertags = usertags
        self.bgpath = bgpath
        if bgpath:
            assert os.path.exists(bgpath), 'Wrong path to background'

    def build_clip(self, clip, max_duration: int = 0) -> dict:
        """Build clip
        :clip: Clip object (VideoFileClip, ImageClip)
        :max_duration: Result duration in seconds
        :return: Dict with new filepath, usertags and more
        """
        background = ImageClip(self.bgpath)
        clip_left = (self.width - clip.size[0]) / 2
        clip_top = (self.height - clip.size[1]) / 2
        if clip_top > 90:
            clip_top -= 50
        clip = clip.set_position((clip_left, clip_top))
        caption = self.caption
        tag = None
        if self.usertags:
            tag = self.usertags[0]
            caption = "@%s" % tag["user"]["name"]
        text_clip = TextClip(caption, color="white", font="Arial",
                             kerning=-1, fontsize=100, method="label")
        text_clip_left = (self.width - 600) / 2
        text_clip_top = clip_top + clip.size[1] + 50
        offset = (text_clip_top + text_clip.size[1]) - self.height
        if offset > 0:
            text_clip_top -= offset + 90
        text_clip = text_clip.resize(width=600).set_position(
            (text_clip_left, text_clip_top)).fadein(3)
        mentions = []
        if tag:
            mention = StoryMention(
                x=0.49892962,  # approximately center
                y=(text_clip_top + text_clip.size[1] / 2) / self.height,
                width=text_clip.size[0] / self.width,
                height=text_clip.size[1] / self.height
            )
            mentions = [mention]
        duration = max_duration
        if max_duration and clip.duration and max_duration > clip.duration:
            duration = clip.duration
        destination = tempfile.mktemp('.mp4')
        CompositeVideoClip(
            [background, clip, text_clip], size=(self.width, self.height)
        ).set_fps(24).set_duration(duration).write_videofile(destination, codec='libx264', audio=True, audio_codec='aac')
        return StoryBuild(
            mentions=mentions,
            path=destination
        )

    def video(self, max_duration: int = 0):
        """Build CompositeVideoClip from source video
        :max_duration: Result duration in seconds
        """
        clip = VideoFileClip(self.filepath, has_mask=True)
        return self.build_clip(clip, max_duration)

    def photo(self, max_duration: int = 0):
        """Build CompositeVideoClip from source photo
        :max_duration: Result duration in seconds
        """
        clip = ImageClip(self.filepath).resize(width=self.width)
        return self.build_clip(clip, max_duration or 14)
