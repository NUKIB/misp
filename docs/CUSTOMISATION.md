# How to customise MISP

You can create your own MISP image based on NUKIB image, that will include your customisations.

## Additional environment variables

* `MISP_CUSTOM_CSS` (optional, string) - filename from `/var/www/MISP/app/webroot/css/` directory that will be used as another CSS file
* `MISP_TERMS_FILE` (optional, string) - filename from `/var/www/MISP/app/files/terms/` directory
* `MISP_HOME_LOGO` (optional, string) - filename from `/var/www/MISP/app/webroot/img/custom/` directory that will be used as home logo
* `MISP_FOOTER_LOGO` (optional, string) - filename from `/var/www/MISP/app/webroot/img/custom/` directory that will be used as footer logo

## Example Dockerfile

```dockerfile
FROM ghcr.io/nukib/misp

COPY org-images/* /var/www/MISP/app/webroot/img/orgs/
COPY img/* /var/www/MISP/app/webroot/img/custom/
COPY custom.css /var/www/MISP/app/webroot/css/
COPY terms.html /var/www/MISP/app/files/terms/

ENV MISP_CUSTOM_CSS custom.css
ENV MISP_HOME_LOGO misp.svg
ENV MISP_FOOTER_LOGO footer.svg
ENV MISP_TERMS_FILE terms.html
```
