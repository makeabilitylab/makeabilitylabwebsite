# Makeability Lab Website
The [Makeability Lab](https://makeabilitylab.cs.washington.edu) is an HCI/Ubicomp research lab at the University of Washington directed by Professor Jon Froehlich. Founded in 2012 by Froehlich and students, the Makeability Lab focuses on designing and studying novel interactive experiences that cross between bits and atoms—the virtual and the physical—and back again to confront some of the world's greatest challenges in environmental sustainability, health and wellness, education, and universal accessibility. 

This repository contains the [Makeability Lab's website](https://makeabilitylab.cs.washington.edu), which is written in Django (backend) and Bootstrap/Javascript (frontend).

# Table of Contents
* [Adding Content Manually](#adding-content-manually)
* [Bootstrapping Content](#bootstrapping-content)
* [Test and Production Servers](#test-and-production-servers)
* [Deploying Code to UW Servers](#deploying-code-to-uw-servers)
* [Makeability Lab Data](#makeability-lab-data)
* [Makeability Lab API](#makeability-lab-api)
* [Manual Installation](#manual-installation)
* [Contributing](#contributing)
* [Troubleshooting](#troubleshooting)


# Docker Installation (Mac)
1. Install [Docker Desktop](https://www.docker.com/get-started)

3. Run `> docker version` from terminal to ensure Docker is running 
  
2. Clone this repository using `git clone https://github.com/jonfroehlich/makeabilitylabwebsite.git` and navigate to the project home directory using the `cd` command.

3. Build the docker images. Run `docker build .` or `docker build . -t <tag>`--the latter allows you to tag your build with a name (we recommend tagging it as `makelab_image` for easy access). This step takes a while the first time (~2-3 min). If you don't add a tag to your build in step 3, you can look at the last line of the build that says `Successfully built <tag>` to get your tag.

4. Running the container. Once the image has built, run `docker-compose up`, this will bring up both the postgres container for the database and the website containers. For future reference, running `docker-compose up -d` will allow you to continue using the same terminal and none of the output messages will be displayed.

5. Create the superuser. In another terminal, navigate to the project home directory using the `cd` command and open an interactive bash terminal in the website container using `docker exec -it makeabilitylabwebsite_website_1 bash`. Once inside the bash terminal, run `python manage.py createsuperuser`.

6. Open the development server in the web browser. At this point the development server should be running via step 4. You will find the website at `localhost:8571` as specified in the `docker-compose.yml` file.

7. Shutting down the server. In another terminal at the project home directory run `docker-compose down` and wait for the containers to shut-down. Note without running this command, the development server will persist even when you close down the terminal, thus preventing you from using port 8571 for other purposes.

After running the `docker-compose up` command, you will not need to rebuild or rerun the Docker container (unless you have made changes to docker-compose.yml). However, you will still need to refresh the webpage in order to see new updates.

### Sample setup:
```
git clone https://github.com/jonfroehlich/makeabilitylabwebsite.git
cd makeabilitylabwebsite/
docker build . -t makelab_image
docker-compose up
```
You should then be able to visit the server at `http://localhost:8571/`.

In new terminal (navigate to the project home directory)
```
docker exec -it makeabilitylabwebsite_website_1 bash
python manage.py createsuperuser
exit
```

# Docker Installation (Windows)

On Windows, [WSL2](https://docs.microsoft.com/en-us/windows/wsl/install) provides an actual Linux kernel running within a lightweight VM, unlike the older WSL which tried to emulate a linux kernel within the Windows kernel—see [Docker's official WSL2 overview](https://docs.docker.com/desktop/windows/wsl/). WSL2 offers faster compile times and is better supported by Docker.

1. [Install  Docker Desktop](https://www.docker.com/get-started). Follow the official [Docker Windows Install Guide](https://docs.docker.com/desktop/windows/install/).
1. [Install WSL2](https://docs.microsoft.com/en-us/windows/wsl/install-win10).
1. Enter the Docker Dashboard and click the settings gear icon in the top right. From there, click the "General" tab and select the "Use the WSL 2 based engine" check box (this will be grayed out and pre-checked if you're running Windows Home).
1. Proceed by clicking **Resources &rarr; WSL Integration** and select your Linux VM of choice under "Enable integration with additional distros:". Here is some extra [documentation](https://docs.docker.com/docker-for-windows/wsl/) from Docker that may help out with this process.
1. Open your Linux VM shell and navigate to where you would like to set up your Makeability Lab website repository.
1. Run `git clone https://github.com/makeabilitylab/makeabilitylabwebsite.git`.
1. Make sure to `chmod 755 docker-entrypoint.sh`
1. You must also manually create some directories:
    ```
    mkdir static
    chmod -R 777 static/
    mkdir website/migrations
    chmod -R 777 website/
    ```

1. Build the docker images. Run `docker build .` or `docker build . -t <tag>`--the latter allows you to tag your build with a name (we recommend tagging it as `makelab_image` for easy access). This step may take a while (~2-3 min). If you don't add an explicit tag to your build, you can look at the last line of the build that says `Successfully built <tag>` to get your tag.

1. Running the container. Once the image has built, run `docker-compose up`, this will bring up both the PostgreSQL container for the database and the website containers. 

1. At this point, you can visit the website at `localhost:8571` as specified in the `docker-compose.yml` file. However, to add content, you need to add an admin users. For this, follow the next step to create a "superuser."

1. Create the superuser. In another terminal, navigate to the project home directory using the `cd` command and open an interactive bash terminal in the website container using `docker exec -it makeabilitylabwebsite_website_1 bash`. Once inside the bash terminal, run `python manage.py createsuperuser` and follow the instructions. Then you can visit localhost:8571/admin to add content.

1. It's also useful to create a mapping between your Linux filesystem in WSL2 and your Windows filesystem. For this, type `Windows + R` to open the Run menu and type: `\\wsl$`. Then, find the Linux installation you're using for the Makeability Lab website (e.g., Ubuntu-18.04) and right-click on that folder, then select `Map Network Drive` and follow the on-screen instructions. By default, it will map to drive `Z:`. So, you can open "This PC" or "My Computer" and see drive `Z:`, which will be the Linux VM.

# Adding Content
Content must be added manually.

NOTE: If you haven't created a superuser yet, you will need to do so through terminal. Refer to Step 6 in the Docker Installation for more information.

1. Once the website is running on your local machine, go to `localhost:8000/admin` in your browser. This will take you to the Django admin interface.
2. Login using the credentials of the superuser created in the previous step.
3. Once logged in, you will see two main headers. Listed under the "WEBSITE" header, there will be a number of folders relating to the various types of content that make up the Makeability website.
4. Chose the folder corresponding to the content you wish to upload. Inside the folder, in the upper right of the screen, there will be an ADD button.
5. Follow what information is needed to create that content for the website in your local development environment.

TIP: Save time by only adding the content needed to fix the issue you are working on.

# Test and Production Servers
We have two UW servers hosting the ML website: https://makeabilitylab-test.cs.washington.edu (test) and https://makeabilitylab.cs.washington.edu (production). They have different PostgresSQL backends so adding content to -test will not affect the production server and vice versa. 

# Deploying Code to UW Servers
The Makeability Lab website auto-deploys from GitHub to the department's Docker infrastructure using webhooks:
![webhooks_screenshot](https://github.com/jonfroehlich/makeabilitylabwebsite/blob/master/readme/webhooks_screenshot.png "Webhooks Screenshot") When we push code to github, the new code will auto-deploy to makeabilitylab-test. When we are ready to push changes to production, we need to do the following:
```
git tag <my version number>
git push --tags
```
This will cause that tag to deploy to production. To verify that the code has actually been pushed to production, view the `buildlog.txt` [here](https://makeabilitylab.cs.washington.edu/logs/buildlog.txt).

## Versioning
We will using semantic versioning when adding tags to push to production. The table below gives instructions for how semantic labeling works. More information is available [here](https://docs.npmjs.com/getting-started/semantic-versioning).

The current version number can be viewed [here](https://github.com/jonfroehlich/makeabilitylabwebsite/releases) along with a history of all previous releases. 

| Code Status    | Stage        | Rule             | Example # |
| -------------- | ------------ | ---------------- | --------- |
| First Release  | New Product  | Start with 1.0.0 | 1.0.0     |
| Bug fixes, other </br> minor changes  | Patch release | Increment the third digit | 1.0.1 |
| New Features that don't </br> break existing features  | Minor release | Increment the middle digit | 1.1.0 |
| Changes that break </br> backwards compatibility | Major release | Increment the first digit | 2.0.0 |

## Configuring the Production Server
The production server was configured largely by UW CSE's Jason Howe. Note that settings.py reads in a config.ini file to configure a connection to the PostgreSQL database. This config.ini file is *not* in git (for obvious reasons as it contains secret keys and passwords). Thus, Jason has setup a "volume mount" for this file so that the production Docker session can read that file.

## Debugging the Production Server
We have logging configured for both makeabilitylab-test.cs.washington.edu and makeabilitylab.cs.washington.edu.

- ssh into `recycle.cs.washington.edu`
- For the test server, cd to `/cse/web/research/makelab/www-test` and view `debug.log`
- For the production server, cd to `/cse/web/research/makelab/www` and view `debug.log`
- Alternatively, if you have Windows dir mapping setup, you can visit `O:\cse\web\research\makelab`

Because the log files are so large, use the `tail` command to view the end of the log file. For example, `tail -n 100 debug.log` will display the last 100 lines in the log file. You can also dump this to a new file: `tail -n 100 debug.log > last100lines.log`

You can also view `buildlog.text`, `httpd-access.log`, and `httpd-error.log` at https://makeabilitylab-test.cs.washington.edu/logs/ and https://makeabilitylab.cs.washington.edu/logs/.

# Makeability Lab Data
There are two types of Makeability Lab data: (i) uploaded files like PDFs, PowerPoint files, images, etc. and (ii) data that goes into the PostgreSQL database. Although we have both a test (makeability-test.cs) and a production server (makeability.cs), they are linked to the same backend data for both (i) and (ii).

## Uploaded Files
All data/files uploaded to the Makeability Lab website via the admin interface (e.g., talks, publications) goes into the `/media` folder. Although typically you will not ever need to manually access this folder (except, for example, to view the `debug.log`), you can do so by ssh'ing into recycle.cs.washington.edu and cd to `/cse/web/research/makelab/www`. This files area is being mapped into the `/media` folder. This directory is shared by both https://makeabilitylab-test.cs.washington.edu/ and https://makeabilitylab.cs.washington.edu/.

## Access to Production Database Server
The Makeability Lab website uses PostgreSQL on production, which is running on grabthar.cs.washington.edu. In the (extremely) rare instance that you need to access Postgres directly, you must do so via recycle.cs.washington.edu.

# Contributing
We use the following process for contributing code:
1. We use issues to organize tasks. You may choose to either select an existing issue to work on, or add your own. When adding issues, be sure to add tags as necessary. 
2. Assign yourself to an issue and create a branch off `master`. The name of your branch should be descriptive and based off the issue that you are working on. (EX: if you were fixing [this](https://github.com/jonfroehlich/makeabilitylabwebsite/issues/335) issue, an appropriate branch name would be `adding-hover-to-landing-page`). Each branch should address one issue.
3. When you are done working on an issue, submit a pull request. We will do local testing and code reviews before merging it with master.

## Things to keep in mind
Tasks that include changes to the user/admin interface should always include mockups. This is so we can collectively agree on how we want the site to look. A good example is [here](https://github.com/jonfroehlich/makeabilitylabwebsite/issues/287). Pull requests should also include before/after images, when applicable.

# Troubleshooting

## Cannot start service website: OCI runtime create failed
If you receive an error like this

```
jonfroehlich@jonfhome:~/git/makeabilitylabwebsite$ docker-compose up
makeabilitylabwebsite_db_1 is up-to-date
Starting makeabilitylabwebsite_website_1 ... error

ERROR: for makeabilitylabwebsite_website_1  Cannot start service website: OCI runtime create failed: container_linux.go:380: starting container process caused: exec: "./docker-entrypoint.sh": permission denied: unknown

ERROR: for website  Cannot start service website: OCI runtime create failed: container_linux.go:380: starting container process caused: exec: "./docker-entrypoint.sh": permission denied: unknown
ERROR: Encountered errors while bringing up the project.
```

Then you need to update some permissions on your configuration files. Try:

```
chmod 755 docker-entrypoint.sh
```

## standard_init_linux.go:228: exec user process caused: no such file or directory

If you receive an error like:

```
website_1  | standard_init_linux.go:228: exec user process caused: no such file or directory
```

Then the line endings in the shell script are set to CRLF rather than LF (see [StackOverflow post](https://stackoverflow.com/a/52665687/388117)). 

To fix this, open `docker-entrypoint.sh` in VSCode and set the line endings to LF.


