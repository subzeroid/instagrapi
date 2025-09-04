import { BadCredentials, TwoFactorRequired } from "../exceptions";
import { passwordEncrypt, generateJazoest, generateUuid } from "../utils";

// This is a temporary base class to allow the mixin to compile.
// In the final implementation, this will be the real Client class.
class TempBase {
    username?: string;
    password?: string;
    settings: any = {};
    state: any = {};
    private _token?: string;

    async private_request(endpoint: string, data: any, login: boolean = false): Promise<any> {
        console.log(`Making private request to ${endpoint} with data:`, data);
        // Mock response for login
        if (endpoint === 'accounts/login/') {
            if (data.username === 'correct_user' && data.enc_password.startsWith('#PWD_INSTAGRAM')) {
                return {
                    logged_in_user: {
                        pk: '123456789',
                        username: 'correct_user',
                        full_name: 'Correct User',
                        is_private: false,
                        profile_pic_url: 'https://example.com/pic.jpg',
                        is_verified: true,
                    },
                    status: 'ok',
                };
            } else if (data.username === '2fa_user') {
                throw new TwoFactorRequired("Two factor required");
            } else {
                throw new BadCredentials("Invalid credentials");
            }
        }
        return { status: 'ok' };
    }

    get token(): string {
        if (!this._token) {
            // A simple token generation for mock purposes
            this._token = `mock_token_${Math.random()}`;
        }
        return this._token;
    }
}


// In TypeScript, we can't use mixins in the same way as Python.
// We use a generic function that takes a base class and returns a new class with the mixin's functionality.
// This is a common pattern for mixins in TypeScript.
type Constructor<T = TempBase> = new (...args: any[]) => T;

export function LoginMixin<TBase extends Constructor>(Base: TBase) {
    return class extends Base {
        relogin_attempt = 0;

        constructor(...args: any[]) {
            super(...args);
            this.state.device_settings = {};
            this.state.uuids = {};
            this.state.country = "US";
            this.state.country_code = 1;
            this.state.locale = "en_US";
            this.state.timezone_offset = -14400;
            this.initUuids();
        }

        private initUuids() {
            this.state.uuids.phone_id = generateUuid();
            this.state.uuids.uuid = generateUuid();
            this.state.uuids.client_session_id = generateUuid();
            this.state.uuids.advertising_id = generateUuid();
            this.state.uuids.android_device_id = `android-${generateUuid().substring(0, 16)}`;
            this.state.uuids.request_id = generateUuid();
            this.state.uuids.tray_session_id = generateUuid();
        }

        async login(username?: string, password?: string, relogin: boolean = false, verificationCode: string = ""): Promise<boolean> {
            if (username && password) {
                this.username = username;
                this.password = password;
            }
            if (!this.username || !this.password) {
                throw new BadCredentials("Both username and password must be provided.");
            }

            if (relogin) {
                // Clear session data for relogin
                this.state.authorization_data = {};
                if (this.relogin_attempt > 1) {
                    throw new Error("Relogin attempt exceeded");
                }
                this.relogin_attempt++;
            }

            const encPassword = passwordEncrypt(this.password);
            const data = {
                jazoest: generateJazoest(this.state.uuids.phone_id),
                country_codes: JSON.stringify([{ country_code: this.state.country_code.toString(), source: ["default"] }]),
                phone_id: this.state.uuids.phone_id,
                enc_password: encPassword,
                username: this.username,
                adid: this.state.uuids.advertising_id,
                guid: this.state.uuids.uuid,
                device_id: this.state.uuids.android_device_id,
                google_tokens: "[]",
                login_attempt_count: "0",
            };

            try {
                const result = await this.private_request('accounts/login/', data, true);
                if (result.status === 'ok') {
                    this.state.authorization_data = result.logged_in_user;
                    // In a real scenario, we'd parse auth headers here.
                    return true;
                }
            } catch (e) {
                if (e instanceof TwoFactorRequired) {
                    if (!verificationCode) {
                        throw new TwoFactorRequired("Verification code not provided for 2FA.");
                    }
                    // Handle 2FA login...
                    console.log("2FA required, handling with verification code...");
                    // This part would make another request to 'accounts/two_factor_login/'
                    // For now, we'll just re-throw.
                    throw e;
                }
                throw e; // Re-throw other errors
            }

            return false;
        }
    };
}
