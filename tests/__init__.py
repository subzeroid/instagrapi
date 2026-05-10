from tests.live.test_account import ClientAccountTestCase
from tests.live.test_client import ClientTestCase
from tests.live.test_collection import ClientCollectionTestCase
from tests.live.test_comments import (
    ClientCommentExtendTestCase,
    ClientCommentRepliesLiveTestCase,
    ClientCommentTestCase,
)
from tests.live.test_cutout_sticker import ClientCutoutStickerTestCase
from tests.live.test_device import ClientDeviceAgentTestCase, ClientDeviceTestCase
from tests.live.test_direct import (
    ClientDirectMediaLiveTestCase,
    ClientDirectMessageTypesTestCase,
    ClientDirectTestCase,
    ClientDirectThreadLiveTestCase,
)
from tests.live.test_hashtag import ClientHashtagTestCase
from tests.live.test_highlight import ClientHighlightTestCase
from tests.live.test_location import ClientLocationTestCase
from tests.live.test_media import (
    ClientCompareExtractTestCase,
    ClientExtractTestCase,
    ClientMediaExtendTestCase,
    ClientMediaTestCase,
)
from tests.live.test_notes import ClientNoteLiveTestCase
from tests.live.test_public import ClientPublicTestCase
from tests.live.test_share import ClientShareTestCase
from tests.live.test_signup import SignUpTestCase
from tests.live.test_story import ClientStoryTestCase
from tests.live.test_timeline import ClientTimelineLiveTestCase
from tests.live.test_totp import TOTPTestCase
from tests.live.test_upload import ClientFeedMusicUploadLiveTestCase, ClienUploadTestCase
from tests.live.test_user import (
    ClientFollowRequestLiveTestCase,
    ClientUserExtendTestCase,
    ClientUserTestCase,
)
from tests.regression.test_auth_story import AuthAndStoryRegressionTestCase
from tests.regression.test_challenge import ChallengeRegressionTestCase
from tests.regression.test_comments import CommentRepliesRegressionTestCase
from tests.regression.test_direct import DirectMixinRegressionTestCase
from tests.regression.test_download import DownloadRegressionTestCase
from tests.regression.test_extractors import (
    DirectExtractorRegressionTestCase,
    ExtractorsRegressionTestCase,
)
from tests.regression.test_fbsearch import FbSearchRegressionTestCase
from tests.regression.test_hardening import HardeningRegressionTestCase
from tests.regression.test_location import LocationMixinRegressionTestCase
from tests.regression.test_media import (
    CheckOffensiveCommentV2RegressionTestCase,
    MediaInfoV2RegressionTestCase,
)
from tests.regression.test_notes import NoteMixinRegressionTestCase
from tests.regression.test_public import (
    PrivateGraphQLRequestRegressionTestCase,
    PublicRegressionTestCase,
)
from tests.regression.test_signup import PasswordEncryptionRegressionTestCase
from tests.regression.test_story_configure import StoryConfigureRegressionTestCase
from tests.regression.test_tempfile import TempfileHelperRegressionTestCase
from tests.regression.test_timeline import TimelineRegressionTestCase
from tests.regression.test_track import TrackMixinRegressionTestCase
from tests.regression.test_upload import UploadRegressionTestCase
from tests.regression.test_user import UserMixinRegressionTestCase
