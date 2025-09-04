import { describe, it, expect, mock } from "bun:test";
import { Client } from '../src/client';
import { BadCredentials, TwoFactorRequired } from "../src/exceptions";
import { User } from "../src/types";

// Mock the entire utils module to have control over its functions
mock.module('../src/utils', () => ({
    generateUuid: () => 'mock-uuid',
    passwordEncrypt: (password: string) => `#PWD_INSTAGRAM:4:0:${password}`, // Simple mock
    generateJazoest: () => 'mock-jazoest',
}));


describe("Authentication", () => {

    it("should login successfully with correct credentials", async () => {
        const client = new Client();

        // Mock the private_request method for this specific test
        client.private_request = async (endpoint: string, data: any): Promise<any> => {
            if (endpoint === 'accounts/login/' && data.username === 'testuser') {
                return {
                    status: 'ok',
                    logged_in_user: { pk: '123', username: 'testuser' } as User
                };
            }
            return { status: 'fail' };
        };

        const loggedIn = await client.login('testuser', 'testpass');
        expect(loggedIn).toBe(true);
        expect(client.state.authorization_data.pk).toBe('123');
    });

    it("should throw BadCredentials error for wrong credentials", async () => {
        const client = new Client();

        client.private_request = async (endpoint: string, data: any): Promise<any> => {
            if (endpoint === 'accounts/login/') {
                 throw new BadCredentials("Invalid credentials");
            }
            return { status: 'fail' };
        };

        // Using expect().rejects to test for thrown exceptions in async functions
        await expect(client.login('wronguser', 'wrongpass')).rejects.toThrow(BadCredentials);
    });

    it("should throw TwoFactorRequired error when 2FA is needed", async () => {
        const client = new Client();

        client.private_request = async (endpoint: string, data: any): Promise<any> => {
             if (endpoint === 'accounts/login/') {
                throw new TwoFactorRequired("Two factor required");
            }
            return { status: 'fail' };
        };

        // Expect a 2FA error, and also check that it asks for a code
        await expect(client.login('2fa_user', 'anypass')).rejects.toThrow("Verification code not provided for 2FA.");
    });

    it("should throw an error if username or password is not provided", async () => {
        const client = new Client();
        await expect(client.login(undefined, 'somepass')).rejects.toThrow(BadCredentials);
        await expect(client.login('someuser', undefined)).rejects.toThrow(BadCredentials);
    });

});
