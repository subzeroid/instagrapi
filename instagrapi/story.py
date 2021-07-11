import tempfile
from pathlib import Path
from typing import List

from .types import StoryBuild, StoryMention

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

    def build_main(self, clip, max_duration: int = 0) -> StoryBuild:
        """
        Build clip

        Parameters
        ----------
        clip: (VideoFileClip, ImageClip)
            An object of either VideoFileClip or ImageClip
        max_duration: int, optional
            Duration of the clip if a video clip, default value is 0

        Returns
        -------
        StoryBuild
            An object of StoryBuild
        """
        clips = []
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
                color="white",
                font="Arial",
                kerning=-1,
                fontsize=100,
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
        destination = tempfile.mktemp(".mp4")
        CompositeVideoClip(clips, size=(self.width, self.height)).set_fps(
            24
        ).set_duration(duration).write_videofile(
            destination, codec="libx264", audio=True, audio_codec="aac"
        )
        return StoryBuild(mentions=mentions, path=destination)

    def video(self, max_duration: int = 0):
        """
        Build CompositeVideoClip from source video

        Parameters
        ----------
        max_duration: int, optional
            Duration of the clip if a video clip, default value is 0

        Returns
        -------
        StoryBuild
            An object of StoryBuild
        """
        clip = VideoFileClip(str(self.path), has_mask=True)
        return self.build_main(clip, max_duration)

    def photo(self, max_duration: int = 0):
        """
        Build CompositeVideoClip from source video

        Parameters
        ----------
        max_duration: int, optional
            Duration of the clip if a video clip, default value is 0

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
        return self.build_main(clip, max_duration or 15)
