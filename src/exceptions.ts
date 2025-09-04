export class ClientError extends Error {
  response?: any;
  code?: number;

  constructor(message?: string, ...args: any[]) {
    super(message, ...args);
    this.name = this.constructor.name;
  }
}

export class ClientUnknownError extends ClientError {}
export class WrongCursorError extends ClientError {
  message = "You specified a non-existent cursor";
}
export class ClientStatusFail extends ClientError {}
export class ClientErrorWithTitle extends ClientError {}
export class ResetPasswordError extends ClientError {}
export class GenericRequestError extends ClientError {}
export class ClientGraphqlError extends ClientError {}
export class ClientJSONDecodeError extends ClientError {}
export class ClientConnectionError extends ClientError {}
export class ClientBadRequestError extends ClientError {}
export class ClientUnauthorizedError extends ClientError {}
export class ClientForbiddenError extends ClientError {}
export class ClientNotFoundError extends ClientError {}
export class ClientThrottledError extends ClientError {}
export class ClientRequestTimeout extends ClientError {}
export class ClientIncompleteReadError extends ClientError {}
export class ClientLoginRequired extends ClientError {}
export class ReloginAttemptExceeded extends ClientError {}
export class PrivateError extends ClientError {}
export class NotFoundError extends PrivateError {
  reason = "Not found";
}

export class HashtagError extends PrivateError {}
export class HashtagNotFound extends NotFoundError {}

export class UserError extends PrivateError {}
export class UserNotFound extends NotFoundError {}


export class FeedbackRequired extends PrivateError {}
export class ChallengeError extends PrivateError {}
export class ChallengeRedirection extends ChallengeError {}
export class ChallengeRequired extends ChallengeError {}
export class ChallengeSelfieCaptcha extends ChallengeError {}
export class ChallengeUnknownStep extends ChallengeError {}
export class SelectContactPointRecoveryForm extends ChallengeError {}
export class RecaptchaChallengeForm extends ChallengeError {}
export class SubmitPhoneNumberForm extends ChallengeError {}
export class LegacyForceSetNewPasswordForm extends ChallengeError {}
export class LoginRequired extends PrivateError {}
export class SentryBlock extends PrivateError {}
export class RateLimitError extends PrivateError {}
export class ProxyAddressIsBlocked extends PrivateError {}
export class BadPassword extends PrivateError {}
export class BadCredentials extends PrivateError {}
export class PleaseWaitFewMinutes extends PrivateError {}
export class UnknownError extends PrivateError {}
export class TwoFactorRequired extends PrivateError {}
export class PrivateAccount extends PrivateError {}
export class InvalidTargetUser extends PrivateError {}
export class InvalidMediaId extends PrivateError {}
export class MediaUnavailable extends PrivateError {}
export class ValidationError extends Error {}
export class EmailInvalidError extends ClientError {}
export class EmailNotAvailableError extends ClientError {}
export class EmailVerificationSendError extends ClientError {}
export class AgeEligibilityError extends ClientError {}
export class CaptchaChallengeRequired extends ClientError {
    challenge_details: any;
    constructor(message = "Captcha challenge required, but no solver configured or available.", challenge_details = {}, ...args: any[]) {
        super(message, ...args);
        this.challenge_details = challenge_details;
    }
}
