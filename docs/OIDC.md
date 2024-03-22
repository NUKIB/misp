# OpenID Connect (OIDC) login

This Docker image is prepared to use OIDC for login into MISP. To enhance security, OIDC is implemented right into Apache by [mod_auth_openidc](https://github.com/OpenIDC/mod_auth_openidc)
and also in MISP itself. That means that unauthenticated users will stop right on Apache.

If a request to MISP is made with `Authorization` header, that contains an authentication key in MISP format,
OIDC authentication is not used. Instead, Apache checks if a key is valid and let user inside.

## Environment variables

* `OIDC_LOGIN` (optional, boolean, default `false`) - set to `true` to enable OIDC login
* `OIDC_PROVIDER` (required when `OIDC_LOGIN` is `true`, string) - URL for OIDC provider in Apache
* `OIDC_CLIENT_ID` (required when `OIDC_LOGIN` is `true`, string)
* `OIDC_CLIENT_SECRET` (required when `OIDC_LOGIN` is `true`, string)
* `OIDC_AUTHENTICATION_METHOD` (optional, string, default `client_secret_basic`) - should be set to `client_secret_jwt` if identity provider supports that method, because it is more secure
* `OIDC_CODE_CHALLENGE_METHOD` (optional, string) - can be set to `plain` or `S256`, but this method must be supported by the identity provider
* `OIDC_PASSWORD_RESET` (optional, string) - URL to password reset page
* `OIDC_CLIENT_CRYPTO_PASS` (required when `OIDC_LOGIN` is `true`, string) - password used for cookie encryption by Apache, should be at least 32 chars long
* `OIDC_DEFAULT_ORG` (optional, string) - default organisation name for a user that doesn't have organisation name in claim defined by `OIDC_ORGANISATION_PROPERTY` variable. If not provided `MISP_ORG` will be used. Value should be organisation ID, name or UUID.
* `OIDC_ROLES_PROPERTY` (optional, string, default `roles`) - name of claim used for user roles in MISP
* `OIDC_ROLES_MAPPING` (optional, string, default see bellow) - roles mapping from roles provided by IdP to MISP roles
* `OIDC_ORGANISATION_PROPERTY` (optional, string, default `organization`) - ID token or user info claim that will be used as an organisation in MISP. This property should contain organisation ID, name or UUID.
* `OIDC_OFFLINE_ACCESS` (optional, boolean, default `false`) - if true, offline access token will be requested for user
* `OIDC_CHECK_USER_VALIDITY` (optional, int, default `0`) - number of seconds, after which user will be revalidated if he is still active in IdP. Zero means that this functionality is disabled. Recommended value is `300`.
* `OIDC_UPDATE_USER_ROLE` (optional, bool, default `true`) - if disabled, manually modified role in MISP admin interface will be not changed from roles defined in OIDC
* `OIDC_TOKEN_SIGNED_ALGORITHM` (optional, string) - can be any of `RS256|RS384|RS512|PS256|PS384|PS512|HS256|HS384|HS512|ES256|ES384|ES512`, the algorithms supported by `mod_auth_openidc` (the Apache OIDC-module), leaving empty will make `mod_auth_openidc` default to `RS256` 

### Inner

You can use a different provider for authentication in MISP. If you don't provide these variables, they will be set to the same as for Apache.

* `OIDC_PROVIDER_INNER` (optional, string, default value from `OIDC_PROVIDER`) - URL for OIDC provider in MISP
* `OIDC_CLIENT_ID_INNER` (optional, string, default value from `OIDC_CLIENT_ID`)
* `OIDC_CLIENT_SECRET_INNER` (optional, string, default value from `OIDC_CLIENT_SECRET`)
* `OIDC_AUTHENTICATION_METHOD_INNER` (optional, string, default value from `OIDC_AUTHENTICATION_METHOD`)
* `OIDC_CODE_CHALLENGE_METHOD_INNER` (optional, string, default value from `OIDC_CODE_CHALLENGE_METHOD_INNER`)
* `OIDC_ROLES_PROPERTY_INNER` (optional, string, default value from `OIDC_ROLES_PROPERTY`)

## User Roles

You can set the user role in MISP by modifying `roles` claim in OIDC provider. By default, every user that wants to access
MISP must be assigned to one of these roles:

```php
[
   'misp-admin-access' => 1, // Admin
   'misp-org-admin-access' => 2, // Org Admin
   'misp-sync-access' => 5, // Sync user
   'misp-publisher-access' => 4, // Publisher
   'misp-api-access' => 'User with API access',
   'misp-access' => 3, // User
]
```

If you want to modify this setting, you have to modify `OIDC_ROLES_MAPPING` value. Default value is:

```
misp-admin-access=1,misp-org-admin-access=2,misp-sync-access=5,misp-publisher-access=4,misp-api-access=User with API access,misp-access=3
```

The format is `<IdP ROLE NAME>=<MISP ROLE ID OR NAME>` or also JSON string can be provided where key is IdP Role name and value MISP Role ID or Name.

## User Organisation

You can provide OIDC claim `organization` to a user, which can contain organisation name or UUID. If this claim exists,
MISP will assign a user to that organisation.

## Caveats

### User blocking

When a user is blocked in identity provider, he will be not blocked in MISP. That means that he can not login to login, but
an API authentication key will still work and also notification e-mail will be still sent to his e-mail address.

To solve this, OIDC comes with offline tokes. You can enable them by setting `OIDC_OFFLINE_ACCESS` variable to true. 
When the user will  be login, an offline token will be saved to the database. With this token, MISP can check if 
a user is still valid or update user role or organisation.

If you want to block users that are no longer valid, you have to set `OIDC_CHECK_USER_VALIDITY` variable to a number
of seconds that user will be checked if he is still valid. If not or offline token was revoked, user will be blocked until
he will login to MISP again with valid account. 

### Logout

The problem with OpenID Connect is that if a user logout from one service, he will still be logged in to another service.
This can be fixed by Backchannel logout, but currently is not supported in this image.

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
OIDC_OFFLINE_ACCESS=yes
OIDC_CHECK_USER_VALIDITY=600
```
