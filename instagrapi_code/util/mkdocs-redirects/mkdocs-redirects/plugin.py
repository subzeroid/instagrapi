import logging
import os
import textwrap
from urllib.parse import urlparse

from mkdocs import utils
from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin

log = logging.getLogger('mkdocs.plugin.redirects')
log.addFilter(utils.warning_filter)


def write_html(site_dir, old_path, new_path):
    """ Write an HTML file in the site_dir with a meta redirect to the new page """
    # Determine all relevant paths
    old_path_abs = os.path.join(site_dir, old_path)
    old_dir = os.path.dirname(old_path)
    old_dir_abs = os.path.dirname(old_path_abs)

    # Create parent directories if they don't exist
    if not os.path.exists(old_dir_abs):
        log.debug("Creating directory '%s'", old_dir)
        os.makedirs(old_dir_abs)

    # Write the HTML redirect file in place of the old file
    with open(old_path_abs, 'w') as f:
        log.debug("Creating redirect: '%s' -> '%s'",
                  old_path, new_path)
        f.write(textwrap.dedent(
            """
            <!doctype html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <title>Redirecting...</title>
                <link rel="canonical" href="{url}">
                <meta name="robots" content="noindex">
                <script>var anchor=window.location.hash.substr(1);location.href="{url}"+(anchor?"#"+anchor:"")</script>
                <meta http-equiv="refresh" content="0; url={url}">
            </head>
            <body>
            Redirecting...
            </body>
            </html>
            """
        ).format(url=new_path))


def get_relative_html_path(old_page, new_page, use_directory_urls):
    """ Return the relative path from the old html path to the new html path"""
    old_path = get_html_path(old_page, use_directory_urls)
    new_path = get_html_path(new_page, use_directory_urls)

    if use_directory_urls:
        # remove /index.html from end of path
        new_path = os.path.dirname(new_path)

    relative_path = os.path.relpath(new_path, start=os.path.dirname(old_path))

    if use_directory_urls:
        relative_path = relative_path + '/'

    return relative_path


def get_html_path(path, use_directory_urls):
    """ Return the HTML file path for a given markdown file """
    parent, filename = os.path.split(path)
    name_orig, ext = os.path.splitext(filename)

    # Directory URLs require some different logic. This mirrors mkdocs' internal logic.
    if use_directory_urls:

        # Both `index.md` and `README.md` files are normalized to `index.html` during build
        name = 'index' if name_orig.lower() in ('index', 'readme') else name_orig

        # If it's name is `index`, then that means it's the "homepage" of a directory, so should get placed in that dir
        if name == 'index':
            return os.path.join(parent, 'index.html')

        # Otherwise, it's a file within that folder, so it should go in its own directory to resolve properly
        else:
            return os.path.join(parent, name, 'index.html')

    # Just use the original name if Directory URLs aren't used
    else:
        return os.path.join(parent, (name_orig + '.html'))


class RedirectPlugin(BasePlugin):
    # Any options that this plugin supplies should go here.
    config_scheme = (
        ('redirect_maps', config_options.Type(dict, default={})),  # note the trailing comma
    )

    # Build a list of redirects on file generation
    def on_files(self, files, config, **kwargs):
        self.redirects = self.config.get('redirect_maps', {})

        # SHIM! Produce a warning if the old root-level 'redirects' config is present
        if config.get('redirects'):
            log.warn("The root-level 'redirects:' setting is not valid and has been changed in version 1.0! "
                     "The plugin-level 'redirect-map' must be used instead. See https://git.io/fjdBN")

        # Validate user-provided redirect "old files"
        for page_old in self.redirects.keys():
            if not utils.is_markdown_file(page_old):
                log.warn("redirects plugin: '%s' is not a valid markdown file!", page_old)

        # Build a dict of known document pages to validate against later
        self.doc_pages = {}
        for page in files.documentation_pages():  # object type: mkdocs.structure.files.File
            self.doc_pages[page.src_path.replace('\\', '/')] = page

    # Create HTML files for redirects after site dir has been built
    def on_post_build(self, config, **kwargs):

        # Determine if 'use_directory_urls' is set
        use_directory_urls = config.get('use_directory_urls')

        # Walk through the redirect map and write their HTML files
        for page_old, page_new in self.redirects.items():

            # External redirect targets are easy, just use it as the target path
            if page_new.lower().startswith(('http://', 'https://')):
                dest_path = page_new

            elif page_new in self.doc_pages:
                dest_path = get_relative_html_path(page_old, page_new, use_directory_urls)

            # If the redirect target isn't external or a valid internal page, throw an error
            # Note: we use 'warn' here specifically; mkdocs treats warnings specially when in strict mode
            else:
                log.warn("Redirect target '%s' does not exist!", page_new)
                continue

            # DO IT!
            write_html(config['site_dir'],
                       get_html_path(page_old, use_directory_urls),
                       dest_path)
