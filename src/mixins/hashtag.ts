import { Hashtag } from "../types";
import { HashtagNotFound } from "../exceptions";

// This would be in a real extractors.ts file
function extractHashtagV1(data: any): Hashtag {
    // This is a mock implementation based on the python code's expected output
    return {
        id: data.id,
        name: data.name,
        media_count: data.media_count,
        profile_pic_url: data.profile_pic_url,
    };
}


// Base class definition for mixin application
type Constructor<T = any> = new (...args: any[]) => T;

export function HashtagMixin<TBase extends Constructor>(Base: TBase) {
    return class extends Base {

        /**
         * Get information about a hashtag by Private Mobile API
         * @param name Name of the hashtag
         * @returns An object of Hashtag
         */
        async hashtag_info_v1(name: string): Promise<Hashtag> {
            const result = await this.private_request(`tags/${name}/info/`);
            return extractHashtagV1(result);
        }

        /**
         * Get information about a hashtag (defaults to v1)
         * @param name Name of the hashtag
         * @returns An object of Hashtag
         */
        async hashtag_info(name: string): Promise<Hashtag> {
            try {
                // In a real scenario, you might try a1 or gql first.
                // For this conversion, we'll stick to the v1 implementation.
                return await this.hashtag_info_v1(name);
            } catch (e) {
                // The original has more complex error handling. We'll keep it simple.
                throw new HashtagNotFound(`Hashtag ${name} not found.`);
            }
        }

        /**
         * Follow a hashtag
         * @param hashtag Unique identifier of a Hashtag
         * @returns A boolean value
         */
        async hashtag_follow(hashtag: string): Promise<boolean> {
            if (!this.state.user_id) {
                throw new Error("Login required");
            }
            const data = { user_id: this.state.user_id, _uuid: this.state.uuids.uuid };
            const result = await this.private_request(
                `web/tags/follow/${hashtag}/`,
                { data } // Assuming data is sent in the body
            );
            return result.status === "ok";
        }

        /**
         * Unfollow a hashtag
         * @param hashtag Unique identifier of a Hashtag
         * @returns A boolean value
         */
        async hashtag_unfollow(hashtag: string): Promise<boolean> {
            if (!this.state.user_id) {
                throw new Error("Login required");
            }
            const data = { user_id: this.state.user_id, _uuid: this.state.uuids.uuid };
             const result = await this.private_request(
                `web/tags/unfollow/${hashtag}/`,
                { data }
            );
            return result.status === "ok";
        }
    };
}
