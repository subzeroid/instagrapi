import os
import tempfile

from moviepy.editor import TextClip, CompositeVideoClip, VideoFileClip, ImageClip
from PIL import Image, ImageFont, ImageDraw


class StoryBuilder:
    width = 720
    height = 1280

    def __init__(self, filepath: str, caption: str = "", usertags: list = [], bgpath: str = ""):
        self.filepath = filepath
        self.caption = caption
        self.usertags = usertags
        self.bgpath = bgpath
        if bgpath:
            assert os.path.exists(bgpath), 'Wrong path to background'

    def build_clip(self, clip, max_duration):
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
        text_clip = TextClip(caption, color="white", font="Arial", kerning=-1, fontsize=100, method="label")
        text_clip_left = (self.width - 600) / 2
        text_clip_top = clip_top + clip.size[1] + 50
        offset = (text_clip_top + text_clip.size[1]) - self.height
        if offset > 0:
            text_clip_top -= offset + 90
        text_clip = text_clip.resize(width=600).set_position((text_clip_left, text_clip_top)).fadein(3)
        usertags = []
        if tag:
            tag['x'] = 0.49892962  # approximately center
            tag['y'] = (text_clip_top + text_clip.size[1] / 2) / self.height
            tag['width'] = text_clip.size[0] / self.width
            tag['height'] = text_clip.size[1] / self.height
            usertags = [tag]
        duration = max_duration
        if max_duration and clip.duration and max_duration > clip.duration:
            duration = clip.duration
        destination = tempfile.mktemp('.mp4')
        CompositeVideoClip(
            [background, clip, text_clip], size=(self.width, self.height)
        ).set_fps(24).set_duration(duration).write_videofile(destination, codec='libx264', audio=True, audio_codec='aac')
        return {
            'usertags': usertags,
            'filepath': destination
        }

    def video(self, max_duration: int = 0):
        clip = VideoFileClip(self.filepath, has_mask=True)
        return self.build_clip(clip, max_duration)

    def photo(self, max_duration: int = 0):
        clip = ImageClip(self.filepath).resize(width=self.width)
        return self.build_clip(clip, max_duration or 14)

    def photo_pil(self):
        """Unfinished
        """
        background = Image.open(self.bgpath)
        txt = Image.new('RGBA', background.size, (255, 255, 255, 0))
        fnt = ImageFont.load_default()
        caption = self.caption
        tag = None
        if self.usertags:
            tag = self.usertags[0]
            caption = "@%s" % tag["user"]["name"]
        draw = ImageDraw.Draw(txt)
        draw.text((360, 640), caption, font=fnt, fill=(255, 255, 255, 128))
        out = Image.alpha_composite(background, txt)
        destination = tempfile.mktemp('.jpg')
        # out.show()
        out.convert('RGB').save(open(destination, 'w'))
        return {
            'usertags': self.usertags,
            'filepath': destination
        }
