API_DOMAIN = "i.instagram.com"

# Instagram 134.0.0.26.121
# Android (26/8.0.0;
# 480dpi; 1080x1920; Xiaomi;
# MI 5s; capricorn; qcom; en_US; 205280538)
USER_AGENT_BASE = (
    "Instagram {app_version} "
    "Android ({android_version}/{android_release}; "
    "{dpi}; {resolution}; {manufacturer}; "
    "{model}; {device}; {cpu}; {locale}; {version_code})"
)
# Instagram 76.0.0.15.395 (iPhone9,2; iOS 10_0_2; en_US; en-US; scale=2.61; 1080x1920) AppleWebKit/420+
# Instagram 208.0.0.32.135 (iPhone; iOS 14_7_1; en_US; en-US; scale=2.61; 1080x1920) AppleWebKit/605.1.15

SOFTWARE = "{model}-user+{android_release}+OPR1.170623.032+V10.2.3.0.OAGMIXM+release-keys"

# QUERY_HASH_PROFILE = 'c9100bf9110dd6361671f113dd02e7d6'
# QUERY_HASH_MEDIAS = '42323d64886122307be10013ad2dcc44'
# QUERY_HASH_IGTVS = 'bc78b344a68ed16dd5d7f264681c4c76'
# QUERY_HASH_STORIES = '5ec1d322b38839230f8e256e1f638d5f'
# QUERY_HASH_HIGHLIGHTS_FOLDERS = 'ad99dd9d3646cc3c0dda65debcd266a7'
# QUERY_HASH_HIGHLIGHTS_STORIES = '5ec1d322b38839230f8e256e1f638d5f'
# QUERY_HASH_FOLLOWERS = 'c76146de99bb02f6415203be841dd25a'
# QUERY_HASH_FOLLOWINGS = 'd04b0a864b4b54837c0d870b0e77e076'
# QUERY_HASH_HASHTAG = '174a5243287c5f3a7de741089750ab3b'
# QUERY_HASH_COMMENTS = '33ba35852cb50da46f5b5e889df7d159'
# QUERY_HASH_TAGGED_MEDIAS = 'be13233562af2d229b008d2976b998b5'

LOGIN_EXPERIMENTS = "ig_android_reg_nux_headers_cleanup_universe,ig_android_device_detection_info_upload,ig_android_nux_add_email_device,ig_android_gmail_oauth_in_reg,ig_android_device_info_foreground_reporting,ig_android_device_verification_fb_signup,ig_android_direct_main_tab_universe_v2,ig_android_passwordless_account_password_creation_universe,ig_android_direct_add_direct_to_android_native_photo_share_sheet,ig_growth_android_profile_pic_prefill_with_fb_pic_2,ig_account_identity_logged_out_signals_global_holdout_universe,ig_android_quickcapture_keep_screen_on,ig_android_device_based_country_verification,ig_android_login_identifier_fuzzy_match,ig_android_reg_modularization_universe,ig_android_security_intent_switchoff,ig_android_device_verification_separate_endpoint,ig_android_suma_landing_page,ig_android_sim_info_upload,ig_android_smartlock_hints_universe,ig_android_fb_account_linking_sampling_freq_universe,ig_android_retry_create_account_universe,ig_android_caption_typeahead_fix_on_o_universe"

SUPPORTED_CAPABILITIES = [
    {
        "name":
            "SUPPORTED_SDK_VERSIONS",
        "value":
            "108.0,109.0,110.0,111.0,112.0,113.0,114.0,115.0,116.0,117.0,118.0,119.0,120.0,121.0,122.0,123.0,124.0,125.0,126.0,127.0"
    }, {
        "name": "FACE_TRACKER_VERSION",
        "value": "14"
    }, {
        "name": "segmentation",
        "value": "segmentation_enabled"
    }, {
        "name": "COMPRESSION",
        "value": "ETC2_COMPRESSION"
    }, {
        "name": "world_tracker",
        "value": "world_tracker_enabled"
    }, {
        "name": "gyroscope",
        "value": "gyroscope_enabled"
    }
]

# List of query hashes for reference

QUERY_HASH_HASHTAG_BY_NAME = "f92f56d47dc7a55b606908374b43a314"

QUERY_HASH_MEDIA_BY_SHORTCODE = "477b65a610463740ccdb83135b2014db"
QUERY_HASH_USERTAG_MEDIAS_BY_ID = "be13233562af2d229b008d2976b998b5"

QUERY_HASH_USER_BY_ID = "e7e2f4da4b02303f74f0841279e52d76"
QUERY_HASH_USER_SHORT_BY_ID = "ad99dd9d3646cc3c0dda65debcd266a7"
QUERY_HASH_USER_FOLLOWERS_BY_ID = "5aefa9893005572d237da5068082d8d5"

QUERY_HASH_PUBLIC_LOCATION_BY_ID = "1b84447a4d8b6d6d0426fefb34514485"
QUERY_HASH_PUBLIC_USER_BY_ID = "e74d51c10ecc0fe6250a295b9bb9db74"

QUERY_HASH_USER_STORIES_BY_ID = "303a4ae99711322310f25250d988f3b7"

# List of doc IDs that can potentially be used

DOC_ID_MEDIA_BY_SHORTCODE = "8845758582119845"
DOC_ID_MEDIA_BY_SHORTCODE_2 = "10015901848480474"
DOC_ID_USER_POSTS_BY_NAME = "9310670392322965"
DOC_ID_USER_POSTS_BY_NAME_2 = "9066276850131169"
DOC_ID_USER_POSTS_BY_NAME_3 = "7898261790222653"
DOC_ID_USER_REELS_BY_ID = "7845543455542541"
