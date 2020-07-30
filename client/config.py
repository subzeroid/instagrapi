SIG_KEY_VERSION = "4"
IG_SIG_KEY = "a86109795736d73c9a94172cd9b736917d7d94ca61c9101164894b3f0d43bef4"

API_DOMAIN = "i.instagram.com"
API_URL = "https://{domain}/api/v1/".format(domain=API_DOMAIN)

# Instagram 134.0.0.26.121
# Android (26/8.0.0;
# 480dpi; 1080x1920; Xiaomi;
# MI 5s; capricorn; qcom; en_US; 205280538)
USER_AGENT_BASE = (
    "Instagram {app_version} "
    "Android ({android_version}/{android_release}; "
    "{dpi}; {resolution}; {manufacturer}; "
    "{device}; {model}; {cpu}; en_US; {version_code})"
)


LOGIN_EXPERIMENTS = "ig_android_fci_onboarding_friend_search,ig_android_device_detection_info_upload,ig_android_account_linking_upsell_universe,ig_android_direct_main_tab_universe_v2,ig_android_sign_in_help_only_one_account_family_universe,ig_android_sms_retriever_backtest_universe,ig_android_direct_add_direct_to_android_native_photo_share_sheet,ig_android_spatial_account_switch_universe,ig_growth_android_profile_pic_prefill_with_fb_pic_2,ig_account_identity_logged_out_signals_global_holdout_universe,ig_android_prefill_main_account_username_on_login_screen_universe,ig_android_login_identifier_fuzzy_match,ig_android_mas_remove_close_friends_entrypoint,ig_android_shared_email_reg_universe,ig_android_video_render_codec_low_memory_gc,ig_android_custom_transitions_universe,ig_android_push_fcm,multiple_account_recovery_universe,ig_android_show_login_info_reminder_universe,ig_android_email_fuzzy_matching_universe,ig_android_one_tap_aymh_redesign_universe,ig_android_direct_send_like_from_notification,ig_android_suma_landing_page,ig_android_prefetch_debug_dialog,ig_android_smartlock_hints_universe,ig_android_black_out,ig_activation_global_discretionary_sms_holdout,ig_android_video_ffmpegutil_pts_fix,ig_android_multi_tap_login_new,ig_save_smartlock_universe,ig_android_caption_typeahead_fix_on_o_universe,ig_android_enable_keyboardlistener_redesign,ig_android_nux_add_email_device,ig_android_direct_remove_view_mode_stickiness_universe,ig_android_hide_contacts_list_in_nux,ig_android_new_users_one_tap_holdout_universe,ig_android_ingestion_video_support_hevc_decoding,ig_android_mas_notification_badging_universe,ig_android_secondary_account_in_main_reg_flow_universe,ig_android_secondary_account_creation_universe,ig_android_account_recovery_auto_login,ig_android_pwd_encrytpion,ig_android_bottom_sheet_keyboard_leaks,ig_android_sim_info_upload,ig_android_shorten_sac_for_one_eligible_main_account_universe,ig_android_mobile_http_flow_device_universe,ig_android_hide_fb_button_when_not_installed_universe,ig_android_targeted_one_tap_upsell_universe,ig_android_gmail_oauth_in_reg,ig_android_vc_interop_use_test_igid_universe,ig_android_notification_unpack_universe,ig_android_quickcapture_keep_screen_on,ig_android_registration_confirmation_code_universe,ig_android_device_based_country_verification,ig_android_log_suggested_users_cache_on_error,ig_android_reg_modularization_universe,ig_android_device_verification_separate_endpoint,ig_android_universe_noticiation_channels,ig_android_account_linking_universe,ig_android_hsite_prefill_new_carrier,ig_android_one_login_toast_universe,ig_android_retry_create_account_universe,ig_android_family_apps_user_values_provider_universe,ig_android_reg_nux_headers_cleanup_universe,ig_android_get_cookie_with_concurrent_session_universe,ig_android_device_info_foreground_reporting,ig_android_shortcuts_2019,ig_android_device_verification_fb_signup,ig_android_onetaplogin_optimization,ig_android_passwordless_account_password_creation_universe,ig_android_black_out_toggle_universe,ig_video_debug_overlay,ig_android_ask_for_permissions_on_reg,ig_assisted_login_universe,ig_android_security_intent_switchoff,ig_android_device_info_job_based_reporting,ig_android_add_account_button_in_profile_mas_universe,ig_android_passwordless_auth,ig_android_direct_main_tab_account_switch,ig_android_recovery_one_tap_holdout_universe,ig_android_modularized_dynamic_nux_universe,ig_android_sac_follow_from_other_accounts_nux_universe,ig_android_fb_account_linking_sampling_freq_universe,ig_android_fix_sms_read_lollipop,ig_android_access_flow_prefill"

SUPPORTED_CAPABILITIES = [
    {
        "name": "SUPPORTED_SDK_VERSIONS",
        "value": "45.0,46.0,47.0,48.0,49.0,50.0,51.0,52.0,53.0,54.0,55.0,56.0,57.0,58.0,59.0,60.0,61.0,62.0,63.0,64.0,65.0,66.0,67.0,68.0,69.0,70.0,71.0,72.0,73.0,74.0,75.0,76.0,77.0,78.0,79.0,80.0,81.0",
    },
    {"name": "FACE_TRACKER_VERSION", "value": "14"},
    {"name": "COMPRESSION", "value": "ETC2_COMPRESSION"},
    {"name": "world_tracker", "value": "world_tracker_enabled"},
    {"name": "segmentation", "value": "segmentation_enabled"},
    {"name": "gyroscope", "value": "gyroscope_enabled"},
]
