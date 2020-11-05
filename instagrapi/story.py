import tempfile
from pathlib import Path
from typing import List

from moviepy.editor import TextClip, CompositeVideoClip, VideoFileClip, ImageClip

from .types import StoryBuild, StoryMention


class StoryBuilder:
    width = 720
    height = 1280

    def __init__(self, path: Path, caption: str = "", mentions: List[StoryMention] = [], bgpath: Path = ""):
        """Init params
        :path: path to cource video or photo file
        :caption: text caption for story
        :mentions: list of StoryMention (see types.py)
        :bgpath: path to background image (recommend jpg and 720x1280)
        """
        self.path = Path(path)
        self.caption = caption
        self.mentions = mentions
        self.bgpath = Path(bgpath)

    def build_main(self, clip, max_duration: int = 0) -> StoryBuild:
        """Build clip
        :clip: Clip object (VideoFileClip, ImageClip)
        :max_duration: Result duration in seconds
        :return: StoryBuild (with new path and mentions)
        """
        clips = []
        # Background
        if self.bgpath:
            assert self.bgpath.exists(),\
                f'Wrong path to background {self.bgpath}'
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
        caption = "@%s" % mention.user.username if mention.user.username else self.caption
        text_clip = TextClip(
            caption, color="white", font="Arial",
            kerning=-1, fontsize=100, method="label"
        )
        text_clip_left = (self.width - 600) / 2
        text_clip_top = clip_top + clip.size[1] + 50
        offset = (text_clip_top + text_clip.size[1]) - self.height
        if offset > 0:
            text_clip_top -= offset + 90
        text_clip = text_clip.resize(width=600).set_position(
            (text_clip_left, text_clip_top)).fadein(3)
        clips.append(text_clip)
        # Mentions
        mentions = []
        if mention:
            mention.x = 0.49892962  # approximately center
            mention.y = (text_clip_top + text_clip.size[1] / 2) / self.height
            mention.width = text_clip.size[0] / self.width
            mention.height = text_clip.size[1] / self.height
            mentions = [mention]
        duration = max_duration
        if max_duration and clip.duration and max_duration > clip.duration:
            duration = clip.duration
        destination = tempfile.mktemp('.mp4')
        CompositeVideoClip(clips, size=(self.width, self.height))\
            .set_fps(24)\
            .set_duration(duration)\
            .write_videofile(destination, codec='libx264', audio=True, audio_codec='aac')
        return StoryBuild(mentions=mentions, path=destination)

    def video(self, max_duration: int = 0):
        """Build CompositeVideoClip from source video
        :max_duration: Result duration in seconds
        """
        clip = VideoFileClip(str(self.path), has_mask=True)
        return self.build_main(clip, max_duration)

    def photo(self, max_duration: int = 0):
        """Build CompositeVideoClip from source photo
        :max_duration: Result duration in seconds
        """
        clip = ImageClip(str(self.path)).resize(width=self.width)
        return self.build_main(clip, max_duration or 15)
