SIG_KEY_VERSION = "4"
IG_SIG_KEY = "a86109795736d73c9a94172cd9b736917d7d94ca61c9101164894b3f0d43bef4"
API_DOMAIN = "i.instagram.com"

# Instagram 134.0.0.26.121
# Android (26/8.0.0;
# 480dpi; 1080x1920; Xiaomi;
# MI 5s; capricorn; qcom; en_US; 205280538)
USER_AGENT_BASE = (
    "Instagram {app_version} "
    "Android ({android_version}/{android_release}; "
    "{dpi}; {resolution}; {manufacturer}; "
    "{device}; {model}; {cpu}; {locale}; {version_code})"
)
SOFTWARE = "{model}-user+{android_release}+OPR1.170623.012+V10.2.7.0.OAGMIXM+release-keys"


LOGIN_EXPERIMENTS = "ig_android_reg_nux_headers_cleanup_universe,ig_android_device_detection_info_upload,ig_android_nux_add_email_device,ig_android_gmail_oauth_in_reg,ig_android_device_info_foreground_reporting,ig_android_device_verification_fb_signup,ig_android_direct_main_tab_universe_v2,ig_android_passwordless_account_password_creation_universe,ig_android_direct_add_direct_to_android_native_photo_share_sheet,ig_growth_android_profile_pic_prefill_with_fb_pic_2,ig_account_identity_logged_out_signals_global_holdout_universe,ig_android_quickcapture_keep_screen_on,ig_android_device_based_country_verification,ig_android_login_identifier_fuzzy_match,ig_android_reg_modularization_universe,ig_android_security_intent_switchoff,ig_android_device_verification_separate_endpoint,ig_android_suma_landing_page,ig_android_sim_info_upload,ig_android_smartlock_hints_universe,ig_android_fb_account_linking_sampling_freq_universe,ig_android_retry_create_account_universe,ig_android_caption_typeahead_fix_on_o_universe"

SUPPORTED_CAPABILITIES = [
    {
        "name": "SUPPORTED_SDK_VERSIONS",
        "value": "80.0,81.0,82.0,83.0,84.0,85.0,86.0,87.0,88.0,89.0,90.0,91.0,92.0,93.0,94.0,95.0,96.0,97.0,98.0,99.0,100.0,101.0,102.0,103.0,104.0,105.0,106.0,107.0,108.0,109.0,110.0,111.0"
    },
    {"name": "FACE_TRACKER_VERSION", "value": "14"},
    {"name": "segmentation", "value": "segmentation_enabled"},
    {"name": "COMPRESSION", "value": "ETC2_COMPRESSION"},
    {"name": "world_tracker", "value": "world_tracker_enabled"},
    {"name": "gyroscope", "value": "gyroscope_enabled"}
]
