import { describe, it, expect, mock } from "bun:test";
import { Client } from '../src/client';
import { Hashtag } from "../src/types";
import { HashtagNotFound } from "../src/exceptions";

// Mock the utils module as it's not relevant for this test
mock.module('../src/utils', () => ({
    generateUuid: () => 'mock-uuid',
    passwordEncrypt: (password: string) => `#PWD_INSTAGRAM:4:0:${password}`,
    generateJazoest: () => 'mock-jazoest',
}));

describe("Hashtag functionality", () => {

    it("should get hashtag info successfully", async () => {
        const client = new Client();
        const mockHashtag: Hashtag = {
            id: '17841562498105353',
            name: 'instagram',
            media_count: 12345,
            profile_pic_url: 'https://example.com/hashtag.jpg'
        };

        // Mock the private_request for hashtag info
        client.private_request = async (endpoint: string): Promise<any> => {
            if (endpoint === 'tags/instagram/info/') {
                return mockHashtag;
            }
            return {};
        };

        const hashtag = await client.hashtag_info('instagram');
        expect(hashtag).toBeDefined();
        expect(hashtag.name).toBe('instagram');
        expect(hashtag.id).toBe('17841562498105353');
    });

    it("should throw HashtagNotFound for a non-existent hashtag", async () => {
        const client = new Client();

        client.private_request = async (endpoint: string): Promise<any> => {
            if (endpoint === 'tags/nonexistent/info/') {
                // The real API would throw a 404, which our request handler would turn into an error.
                // We simulate the mixin's behavior of throwing HashtagNotFound.
                 throw new HashtagNotFound("Hashtag not found");
            }
            return {};
        };

        await expect(client.hashtag_info('nonexistent')).rejects.toThrow(HashtagNotFound);
    });

    it("should follow a hashtag successfully", async () => {
        const client = new Client();
        // Simulate a logged-in state
        client.state.user_id = '12345';
        client.state.uuids = { uuid: 'mock-uuid' };

        client.private_request = async (endpoint: string, options: any): Promise<any> => {
            if (endpoint === 'web/tags/follow/instagram/') {
                return { status: 'ok' };
            }
            return { status: 'fail' };
        };

        const result = await client.hashtag_follow('instagram');
        expect(result).toBe(true);
    });

    it("should throw an error when trying to follow a hashtag without being logged in", async () => {
        const client = new Client();
        // No user_id, so not logged in
        await expect(client.hashtag_follow('instagram')).rejects.toThrow("Login required");
    });

});
