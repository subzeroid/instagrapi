from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from instagrapi.types import User as Profile, BioLink
from typing import List
from pydantic import BaseModel
from enum import Enum
import os
import dotenv
import time
import json

dotenv.load_dotenv()

USERNAME = os.getenv("INSTAGRAM_USERNAME")
PASSWORD = os.getenv("INSTAGRAM_PASSWORD")


class SearchFilters(BaseModel):
    min_followers: int = 10000
    max_followers: int = 100000
    min_engagement_rate: float = 1.0
    
class Creator(BaseModel):
    followers: int
    engagement_rate: float
    bio_links: List[BioLink] = []
    bio: str
    profit_potential: float
    username: str

class SearchMethod(Enum):
    HASHTAG = "hashtag"
    KEYWORD = "keyword"

class SearchParams(BaseModel):
    method: SearchMethod
    max_profiles: int
    niche: str
    save: bool

class CreatorCategory(Enum):
    MATCH = "match"
    PREFILTERED = "prefiltered"
    FILTERED = "filtered"



class CreatorSearcher:
    def __init__(self):
        self.cl = Client()
        self.login()
        
    def login(self):
            """
            Attempts to login to Instagram using either the provided session information
            or the provided username and password.
            """

            session = self.cl.load_settings("session.json")
            self.cl.delay_range = [1, 3]
            
            login_via_session = False
            login_via_pw = False

            if session:
                try:
                    self.cl.set_settings(session)
                    self.cl.login(USERNAME, PASSWORD)

                    try:
                        self.cl.get_timeline_feed()
                    except LoginRequired:
                        old_session = self.cl.get_settings()
                        self.cl.set_settings({})
                        self.cl.set_uuids(old_session["uuids"])
                        self.cl.login(USERNAME, PASSWORD)
                    login_via_session = True
                except Exception as e:
                    pass

            if not login_via_session:
                try:
                    if self.cl.login(USERNAME, PASSWORD):
                        login_via_pw = True
                except Exception as e:
                    pass

            if not login_via_pw and not login_via_session:
                raise Exception("Couldn't login user with either password or session")

    def _filter_creator(self, creator, filters: SearchFilters) -> bool:
        if creator.followers <= filters.min_followers:
            return False
        if creator.followers >= filters.max_followers:
            return False
        if creator.engagement_rate < filters.min_engagement_rate:
            return False
        if creator.profit_potential < filters.min_profit_potential:
            return False
        return True

    def _prefilter_profile(self, profile: Profile, filters: SearchFilters) -> bool:
        pre_filters = {
            "min_followers": filters.min_followers,
            "max_followers": filters.max_followers,
        }

        if profile.follower_count < pre_filters["min_followers"] or profile.follower_count > pre_filters["max_followers"]:
            return False
        return True

    def profile_to_creator(self, profile: Profile) -> Creator:
        er = self.calculate_profile_engagement_rate(profile)
        profit_potential = self.calculate_profit_potential(profile, er)
        return Creator(followers=profile.follower_count, engagement_rate=er, profit_potential=profit_potential, bio=profile.biography, bio_links=profile.bio_links, username=profile.username)

    def calculate_profile_engagement_rate(self, profile: Profile) -> float:
        # Skip first 3 reels to prevent pinned reels from skewing the engagement rate
        print(f"=== Calculating engagement rate for {profile.username} ===")
        user_medias = list(self.cl.user_clips(profile.pk, amount=33))[3:]

        user_recent_reels = list(filter(lambda media: media.product_type == "clips" and media.media_type == 2, user_medias))
        if len(user_recent_reels) == 0:
            print(f"=== No reels found for {profile.username} ===")
            return 0.0
        
        total_likes = sum(media.like_count for media in user_recent_reels)
        total_comments = sum(media.comment_count for media in user_recent_reels)

        followers = profile.follower_count
        average_likes = total_likes / len(user_recent_reels)
        average_comments = total_comments / len(user_recent_reels)

        engagement_rate = ((average_likes + average_comments) / followers) * 100
        print(f"=== Engagement rate for {profile.username} is {engagement_rate} ===")
        return engagement_rate


    def calculate_profit_potential(self, profile: Profile, er: float) -> float:
        return profile.follower_count * er * 0.4


    def get_profiles(self, params: SearchParams) -> List[str]:
        if params.method == SearchMethod.HASHTAG:
            return self.get_profiles_by_hashtag(params.niche, params.max_profiles)
        elif params.method == SearchMethod.KEYWORD:
            return self.get_profiles_by_keyword(params.niche)
        

    def get_profiles_by_hashtag(self, hashtag: str, max_profiles: int) -> List[Profile]:
        profiles = []
        
        hashtag_medias = self.cl.hashtag_medias_top(hashtag, amount=max_profiles)
        for media in hashtag_medias:
            user_id = media.user.pk

            id_already_in_profiles = any(profile == user_id for profile in profiles)
            if id_already_in_profiles:
                continue
            profiles.append(user_id)

        print(f"=== Analyzed {max_profiles} profiles and found {len(profiles)} unique ones. ===")
        
        return profiles


    def get_profiles_by_keyword(self, keyword: str) -> List[Profile]:
        raise NotImplementedError("Not implemented")


    def filter_and_save(self, filters: SearchFilters, user_id: str, path: str) -> CreatorCategory:
        try:
            profile = self.cl.user_info(user_id)
            profile_valid = self._prefilter_profile(profile, filters)

            if profile_valid is False:
                print(f"=== Profile {profile.username} failed prefilter. ===")
                return CreatorCategory.PREFILTERED
            
            creator = self.profile_to_creator(profile)
            creator_valid = self._filter_creator(creator, filters)

            if creator_valid is False:
                print(f"=== Profile {profile.username} failed filter. ===")
                return CreatorCategory.FILTERED

            self.save_creator(creator, path)
            return CreatorCategory.MATCH
        except Exception as e:
            print(f"=== Error filtering and saving profile {user_id}: {e} ===")
            print(" === Will Stop Process bcs this error was likely instagram rate limiting. === ")
            raise e

        


    def save_creator(self, creator: Creator, path: str) -> None:
        existing_creators = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                existing_creators = json.load(f)
        

        existing_creators.append(creator.model_dump())
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing_creators, f, ensure_ascii=False, indent=2)


    def search(self, params: SearchParams, filters: SearchFilters) -> List[Creator]:
        results = []
        path = self.start_search_log(params.niche)
        profiles = self.get_profiles(params)

        for profile in profiles:
            try:
                cat = self.filter_and_save(filters, profile, path)
            except Exception as e:
                print("=== Filtering and saving raised. Calculating results ===")
                break
            results.append(cat)


        prefiltered = results.count(CreatorCategory.PREFILTERED)
        filtered = results.count(CreatorCategory.FILTERED)
        matches = results.count(CreatorCategory.MATCH)
        
        print("=== Results: ===")
        print(f"=== Prefiltered Creators: {prefiltered} ===")
        print(f"=== Filtered Creators: {filtered} ===")
        print(f"=== Matched Creators: {matches} ===")

        
    def start_search_log(self, niche: str) -> str:
        path = f"user_searches/{niche}_results_{time.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
        
        return path




# Example usage:

searcher = CreatorSearcher()

search_filters = SearchFilters(
    min_followers=10000,
    max_followers=100000,
    min_engagement_rate=0.6,
    min_profit_potential=300 # This is an estimation of how much buyers this creator has.
)

searchParams = SearchParams(
    method=SearchMethod.HASHTAG,
    max_profiles=70,
    niche="menopause",
    save=True
)

creators = searcher.search(searchParams, search_filters)

