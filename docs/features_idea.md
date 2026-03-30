# Security improvements
1. Password politics should be enforced by the application, not by the client.
Défine environment variables for password policies.
✔️ Min 12 caractères
✔️ 1 minuscule, 1 majuscule, 1 chiffre, 1 spécial


2. Créer une feature de modification de mot de passe


3. Le POST /users/activate ne doit pas renvoyer de détail le pattern de code
Actuellement on a : 
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
Uniquement dans le cas d'erreur sur le pattern du code, il faudrait renvoyer uniquement : 
```json
{
  "detail": "The activation code is invalid",
  "error_code": "INVALID_ACTIVATION_CODE"
}
```
