# S3 support

## Setup
Set the following environmental variables in the container (e.g. by adding them to `docker-compose.yml` if using docker compose):

| Env var | Type | Description | Required |
| -- | -- | -- | -- |
| S3_ENABLED | bool | | yes |
| S3_AWS_COMPATIBLE | bool | Use external AWS compatible system such as MinIO |
| S3_CA | str | AWS TLS CA, set to empty to use CURL internal trusted certificates or path for custom trusted CA |
| S3_VALIDATE_CA | bool | Validate CA |
| S3_AWS_ENDPOINT | str | Uses external AWS compatible endpoint such as MinIO | 
| S3_BUCKET_NAME | str | Bucket name to upload to, please make sure that the bucket exists. | yes |
| S3_REGION | str | Region in which your S3 bucket resides |
| S3_ACCESS_KEY | str | AWS key to use when uploading samples | yes* |
| S3_SECRET_KEY | str | AWS secret key to use when uploading samples | yes* |

\* Required unless you're running MISP on EC2. If so, follow step 2a in [MISP's own documentation for S3 support](https://github.com/MISP/MISP/blob/2.4/docs/CONFIG.s3-attachments.md) instead. 

*Note: The AWS access/secret must belong to a user with readwrite permissions.*

#### Value hierarchy
The environmental variables set values in `config.php`. Changes made in the UI are stored in the database, and prioritised over those in `config.php`. 

## Example of local setup


### Spin up a MinIO container 
- Use docker (or podman) to spin up a container
```
docker run --name minio -p 9000:9000 -p 9001:9001 -d quay.io/minio/minio server /data --console-address ":9001"
```

- Next, you need to create a bucket and an access/secret key pair.
    - Go to http://localhost:9001, log in with default user "minioadmin" and password "minioadmin". 
    - Go to Administrator > Buckets and create a new bucket. 
    - Go to Administrator > Identity > User and create a new user.
    - Click on the new user, then go to Service Accounts and create a new access key for the user.

### Spin up MISP container  
- Fetch `docker-compose.yml` if you haven't already:
```
curl --proto '=https' --tlsv1.2 -O https://raw.githubusercontent.com/NUKIB/misp/main/docker-compose.yml
```

- Either add env vars in the `docker-compose.yml` file, like e.g.:
```
...
 environment:
      MYSQL_HOST: mysql
      MYSQL_LOGIN: misp
      MYSQL_PASSWORD: password # Please change for production
      ...
      S3_ENABLED: true
      S3_AWS_COMPATIBLE: true
      S3_AWS_ENDPOINT: http://<minio container ip*>:9001
      S3_BUCKET_NAME: <your bucket>
      S3_ACCESS_KEY: <your key>
      S3_SECRET_KEY: <your secret>
...
```
...or create an env vars file named `.env_s3` and fill it with the required env vars.


- Run docker compose:
```
docker compose up -d
```


**MinIO's container IP is in this case your host IP. You can set it to minio (so: `http://minio:9000`) instead by connected the MinIO container to same network the MISP container is using.*
```
docker network disconnect bridge minio
docker network connect misp_default minio
```


## Warnings from misp/MISP

When visiting Administration > Server Settings & Maintenance, four warnings will most likely pop up on top of the screen, looking like this:

```
Warning (2): file_exists(): Unable to find the wrapper &quot;s3&quot; - did you forget to enable it when you configured PHP? [APP/Model/Server.php, line 3477]

Warning (2): mkdir() [<a href='http://php.net/function.mkdir'>function.mkdir</a>]: Unable to find the wrapper &quot;s3&quot; - did you forget to enable it when you configured PHP? [APP/Model/Server.php, line 3479]

Warning (2): mkdir() [<a href='http://php.net/function.mkdir'>function.mkdir</a>]: Permission denied [APP/Model/Server.php, line 3479]

Warning (2): is_writable() [<a href='http://php.net/function.is-writable'>function.is-writable</a>]: Unable to find the wrapper &quot;s3&quot; - did you forget to enable it when you configured PHP? [APP/Model/Server.php, line 3483]
```

__You can ignore these__. They all appear as a consequence of MISPs internal "are directories writeable" check (the writeableDirsDiagnostics function), which does not take external directories into consideration.

## Error when trying to upload attachment?
 - **Check that the address to the S3 storage is correct**: it should be an IP-address, a public DNS, or (if local setup as described previously) a container name. 

 - **Check that the S3 key and secret are correct**. If building and rebuilding a local setup, make sure to not only destroy the containers but also the database created - it stores the S3 key and secret, and misp values database content over given input. 