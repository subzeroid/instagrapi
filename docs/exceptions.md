## Common Exceptions

| Exception                 | Base        | Description
| ------------------------- | ----------- |-------------------------------------
| ClientError               | Exception   | Base Exception for Instagram calls
| GenericRequestError       | ClientError | Base Exception for Request (Solution: try changing your proxy)
| ClientGraphqlError        | ClientError | Exception for GraphQL calls
| ClientJSONDecodeError     | ClientError | JSON Exception
| ClientConnectionError     | ClientError | Connection error (Solution: try changing your proxy)
| ClientBadRequestError     | ClientError | HTTP 400 Exception
| ClientUnauthorizedError   | ClientError | HTTP 401 Exception
| ClientForbiddenError      | ClientError | HTTP 403 Exception
| ClientNotFoundError       | ClientError | HTTP 404 Exception
| ClientThrottledError      | ClientError | HTTP 429 Exception (Solution: try changing your proxy)
| ClientRequestTimeout      | ClientError | Request Timeout Exception
| ClientIncompleteReadError | ClientError | Raises when response interrupted
| ClientLoginRequired       | ClientError | Raises when Instagram required Login (Solution: try changing your proxy)
| ReloginAttemptExceeded    | ClientError | Raises when all attempts exceeded
| ClientErrorWithTitle      | ClientError | Occurs when Instagram returns an unknown error with the title
| ClientUnknownError        | ClientError | Occurs when Instagram returns an unknown error
| WrongCursorError          | ClientError | Occurs when the cursor for pagination is passed in the wrong format
| ClientStatusFail          | ClientError | Occurs when Instagram returns message with status=fail with details

## Proxy Exceptions

| Exception                 | Base         | Description
| ------------------------- | ------------ |-------------------------------------
| ProxyError                | ClientError  | Base exception for proxy
| ConnectProxyError         | ProxyError   | Occurs when it is not possible to connect to your proxy
| AuthRequiredProxyError    | ProxyError   | Occurs when incorrect credentials are passed to authorize your proxy
| ProxyAddressIsBlocked     | PrivateError | Happens when your proxy is blocked by Instagram, change your proxy!
| SentryBlock               | PrivateError | Raises when get message=sentry_block (most likely you were banned from instagram by ip address. Solution: try changing your proxy)
| RateLimitError            | PrivateError | Raises when get message=rate_limit_error (Solution: try changing your proxy)
| PleaseWaitFewMinutes     | PrivateError | Raises when get message="Please wait a few minutes before you try again" (Solution: try changing your proxy)

## GraphQL/Public Exceptions

| Exception                 | Base         | Description
| ------------------------- | ------------ |-------------------------------------
| AccountSuspended          | ClientError  | Your account is suspended
| TermsUnblock              | ClientError  | Your account may be blocked, you need to agree to the terms
| TermsAccept               | ClientError  | Your account may be blocked, you need to agree to the terms
| AboutUsError              | ClientError  | Your account may be blocked

## Private Exceptions

| Exception                | Base         | Description
| ------------------------ | ------------ |-----------------------------------------------------------
| PrivateError             | ClientError  | Base Exception for Private calls (received from Instagram)
| FeedbackRequired         | PrivateError | Raises when get message=feedback_required
| PreLoginRequired         | ClientError | Raises when authorization is required before calling a method
| LoginRequired            | PrivateError | Raises when get message=login_required (from Instagram)
| BadPassword              | PrivateError | Raises when get message=bad_password
| TwoFactorRequired        | PrivateError | Raises when get message=two_factor_required
| UnknownError             | PrivateError | Raises when get unknown message (new message from instagram)
| BadCredentials           | PrivateError | The login and password pair for your account have not been passed
| IsRegulatedC18Error      | ClientBadRequestError | The user is limited to 18+

## Challenge Exceptions

| Exception                      | Base           | Description                                                 |
| ------------------------------ | -------------- |------------------------------------------------------------ |
| ChallengeError                 | PrivateError   | Base Challenge Exception (received from Instagram)
| ChallengeRedirection           | ChallengeError | Raises when get type=CHALLENGE_REDIRECTION
| ChallengeRequired              | ChallengeError | Raises when get message=challenge_required
| ChallengeSelfieCaptcha         | ChallengeError | Raises when get step=selfie_captcha
| ChallengeUnknownStep           | ChallengeError | Occurs when challenge is unknown
| SelectContactPointRecoveryForm | ChallengeError | Raises when get challengeType=SelectContactPointRecoveryForm
| RecaptchaChallengeForm         | ChallengeError | Raises when get challengeType=RecaptchaChallengeForm
| SubmitPhoneNumberForm          | ChallengeError | Raises when get challengeType=SubmitPhoneNumberForm
| LegacyForceSetNewPasswordForm  | ChallengeError | Raises when get challengeType=LegacyForceSetNewPasswordForm
| ConsentRequired                | PrivateError   | Raises when get message=consent_required
| GeoBlockRequired               | PrivateError   | Raises when get message=geoblock_required
| CheckpointRequired             | PrivateError   | Raises when get message=checkpoint_required

## Media Exceptions

