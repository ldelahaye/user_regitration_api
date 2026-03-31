# Security improvements

* Create a password change feature


* Create a password reset feature


* POST /users/activate should not reveal the code pattern in validation errors
Currently we get:
```json
{
  "detail": "body → code: String should match pattern '^\\d{4}$'",
  "error_code": "VALIDATION_ERROR",
  "errors": [
    {
      "type": "string_pattern_mismatch",
      "loc": [
        "body",
        "code"
      ],
      "msg": "String should match pattern '^\\d{4}$'",
      "input": "62734",
      "ctx": {
        "pattern": "^\\d{4}$"
      }
    }
  ]
}
```
When the code pattern validation fails, we should only return:
```json
{
  "detail": "The activation code is invalid",
  "error_code": "INVALID_ACTIVATION_CODE"
}
```


* Integrate multi-factor authentication (MFA/2FA)
Following ANSSI recommendations R1-R4 from the guide "Multi-factor authentication and passwords" (v2, October 2021), multi-factor authentication should be offered to strengthen user account security.

Implementation ideas:
- TOTP (RFC 6238): the user scans a QR code with an authenticator app (Google Authenticator, Authy, etc.)
- Endpoint `POST /users/mfa/enable`: generates a TOTP secret, returns the otpauth:// URI and a QR code
- Endpoint `POST /users/mfa/verify`: validates a TOTP code to activate MFA
- Add an `mfa_enabled` field on the User model
- Modify the authentication flow: after password verification, require a TOTP code if MFA is enabled
- Generate recovery (backup) codes upon activation

Reference: https://cyber.gouv.fr/publications/recommandations-relatives-lauthentification-multifacteur-et-aux-mots-de-passe
