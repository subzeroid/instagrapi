export interface BioLink {
  link_id: string;
  url: string;
  lynx_url?: string;
  link_type?: string;
  title?: string;
  is_pinned?: boolean;
  open_external_url_with_in_app_browser?: boolean;
}

export interface Broadcast {
  title: string;
  thread_igid: string;
  subtitle: string;
  invite_link: string;
  is_member: boolean;
  group_image_uri: string;
  group_image_background_uri: string;
  thread_subtype: number;
  number_of_members: number;
  creator_igid?: string;
  creator_username: string;
}

export interface User {
  pk: string;
  username: string;
  full_name: string;
  is_private: boolean;
  profile_pic_url: string;
  profile_pic_url_hd?: string;
  is_verified: boolean;
  media_count: number;
  follower_count: number;
  following_count: number;
  biography?: string;
  bio_links: BioLink[];
  external_url?: string;
  account_type?: number;
  is_business: boolean;
  broadcast_channel: Broadcast[];
  public_email?: string;
  contact_phone_number?: string;
  public_phone_country_code?: string;
  public_phone_number?: string;
  business_contact_method?: string;
  business_category_name?: string;
  category_name?: string;
  category?: string;
  address_street?: string;
  city_id?: string;
  city_name?: string;
  latitude?: number;
  longitude?: number;
  zip?: string;
  instagram_location_id?: string;
  interop_messaging_user_fbid?: string;
}

export interface UserShort {
  pk: string;
  username?: string;
  full_name?: string;
  profile_pic_url?: string;
  profile_pic_url_hd?: string;
  is_private?: boolean;
}

export interface Hashtag {
  id: string;
  name: string;
  media_count?: number;
  profile_pic_url?: string;
}

// A simplified version for now
export interface Media {
  pk: string;
  id: string;
  code: string;
  taken_at: number; // timestamp
  media_type: number;
  user: UserShort;
  like_count: number;
  caption_text: string;
}
