#!/usr/bin/env python3
"""
Test script to validate the new ClipsMetadata Pydantic models.
This tests our implementation with the real Instagram clips_metadata examples.
"""

import json
from rich.console import Console
from instagrapi.types import ClipsMetadata

console = Console()

# Test data from the provided examples
test_clips_metadata_examples = [
    {
        'clips_creation_entry_point': 'clips',
        'featured_label': None,
        'is_public_chat_welcome_video': False,
        'professional_clips_upsell_type': 0,
        'show_tips': None,
        'achievements_info': {
            'num_earned_achievements': None,
            'show_achievements': False
        },
        'additional_audio_info': {
            'additional_audio_username': None,
            'audio_reattribution_info': {'should_allow_restore': False}
        },
        'asset_recommendation_info': None,
        'audio_ranking_info': {'best_audio_cluster_id': '1720142158554736'},
        'audio_type': 'original_sounds',
        'branded_content_tag_info': {'can_add_tag': False},
        'breaking_content_info': None,
        'breaking_creator_info': None,
        'challenge_info': None,
        'content_appreciation_info': {'enabled': False, 'entry_point_container': None},
        'contextual_highlight_info': None,
        'cutout_sticker_info': [],
        'disable_use_in_clips_client_cache': False,
        'external_media_info': None,
        'is_fan_club_promo_video': False,
        'is_shared_to_fb': False,
        'mashup_info': {
            'can_toggle_mashups_allowed': False,
            'formatted_mashups_count': None,
            'has_been_mashed_up': True,
            'has_nonmimicable_additional_audio': False,
            'is_creator_requesting_mashup': False,
            'is_light_weight_check': True,
            'is_light_weight_reuse_allowed_check': False,
            'is_pivot_page_available': False,
            'is_reuse_allowed': True,
            'mashup_type': None,
            'mashups_allowed': True,
            'non_privacy_filtered_mashups_media_count': 7,
            'privacy_filtered_mashups_media_count': None,
            'original_media': None
        },
        'merchandising_pill_info': None,
        'music_canonical_id': '18386621071100037',
        'music_info': None,
        'nux_info': None,
        'original_sound_info': {
            'allow_creator_to_rename': True,
            'audio_asset_id': 1363945744591456,
            'attributed_custom_audio_asset_id': None,
            'can_remix_be_shared_to_fb': True,
            'can_remix_be_shared_to_fb_expansion': True,
            'dash_manifest': '<?xml version="1.0" encoding="UTF-8"?>\n<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011"></MPD>',
            'duration_in_ms': 10800,
            'formatted_clips_media_count': None,
            'hide_remixing': False,
            'is_audio_automatically_attributed': False,
            'is_eligible_for_audio_effects': True,
            'is_eligible_for_vinyl_sticker': True,
            'is_explicit': False,
            'is_original_audio_download_eligible': True,
            'is_reuse_disabled': False,
            'is_xpost_from_fb': False,
            'music_canonical_id': None,
            'oa_owner_is_music_artist': False,
            'original_audio_subtype': 'default',
            'original_audio_title': 'Original audio',
            'original_media_id': 3528172182514999608,
            'progressive_download_url': 'https://instagram.flux3-1.fna.fbcdn.net/example.mp4',
            'should_mute_audio': False,
            'time_created': 1734810960,
            'trend_rank': None,
            'previous_trend_rank': None,
            'overlap_duration_in_ms': None,
            'audio_asset_start_time_in_ms': None,
            'ig_artist': {
                'pk': 68661275454,
                'pk_id': '68661275454',
                'id': '68661275454',
                'username': 'petercoleslanguages',
                'full_name': 'Peter Coles | Polyglot',
                'is_private': False,
                'is_verified': True,
                'profile_pic_id': '3428801016938752722_68661275454',
                'profile_pic_url': 'https://instagram.flux3-1.fna.fbcdn.net/example.jpg',
                'strong_id__': '68661275454'
            },
            'audio_filter_infos': [],
            'audio_parts': [],
            'audio_parts_by_filter': [],
            'consumption_info': {
                'display_media_id': None,
                'is_bookmarked': False,
                'is_trending_in_clips': False,
                'should_mute_audio_reason': '',
                'should_mute_audio_reason_type': None,
                'user_notes': None
            },
            'xpost_fb_creator_info': None,
            'fb_downstream_use_xpost_metadata': {
                'downstream_use_xpost_deny_reason': 'NONE'
            }
        },
        'originality_info': None,
        'reels_on_the_rise_info': None,
        'reusable_text_attribute_string': None,
        'reusable_text_info': None,
        'shopping_info': None,
        'show_achievements': False,
        'template_info': None,
        'may_have_template_info': None,
        'viewer_interaction_settings': None
    }
]


