# instagrapi/mixins/captcha.py
from typing import Callable, Dict, Optional

# Corrected relative import path as per task instructions
from ..exceptions import CaptchaChallengeRequired, ClientError

class CaptchaHandlerMixin:
    def __init__(self, *args, **kwargs):
        self._captcha_handler_instance: Optional[Callable[[Dict], str]] = None
        # Ensure compatibility with other mixins/classes by calling super()
        # This is important if CaptchaHandlerMixin is used in a multiple inheritance scenario.
        if hasattr(super(), '__init__'):
             super().__init__(*args, **kwargs)

    def set_captcha_handler(self, handler: Optional[Callable[[Dict], str]]) -> None:
        """
        Set a custom handler function for solving captcha challenges.

        Parameters
        ----------
        handler: Callable[[Dict], str], optional
            A function that takes a dictionary of challenge details
            (e.g., site_key, page_url, raw_challenge_json) and returns
            the solved captcha token as a string.
            If None, clears the existing handler.
        """
        self._captcha_handler_instance = handler

    def captcha_resolve(self, **challenge_details: Dict) -> str:
        """
        Resolve a captcha challenge using the registered handler.

        Parameters
        ----------
        **challenge_details: Dict
            A dictionary containing details of the captcha challenge,
            such as site_key, challenge_type, raw_challenge_json, page_url.

        Returns
        -------
        str
            The solved captcha token (e.g., g-recaptcha-response).

        Raises
        ------
        CaptchaChallengeRequired
            If no handler is configured, or if the handler fails to return a token,
            or if the handler itself raises an unhandled exception.
        ClientError
            For unexpected errors during the process.
        """
        if not hasattr(self, '_captcha_handler_instance'):
            # This can happen if __init__ of this mixin was not called,
            # e.g. due to incorrect super() chain.
            raise ClientError("CaptchaHandlerMixin not properly initialized. _captcha_handler_instance is missing.")

        if self._captcha_handler_instance:
            try:
                # Ensure all keys expected by typical handlers are present, even if None
                details_to_pass = {
                    'site_key': challenge_details.get('site_key'),
                    'page_url': challenge_details.get('page_url'), # Important for some solvers
                    'challenge_type': challenge_details.get('challenge_type'),
                    'raw_challenge_json': challenge_details.get('raw_challenge_json')
                }
                token = self._captcha_handler_instance(details_to_pass)
                if isinstance(token, str) and token:
                    return token
                else:
                    # Handler was called but didn't return a valid token
                    raise CaptchaChallengeRequired(
                        message="Captcha handler ran but did not return a valid token string.",
                        challenge_details=challenge_details
                    )
            except CaptchaChallengeRequired: # Allow handler to raise this specifically
                raise
            except Exception as e:
                # Handler raised an unexpected exception
                raise CaptchaChallengeRequired(
                    message=f"Captcha handler raised an unexpected exception: {str(e)}",
                    challenge_details=challenge_details
                ) from e
        else:
            # No handler is configured
            raise CaptchaChallengeRequired(
                message="No captcha handler is configured. Use client.set_captcha_handler() to set one.",
                challenge_details=challenge_details
            )
