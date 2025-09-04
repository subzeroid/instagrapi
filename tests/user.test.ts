import { describe, it, expect, mock } from "bun:test";
import { Client } from '../src/client';
import { User } from "../src/types";
import { UserNotFound } from "../src/exceptions";

// Mock the utils module as it's not relevant for this test
mock.module('../src/utils', () => ({
    generateUuid: () => 'mock-uuid',
    passwordEncrypt: (password: string) => `#PWD_INSTAGRAM:4:0:${password}`,
    generateJazoest: () => 'mock-jazoest',
}));

describe("User functionality", () => {
    const mockUser: User = {
        pk: '12345',
        username: 'testuser',
        full_name: 'Test User',
        is_private: false,
        profile_pic_url: 'https://example.com/user.jpg',
        is_verified: false,
        media_count: 10,
        follower_count: 100,
        following_count: 50,
        biography: 'A test user.',
        bio_links: [],
        is_business: false,
        broadcast_channel: [],
    };

    it("should get user info successfully by user id", async () => {
        const client = new Client();

        client.private_request = async (endpoint: string): Promise<any> => {
            if (endpoint === 'users/12345/info/') {
                return { user: mockUser };
            }
            return {};
        };

        const user = await client.user_info('12345');
        expect(user).toBeDefined();
        expect(user.pk).toBe('12345');
        expect(user.username).toBe('testuser');
    });

    it("should get user id from username successfully", async () => {
        const client = new Client();

        client.private_request = async (endpoint: string): Promise<any> => {
            if (endpoint === 'users/testuser/usernameinfo/') {
                return { user: mockUser };
            }
            return {};
        };

        const userId = await client.user_id_from_username('testuser');
        expect(userId).toBe('12345');
    });

    it("should throw UserNotFound for a non-existent user id", async () => {
        const client = new Client();

        client.private_request = async (endpoint: string): Promise<any> => {
            if (endpoint === 'users/nonexistent/info/') {
                throw new UserNotFound("User not found");
            }
            return {};
        };

        await expect(client.user_info('nonexistent')).rejects.toThrow(UserNotFound);
    });

    it("should use cache for user_info if enabled", async () => {
        const client = new Client();
        let requestCount = 0;

        client.private_request = async (endpoint: string): Promise<any> => {
            requestCount++;
            if (endpoint === 'users/12345/info/') {
                return { user: mockUser };
            }
            return {};
        };

        // First call, should make a request
        const user1 = await client.user_info('12345');
        expect(requestCount).toBe(1);
        expect(user1.pk).toBe('12345');

        // Second call, should use cache
        const user2 = await client.user_info('12345');
        expect(requestCount).toBe(1); // Should not have increased
        expect(user2.pk).toBe('12345');

        // Third call, with cache disabled
        const user3 = await client.user_info('12345', false);
        expect(requestCount).toBe(2); // Should have increased
        expect(user3.pk).toBe('12345');
    });

});
