## Common Exceptions

| Exception                 | Base        | Description
| ------------------------- | ----------- |-------------------------------------
| ClientError               | Exception   | Base Exception for Instagram calls
| GenericRequestError       | ClientError | Base Exception for Request (Solution: try changing your proxy)
| ClientGraphqlError        | ClientError | Exception for GraphQL calls
| ClientJSONDecodeError     | ClientError | JSON Exception
| ClientConnectionError     | ClientError | Connection error (Solution: try changing your proxy)
| ClientBadRequestError     | ClientError | HTTP 400 Exception
| ClientForbiddenError      | ClientError | HTTP 403 Exception
| ClientNotFoundError       | ClientError | HTTP 404 Exception
| ClientThrottledError      | ClientError | HTTP 429 Exception (Solution: try changing your proxy)
| ClientRequestTimeout      | ClientError | Request Timeout Exception
| ClientIncompleteReadError | ClientError | Raised when response interrupted
| ClientLoginRequired       | ClientError | Raised when Instagram required Login (Solution: try changing your proxy)
| ReloginAttemptExceeded    | ClientError | Raised when all attempts exceeded

## Private Exceptions

| Exception                | Base         | Description
| ------------------------ | ------------ |-----------------------------------------------------------
| PrivateError             | ClientError  | Base Exception for Private calls (received from Instagram)
| FeedbackRequired         | PrivateError | Raise when get message=feedback_required
| LoginRequired            | PrivateError | Raise when get message=login_required
| SentryBlock              | PrivateError | Raise when get message=sentry_block (most likely you were banned from instagram by ip address. Solution: try changing your proxy)
| RateLimitError           | PrivateError | Raise when get message=rate_limit_error (Solution: try changing your proxy)
| BadPassword              | PrivateError | Raise when get message=bad_password
| TwoFactorRequired        | PrivateError | Raise when get message=two_factor_required
| UnknownError             | PrivateError | Raise when get unknown message (new message from instagram)
| PleaseWaitFewMinutes     | PrivateError | Raise when get message="Please wait a few minutes before you try again" (Solution: try changing your proxy)

## Challenge Exceptions

| Exception                      | Base           | Description                                                 |
| ------------------------------ | -------------- |------------------------------------------------------------ |
| ChallengeError                 | PrivateError   | Base Challenge Exception (received from Instagram)          |
| ChallengeRedirection           | ChallengeError | Raise when get type=CHALLENGE_REDIRECTION                   |
| ChallengeRequired              | ChallengeError | Raise when get message=challenge_required                   |
| SelectContactPointRecoveryForm | ChallengeError | Raise when get challengeType=SelectContactPointRecoveryForm |
| RecaptchaChallengeForm         | ChallengeError | Raise when get challengeType=RecaptchaChallengeForm         |
| SubmitPhoneNumberForm          | ChallengeError | Raise when get challengeType=SubmitPhoneNumberForm          |

## Media Exceptions

| Exception                | Base         | Description                                    |
| ------------------------ | ------------ |----------------------------------------------- |
| MediaError               | PrivateError | Base Media Exception (received from Instagram) |
| MediaNotFound            | MediaError   | Raise when user unavailable                    |

## User Exceptions

| Exception                | Base          | Description                                   |
| ------------------------ | ------------- |---------------------------------------------- |
| UserError                | PrivateError  | Base User Exception (received from Instagram) |
| UserNotFound             | UserError     | Raise when user unavailable                   |

## Collection Exceptions

| Exception                | Base            | Description                                         |
| ------------------------ | --------------- |---------------------------------------------------- |
| CollectionError          | PrivateError    | Base Collection Exception (received from Instagram) |
| CollectionNotFound       | CollectionError | Raise when collection unavailable                   |


## Direct Exceptions

| Exception                | Base           | Description                                    |
| ------------------------ | -------------- |----------------------------------------------- |
| DirectError              | PrivateError   | Base Direct Exception                          |
| DirectThreadNotFound     | DirectError    | Raise when thread not found                    |
| DirectMessageNotFound    | DirectError    | Raise when message in thread not found         |


## Photo Exceptions

| Exception                | Base                | Description                                    |
| ------------------------ | ------------------- |----------------------------------------------- |
| PhotoNotDownload         | PrivateError        | Raise when source photo not found              |
| PhotoNotUpload           | PrivateError        | Raise when photo not upload                    |
| PhotoConfigureError      | PhotoNotUpload      | Raise when photo not configured                |
| PhotoConfigureStoryError | PhotoConfigureError | Raise when photo story not configured          |


## Video Exceptions

| Exception                | Base                | Description                                    |
| ------------------------ | ------------------- | ---------------------------------------------- |
| VideoNotDownload         | PrivateError        | Raise when source video not found              |
| VideoNotUpload           | PrivateError        | Raise when video not upload                    |
| VideoConfigureError      | VideoNotUpload      | Raise when video not configured                |
| VideoConfigureStoryError | VideoConfigureError | Raise when video story not configured          |
| VideoTooLongException    | PrivateError        | Raise when video too long                      |

## IGTV Exceptions

| Exception                | Base          | Description                                    |
| ------------------------ | ------------- |----------------------------------------------- |
| IGTVNotUpload            | PrivateError  | Raise when IGTV not upload                     |
| IGTVConfigureError       | IGTVNotUpload | Raise when IGTV not configured                 |

## Reels Clip Exceptions

| Exception                | Base          | Description                                    |
| ------------------------ | ------------- |----------------------------------------------- |
| ClipNotUpload            | PrivateError  | Raise when Reels Clip not upload               |
| ClipConfigureError       | ClipNotUpload | Raise when Reels Clip not configured           |


## Album Exceptions

| Exception                | Base         | Description                                    |
| ------------------------ | ------------ |----------------------------------------------- |
| AlbumNotDownload         | PrivateError | Raise when album not found                     |
| AlbumUnknownFormat       | PrivateError | Raise when format of media not MP4 or JPG      |
| AlbumConfigureError      | PrivateError | Raise when album not configured                |