| Exception                | Base         | Description                                    |
| ------------------------ | ------------ |----------------------------------------------- |
| MediaError               | PrivateError | Base Media Exception (received from Instagram)
| MediaNotFound            | MediaError   | Raises when user unavailable
| InvalidTargetUser        | PrivateError | Occurs when the selected user cannot be mentioned (does not exist, has been deleted or is closed by privacy settings)
| InvalidMediaId           | PrivateError | Occurs when the selected media does not exists
| MediaUnavailable         | PrivateError | Occurs when the selected media is no longer available

## User Exceptions

| Exception                | Base          | Description                                   |
| ------------------------ | ------------- |---------------------------------------------- |
| UserError                | PrivateError  | Base User Exception (received from Instagram)
| UserNotFound             | UserError     | Raises when user unavailable
| PrivateAccount           | PrivateError  | The target user is closed by privacy settings

## Account Exceptions

| Exception                | Base             | Description                                   |
| ------------------------ | ---------------- |---------------------------------------------- |
| ResetPasswordError       | ClientError      | Raises when password is not reset
| UnsupportedError         | ClientError      | Raises when option is supported
| UnsupportedSettingValue  | UnsupportedError | Raises when account setting value is not supported

## Collection Exceptions

| Exception                | Base            | Description                                         |
| ------------------------ | --------------- |---------------------------------------------------- |
| CollectionError          | PrivateError    | Base Collection Exception (received from Instagram)
| CollectionNotFound       | CollectionError | Raises when collection unavailable

## Direct Exceptions

| Exception                | Base           | Description                                    |
| ------------------------ | -------------- |----------------------------------------------- |
| DirectError              | PrivateError   | Base Direct Exception
| DirectThreadNotFound     | DirectError    | Raises when thread not found
| DirectMessageNotFound    | DirectError    | Raises when message in thread not found

## Photo Exceptions

| Exception                | Base                | Description                                    |
| ------------------------ | ------------------- |----------------------------------------------- |
| PhotoNotDownload         | PrivateError        | Raises when source photo not found
| PhotoNotUpload           | PrivateError        | Raises when photo not upload
| PhotoConfigureError      | PhotoNotUpload      | Raises when photo not configured
| PhotoConfigureStoryError | PhotoConfigureError | Raises when photo story not configured

## Video Exceptions

| Exception                | Base                | Description                                    |
| ------------------------ | ------------------- | ---------------------------------------------- |
| VideoNotDownload         | PrivateError        | Raises when source video not found
| VideoNotUpload           | PrivateError        | Raises when video not upload
| VideoConfigureError      | VideoNotUpload      | Raises when video not configured
| VideoConfigureStoryError | VideoConfigureError | Raises when video story not configured
| VideoTooLongException    | PrivateError        | Raises when video too long

## IGTV Exceptions

| Exception                | Base          | Description                                    |
| ------------------------ | ------------- |----------------------------------------------- |
| IGTVNotUpload            | PrivateError  | Raises when IGTV not upload
| IGTVConfigureError       | IGTVNotUpload | Raises when IGTV not configured

## Reels/Clip Exceptions

| Exception                | Base          | Description                                    |
| ------------------------ | ------------- |----------------------------------------------- |
| ClipNotUpload            | PrivateError  | Raises when Reels Clip not upload
| ClipConfigureError       | ClipNotUpload | Raises when Reels Clip not configured

## Album Exceptions

| Exception                | Base         | Description                                    |
| ------------------------ | ------------ |----------------------------------------------- |
| AlbumNotDownload         | PrivateError | Raises when album not found
| AlbumUnknownFormat       | PrivateError | Raises when format of media not MP4 or JPG
| AlbumConfigureError      | PrivateError | Raises when album not configured

## Story Exceptions

| Exception                | Base          | Description                                    |
| ------------------------ | ------------- |----------------------------------------------- |
| StoryNotFound            | NotFoundError | Raises when story not found

## Highlight Exceptions

| Exception                | Base          | Description                                   |
| ------------------------ | ------------- |---------------------------------------------- |
| HighlightNotFound        | NotFoundError | Raises when highlight not found

## Hashtag Exceptions

| Exception                | Base                 | Description                            |
| ------------------------ | -------------------- |--------------------------------------- |
| HashtagError             | PrivateError         | Base exception for hashtag
| HashtagNotFound          | NotFoundError        | Raises when hashtag not found
| HashtagPageWarning       | ClientForbiddenError | Occurs when Instagram returns warning_message with category_name=HASHTAG_PAGE_WARNING_MESSAGE

## Location Exceptions

| Exception                | Base          | Description                                    |
| ------------------------ | ------------- |----------------------------------------------- |
| LocationError            | PrivateError  | Base exception for location
| LocationNotFound         | NotFoundError | Raises when location not found

## Comment Exceptions

| Exception                | Base         | Description                                    |
| ------------------------ | ------------ |----------------------------------------------- |
| CommentNotFound          | PrivateError | Raises when comment not found
| CommentsDisabled         | PrivateError | The ability to comment has been disabled by the author of the post

## Share Exceptions

| Exception                 | Base         | Description
| ------------------------- | ------------ |-------------------------------------
| ShareDecodeError          | PrivateError | Occurs when the data format for Share-obj is incorrect

## Note Exceptions

| Exception                | Base          | Description                                    |
| ------------------------ | ------------- |----------------------------------------------- |
| NoteNotFound             | NotFoundError | Raises when note not found

## Track Exceptions

| Exception                | Base          | Description                                    |
| ------------------------ | ------------- |----------------------------------------------- |
| TrackNotFound            | NotFoundError | Raises when track not found
