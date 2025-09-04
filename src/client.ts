import { LoginMixin } from './mixins/auth';
import { HashtagMixin } from './mixins/hashtag';
import { UserMixin } from './mixins/user';

// Base class with properties that mixins might need.
class ClientBase {
    // These will be populated by mixins or the constructor
    username?: string;
    password?: string;
    settings: any;
    state: any = {};

    constructor(settings: any = {}) {
        this.settings = settings;
        // The state object will hold dynamic properties like session IDs, tokens, etc.
        this.state = {};
    }

    // Placeholder for the actual request logic which would be in another mixin
    async private_request(endpoint: string, data?: any, login: boolean = false): Promise<any> {
        throw new Error("private_request not implemented in base. Should be implemented by a mixin.");
    }
}

// Apply the mixins to the base class in order.
const ClientWithAuth = LoginMixin(ClientBase);
const ClientWithHashtag = HashtagMixin(ClientWithAuth);
const ClientWithUser = UserMixin(ClientWithHashtag);


// The final Client class is the result of all mixins applied.
export class Client extends ClientWithUser {
    constructor(settings: any = {}) {
        super(settings);
        // Any additional client-specific initialization can go here.
    }
}
