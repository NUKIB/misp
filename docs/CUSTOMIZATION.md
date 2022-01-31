# How to customize MISP image

You can create your MISP image based on NUKIB image, which will include your customizations.

## Additional environment variables for visual changes

* `MISP_CUSTOM_CSS` (optional, string) - filename from `/var/www/MISP/app/webroot/css/` directory that will be used as another CSS file
* `MISP_TERMS_FILE` (optional, string) - filename from `/var/www/MISP/app/files/terms/` directory
* `MISP_HOME_LOGO` (optional, string) - filename from `/var/www/MISP/app/webroot/img/custom/` directory that will be used as home logo
* `MISP_FOOTER_LOGO` (optional, string) - filename from `/var/www/MISP/app/webroot/img/custom/` directory that will be used as footer logo

## Add custom certificates

This image uses by default TLS system certificates. If you use custom certificate authority that is not trusted in
base image, just copy that certificate in PEM format to `/etc/pki/ca-trust/source/anchors/` directory and run
`update-ca-trust` command.

## Example

Create a new file `Dockerfile` in a new directory and copy your customization files:

```dockerfile
# Based on original NUKIB image
FROM ghcr.io/nukib/misp

# Include custom CA to system certificates
COPY cert.pem /etc/pki/ca-trust/source/anchors/
RUN update-ca-trust

# Copy additional organization logos
COPY org-images/* /var/www/MISP/app/webroot/img/orgs/
# Copy custom images, thatcan be used as home or footer logo
COPY img/* /var/www/MISP/app/webroot/img/custom/
# Copy custom CSS,  
COPY custom.css /var/www/MISP/app/webroot/css/
# Copy custom terms
COPY terms.html /var/www/MISP/app/files/terms/

ENV MISP_CUSTOM_CSS custom.css
ENV MISP_HOME_LOGO misp.svg
ENV MISP_FOOTER_LOGO footer.svg
ENV MISP_TERMS_FILE terms.html
```

Then to create a custom image, call this command in the directory that contains created `Dockerfile`.

```bash
docker build -t misp-custom .
```

After the build, you can use your custom image by changing the image definition for MISP container in `docker-compose.yml`
or by running the command in the directory that contains `docker-compose.yml` file.

```bash
MISP_IMAGE=misp-custom docker compose up -d
```