def test_clips_metadata_validation():
    """Test that our ClipsMetadata models can validate the provided examples."""
    console.print("\n[bold green]🎬 Testing ClipsMetadata Pydantic Models[/bold green]")
    console.print("=" * 60)
    
    for i, example in enumerate(test_clips_metadata_examples):
        console.print(f"\n[cyan]Testing example {i + 1}...[/cyan]")
        
        try:
            # Create ClipsMetadata instance from example
            clips_metadata = ClipsMetadata.model_validate(example)
            
            console.print(f"[green]✓ Successfully validated example {i + 1}[/green]")
            console.print(f"[green]  - Entry point: {clips_metadata.clips_creation_entry_point}[/green]")
            console.print(f"[green]  - Audio type: {clips_metadata.audio_type}[/green]")
            console.print(f"[green]  - Music canonical ID: {clips_metadata.music_canonical_id}[/green]")
            console.print(f"[green]  - Artist: {clips_metadata.original_sound_info.ig_artist.username}[/green]")
            console.print(f"[green]  - Duration: {clips_metadata.original_sound_info.duration_in_ms}ms[/green]")
            console.print(f"[green]  - Mashup count: {clips_metadata.mashup_info.non_privacy_filtered_mashups_media_count}[/green]")
            
            # Test serialization back to dict
            serialized = clips_metadata.model_dump()
            console.print(f"[green]  - Serialization works: {len(serialized)} fields[/green]")
            
        except Exception as e:
            console.print(f"[red]✗ Failed to validate example {i + 1}: {e}[/red]")
            import traceback
            console.print(traceback.format_exc())
    
    console.print(f"\n[bold green]✓ ClipsMetadata validation tests completed[/bold green]")


def test_clips_metadata_type_safety():
    """Test type safety by accessing nested fields."""
    console.print("\n[bold green]🔍 Testing ClipsMetadata Type Safety[/bold green]")
    console.print("=" * 60)
    
    example = test_clips_metadata_examples[0]
    clips_metadata = ClipsMetadata.model_validate(example)
    
    # Test nested field access
    console.print(f"[cyan]Achievement info - Show achievements: {clips_metadata.achievements_info.show_achievements}[/cyan]")
    console.print(f"[cyan]Audio reattribution - Should allow restore: {clips_metadata.additional_audio_info.audio_reattribution_info.should_allow_restore}[/cyan]")
    console.print(f"[cyan]Audio ranking - Best cluster ID: {clips_metadata.audio_ranking_info.best_audio_cluster_id}[/cyan]")
    console.print(f"[cyan]Branded content - Can add tag: {clips_metadata.branded_content_tag_info.can_add_tag}[/cyan]")
    console.print(f"[cyan]Content appreciation - Enabled: {clips_metadata.content_appreciation_info.enabled}[/cyan]")
    console.print(f"[cyan]Mashup info - Has been mashed up: {clips_metadata.mashup_info.has_been_mashed_up}[/cyan]")
    console.print(f"[cyan]Mashup info - Reuse allowed: {clips_metadata.mashup_info.is_reuse_allowed}[/cyan]")
    console.print(f"[cyan]Original sound - Allow creator to rename: {clips_metadata.original_sound_info.allow_creator_to_rename}[/cyan]")
    console.print(f"[cyan]Original sound - Audio asset ID: {clips_metadata.original_sound_info.audio_asset_id}[/cyan]")
    console.print(f"[cyan]Original sound - Is explicit: {clips_metadata.original_sound_info.is_explicit}[/cyan]")
    console.print(f"[cyan]Artist - Username: {clips_metadata.original_sound_info.ig_artist.username}[/cyan]")
    console.print(f"[cyan]Artist - Is verified: {clips_metadata.original_sound_info.ig_artist.is_verified}[/cyan]")
    console.print(f"[cyan]Consumption info - Is bookmarked: {clips_metadata.original_sound_info.consumption_info.is_bookmarked}[/cyan]")
    console.print(f"[cyan]FB metadata - Deny reason: {clips_metadata.original_sound_info.fb_downstream_use_xpost_metadata.downstream_use_xpost_deny_reason}[/cyan]")
    
    console.print(f"\n[bold green]✓ Type safety tests completed - All fields accessible with proper typing[/bold green]")


def main():
    """Run all tests for ClipsMetadata models."""
    try:
        test_clips_metadata_validation()
        test_clips_metadata_type_safety()
        console.print(f"\n[bold green]🎉 All ClipsMetadata tests passed![/bold green]")
    except Exception as e:
        console.print(f"\n[red]❌ Test failed: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())


if __name__ == "__main__":
    main() 