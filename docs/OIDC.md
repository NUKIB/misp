# OpenID Connect (OIDC) login

This Docker image is prepared to use OIDC for login into MISP. To enhance security, OIDC is implemented right into Apache by [mod_auth_openidc](https://github.com/zmartzone/mod_auth_openidc)
and also in MISP itself. That means that unauthenticated users will stop right on Apache.

If a request to MISP is made with `Authorization` header, that contains an authentication key in MISP format, 
OIDC authentication is not used. Instead, Apache checks if a key is valid and let user inside.

## Environment variables

* `OIDC_LOGIN` (optional, bool, default `false`) - set to `true` to enable OIDC login
* `OIDC_PROVIDER` (optional, string) - URL for OIDC provider in Apache
* `OIDC_CLIENT_ID` (optional, string)
* `OIDC_CLIENT_SECRET` (optional, string)
* `OIDC_AUTHENTICATION_METHOD` (optional, string, default `client_secret_basic`) - should be set to `client_secret_jwt` if identity provider supports that method, because it is more secure
* `OIDC_CODE_CHALLENGE_METHOD` (optional, string) - can be set to `plain` or `S256`, but this method must be supported by identity provider
* `OIDC_PASSWORD_RESET` (optional, string) - URL to password reset page
* `OIDC_CLIENT_CRYPTO_PASS` (optional, string) - password used for cookie encryption by Apache
* `OIDC_DEFAULT_ORG` (optional, string) - default organisation name for new user that don't have organisation name in `organization` claim. If not provided `MISP_ORG` will be used.
* `OIDC_ORGANISATION_PROPERTY` (optional, string, default `organization`) - ID token claim that will be used as organisation in MISP

### Inner

You can use a different provider for authentication in MISP. If you don't provide these variables, they will be set to the same as for Apache.

* `OIDC_PROVIDER_INNER` (optional, string, default value from `OIDC_PROVIDER`) - URL for OIDC provider in MISP
* `OIDC_CLIENT_ID_INNER` (optional, string, default value from `OIDC_CLIENT_ID`)
* `OIDC_CLIENT_SECRET_INNER` (optional, string, default value from `OIDC_CLIENT_SECRET`)
* `OIDC_AUTHENTICATION_METHOD_INNER` (optional, string, default value from `OIDC_AUTHENTICATION_METHOD`)
* `OIDC_CODE_CHALLENGE_METHOD_INNER` (optional, string, default value from `OIDC_CODE_CHALLENGE_METHOD_INNER`)

## User Roles

You can modify user role in MISP by modifying `role` claim in OIDC provider. By default, every user that wants to access must be
assigned to `misp-access` role. 

```php
[
   'misp-admin-access' => 1, // Admin
   'misp-org-admin-access' => 2, // Org Admin
   'misp-sync' => 5, // Sync user
   'misp-publisher-access' => 4, // Publisher
   'misp-api-access' => 'User with API access',
   'misp-access' => 3, // User
]
```

## User Organisation

You can provide OIDC claim `organization` to user, that can contains organisation name or UUID. If this claim exists, 
MISP will assign user to that organisation.

## Example usage with [Keycloak](https://www.keycloak.org)

### Configure new client in Keycloak

1) Create new client
   1) Client ID: `misp` (or anything else)
   2) Client Protocol: `openid-connect`
   3) Root URL: full URL of your installation
   4) Save
2) On client setting page:
   1) Access Type: `confidential`
   2) Save
3) Credentials
   1) Client Authenticator: `Signed Jwt with Client secret` (more secure than default `Client Id and Secret`)
   2) Copy secret
4) Add role
   1) Roles
   2) Add Role
   3) Role Name: `misp-access`
   4) Save
5) Assign role `misp-access` to users that should be able to access MISP
   
### Configure MISP environment

```bash
OIDC_LOGIN=yes
OIDC_PROVIDER=https://<keycloak>/auth/realms/<realm>/
OIDC_CLIENT_ID=misp
OIDC_CLIENT_SECRET=<client_secret>
OIDC_AUTHENTICATION_METHOD=client_secret_jwt
OIDC_CODE_CHALLENGE_METHOD=S256
OIDC_CLIENT_CRYPTO_PASS=<random string>
```
