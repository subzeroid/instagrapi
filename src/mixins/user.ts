import { User } from "../types";
import { UserNotFound } from "../exceptions";

// This would be in a real extractors.ts file
function extractUserV1(data: any): User {
    // This is a mock implementation based on the python code's expected output
    return data as User;
}

// Base class definition for mixin application
type Constructor<T = any> = new (...args: any[]) => T;

export function UserMixin<TBase extends Constructor>(Base: TBase) {
    return class extends Base {
        private _users_cache: Record<string, User> = {};
        private _usernames_cache: Record<string, string> = {}; // username -> pk

        /**
         * Get user object from user id
         * @param user_id User id of an instagram account
         * @returns An object of User type
         */
        async user_info_v1(userId: string): Promise<User> {
            try {
                const result = await this.private_request(`users/${userId}/info/`);
                if (!result.user) {
                     throw new UserNotFound(`User with id ${userId} not found.`);
                }
                return extractUserV1(result.user);
            } catch (e: any) {
                if (e.message.includes("User not found")) {
                    throw new UserNotFound(e, `User with id ${userId} not found.`);
                }
                throw e;
            }
        }

       /**
         * Get user object from user id
         * @param user_id User id of an instagram account
         * @param use_cache Whether or not to use information from cache
         * @returns An object of User type
         */
        async user_info(userId: string, useCache: boolean = true): Promise<User> {
            if (useCache && this._users_cache[userId]) {
                return { ...this._users_cache[userId] }; // Return a copy
            }
            // In a real scenario, this would have more complex logic with fallbacks to GQL etc.
            const user = await this.user_info_v1(userId);
            this._users_cache[user.pk] = user;
            this._usernames_cache[user.username] = user.pk;
            return { ...user }; // Return a copy
        }

        /**
         * Get user PK from username
         * @param username Username for an Instagram account
         * @returns User PK
         */
        async user_id_from_username(username: string): Promise<string> {
            username = username.toLowerCase();
            if (this._usernames_cache[username]) {
                return this._usernames_cache[username];
            }
            // This is a simplified version of the python code's user_info_by_username
            const result = await this.private_request(`users/${username}/usernameinfo/`);
            if (!result.user) {
                throw new UserNotFound(`User with username ${username} not found.`);
            }
            const user = extractUserV1(result.user);
            this._users_cache[user.pk] = user;
            this._usernames_cache[user.username] = user.pk;
            return user.pk;
        }
    };
}
