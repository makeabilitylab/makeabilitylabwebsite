# Makeability Lab Website
The [Makeability Lab](https://makeabilitylab.cs.washington.edu) is a an HCI/Ubicomp research lab at the University of Washington directed by Professor Jon Froehlich. Founded in 2012 by Froehlich and students, the Makeability Lab focuses on designing and studying novel interactive experiences that cross between bits and atoms—the virtual and the physical—and back again to confront some of the world's greatest challenges in environmental sustainability, health and wellness, education, and universal accessibility. 

This repository contains the [Makeability Lab's website](https://makeabilitylab.cs.washington.edu), which is written in Django (backend) and Bootstrap/Javascript (frontend).

# Table of Contents
* [Dev Prereqs](#dev-prereqs)
* [Docker Installation (Mac)](#docker-installation-mac)
* [Docker Installation (Windows)](#docker-installation-windows)
* [PyCharm IDE](#pycharm)
* [Adding Content Manually](#adding-content-manually)
* [Bootstrapping Content](#bootstrapping-content)
* [Test and Production Servers](#test-and-production-servers)
* [Deploying Code to UW Servers](#deploying-code-to-uw-servers)
* [Makeability Lab Data](#makeability-lab-data)
* [Makeability Lab API](#makeability-lab-api)
* [Manual Installation](#manual-installation)
* [Contributing](#contributing)
* [Troubleshooting](#troubleshooting)

# Dev Prereqs
While the instructions below walk you through a step-by-step process to configure your machine for developing the Makeability Lab website, here's a summary of the tools we use:
- Docker
- PyCharm
- Git

# Docker Installation (Mac)
1. If you don't have Docker yet, you can download it [here](https://store.docker.com/search?type=edition&offering=community). We use the Community Edition. Open up the application. Run `docker version` to make sure that it is running. 
  
2. Clone this repository using `git clone https://github.com/jonfroehlich/makeabilitylabwebsite.git` and navigate to the project home directory using the `cd` command.

3. Build the docker images. Run `docker build .` or `docker build . -t <tag>`--the latter allows you to tag your build with a name (we recommend tagging it as `makelab_image` for easy access). This step takes a while the first time (~2-3 min). If you don't add a tag to your build in step 3, you can look at the last line of the build that says `Successfully built <tag>` to get your tag.

4. Running the container. Once the image has built, run `docker-compose up`, this will bring up both the postgres container for the database and the website containers. For future reference, running `docker-compose up -d` will allow you to continue using the same terminal and none of the output messages will be displayed.

5. Create the superuser. In another terminal, navigate to the project home directory using the `cd` command and open an interactive bash terminal in the website container using `docker exec -it makeabilitylabwebsite_website_1 bash`. Once inside the bash terminal, run `python manage.py createsuperuser`.

6. Open the development server in the web browser. At this point the development server should be running via step 4. You will find the website at `localhost:8571` as specified in the `docker-compose.yml` file. To fill this with test content for development purposes see Bootstrapping Content below.

7. Shutting down the server. In another terminal at the project home directory run `docker-compose down` and wait for the containers to shut-down. Note without running this command, the development server will persist even when you close down the terminal, thus preventing you from using port 8571 for other purposes.

After running the `docker-compose up` command, you will not need to rebuild or rerun the Docker container (unless you have made changes to docker-compose.yml). However, you will still need to refresh the webpage in order to see new updates.
### Sample setup:
```
git clone https://github.com/jonfroehlich/makeabilitylabwebsite.git
cd makeabilitylabwebsite/
docker build . -t makelab_image
docker-compose up
```
In new terminal (navigate to the project home directory)
```
docker exec -it makeabilitylabwebsite_website_1 bash
python manage.py createsuperuser
exit
```

# Docker Installation (Windows)
1. If you don't have Docker yet, you can download it [here](https://store.docker.com/search?type=edition&offering=community). We use the Community Edition. If you previously installed Docker, please navigate to the Docker settings, in the window go to the Reset tab and click "Restore Factory defaults". This will ensure that there will be no conflicts in allocating ports later on.

2. During the install, you will be prompted with a Configuration Dialog that will ask whether to use Windows containers instead of Linux containers. Do not check the box.
![InstallingDockerWindows_ConfigScreen](https://github.com/jonfroehlich/makeabilitylabwebsite/blob/master/readme/InstallingDockerWindows_ConfigScreen_UseWindowsContainersCheckbox.png)

3. Go to the Start Menu and open `Docker for Windows.` If it asks you to enable Hyper-V, you should say Yes and restart.

4. Open PowerShell, run `docker version` to make sure that it is running. 

5. We need to configure Docker so that our local drives are available to our containers. From the system tray, open Docker -> Settings.  In Settings, navigate to the "Shared Drives" tab and select the drive that will host the Makeability Lab code/server. Click "Apply" and you will be prompted to enter the password for your machine.
[![https://gyazo.com/16d374eeadcd0cc550b8ab17f4bcbe5f](https://i.gyazo.com/16d374eeadcd0cc550b8ab17f4bcbe5f.gif)](https://gyazo.com/16d374eeadcd0cc550b8ab17f4bcbe5f)

6. Before you clone the repository, run this command `git config --global core.autocrlf false` in the directory you will be cloning the repository to. Windows crlf is unrecognized in Linux, thus we must set this auto-conversion as false to prevent look-up errors. If you don't do this, your dev environment will not work (see this [Issue](https://github.com/jonfroehlich/makeabilitylabwebsite/issues/429#issuecomment-406443833))

7. Clone this repository using `git clone https://github.com/jonfroehlich/makeabilitylabwebsite.git` and navigate to the project home directory using the `cd` command.

8. Build the docker images. Run `docker build .` or `docker build . -t <tag>`--the latter allows you to tag your build with a name (we recommend tagging it as `makelab_image` for easy access). This step takes a while the first time (~2-3 min). If you don't add a tag to your build in step 3, you can look at the last line of the build that says `Successfully built <tag>` to get your tag.

9. Running the container. Once the image has built, run `docker-compose up`, this will bring up both the postgres container for the database and the website containers. For future reference, running `docker-compose up -d` will allow you to continue using the same terminal and none of the output messages will be displayed.

10. Create the superuser. In another terminal, navigate to the project home directory using the `cd` command and open an interactive bash terminal in the website container using `docker exec -it makeabilitylabwebsite_website_1 bash`. Once inside the bash terminal, run `python manage.py createsuperuser`.

11. Open the development server in the web browser. At this point the development server should be running via step 4. You will find the website at `localhost:8571` as specified in the `docker-compose.yml` file. To fill this with test content for development purposes see Bootstrapping Content below.

12. Shutting down the server. In another terminal at the project home directory run `docker-compose down` and wait for the containers to shut-down. Note without running this command, the development server will persist even when you close down the terminal, thus preventing you from using port 8571 for other purposes.

After running the `docker-compose up` command, you will not need to rebuild or rerun the Docker container (unless you have made changes to docker-compose.yml). However, you will still need to refresh the webpage in order to see new updates.

### Sample setup:
```
# navigate to the directory you will be cloning the repository into
git config --global core.autocrlf false
git clone https://github.com/jonfroehlich/makeabilitylabwebsite.git
cd .\makeabilitylabwebsite\
docker build . -t makelab_image
docker-compose up
```
In new terminal (navigate to the project home directory)
```
docker exec -it makeabilitylabwebsite_website_1 bash
python manage.py createsuperuser
exit
```

### Manual Installation (In the event that Docker fails to run)
Proceed to the manual installation instructions [here](https://docs.google.com/document/d/1LJPSSZA0kLzUX34pq4TgYP406bGH_1JhBtFLEPax7a8/edit?usp=sharing)

# PyCharm
We recommend using PyCharm as an IDE. You can use PyCharm regardless of whether you setup PyCharm to run directly with Docker or to run the website server. (Note: Jon uses PyCharm for dev but not with Docker integration or to run the website server).

## Configuring PyCharm to run with Docker (optional)
Note that in order to configure PyCharm with Docker, you must have the professional version. Students can get this for free at: https://www.jetbrains.com/student/. 

1. You must first configure Docker. Right click on Docker->Settings and then enable daemon on tcp://localhost:2375 [link](https://intellij-support.jetbrains.com/hc/en-us/community/posts/207465185-Pycharm-Docker-and-connection-refused)
1. Then, in Pycharm, select 'Open New Project'. Select the root directory of this project for the file.
2. Go to Run > Edit Configurations. In the side window, go to Defaults > Docker > Dockerfile.
3. Click on the `...` by Server. Select the `Docker for [your OS here]` option. Click `OK` to finish.
4. Click on the `+` button in the upper-left corner to add a new configuration.
5. Set the name to be `makeabilitylabwebsite`, the Dockerfile to be `Dockerfile` with the drop-down menu, and the image tag to `pycharm`. Click `OK` to finish.
6. Select Run > Run 'makeabilitylabwebsite'.
7. Go to Pycharm > Preferences > Project Interpreter
8. Click on the Gear button to the right of the Project Interpreter. Select the `Add...` button.
9. Open the Docker option. The Image Name should be `pycharm:latest`. Click `OK` to finish.

## Configuring PyCharm to run the website server (optional)
You may choose to use either the Terminal or PyCharm to run the website server. The benefit of running the website server via PyCharm is that you can set breakpoints and use the IDE for debugging. (Note: Jon has never done this--I just run the website server from terminal).

NOTE: If you haven't created a superuser yet, you will need to do so through terminal. Refer to Step 6 in the Docker Installation for more information.

1. Go to Run > Run 'makeabilitylabwebsite'. The initial setup for this might take a minute or so.
2. Go to the Docker toolbar. (This should pop up automatically on the bottom of your screen). Click on the dropdown menu for images. Press create container and select `pycharm:latest`. Set the Container name to be `pycharm-web-container`. 
3. Click on the `...` button by Bind Ports. Click the `+` button, and select the Host Port to be `8000` and the Container Port to be `8000`. Click OK to finish.
4. Click on the `...` button by Bind Ports. Click the `+` button, and select the Host path to be `database` and the Container path to be `/code/db`. (Windows users may need to switch the Container path to `\code\db`).
5. Click the `+` button again. Under Host path, click the `...` button. Select the media directory. Select the Container path to be `/code/media`. (Windows users may need to switch the Container path to `\code\media`).
6. Right click on `pycharm-web-container`. Click 'Start container' to run and 'Stop container' to stop the local server. (The attached consoles isn't interactive, so ctrl+c doesn't work here)

# Adding Content Manually
Content must be added manually until the bootstrapping code is fixed.

NOTE: If you haven't created a superuser yet, you will need to do so through terminal. Refer to Step 6 in the Docker Installation for more information.

1. Once the website is running on your local machine, go to `localhost:8000/admin` in your browser. This will take you to the Django admin interface.
2. Login using the credentials of the superuser created in the previous step.
3. Once logged in, you will see two main headers. Listed under the "WEBSITE" header, there will be a number of folders relating to the various types of content that make up the Makeability website.
4. Chose the folder corresponding to the content you wish to upload. Inside the folder, in the upper right of the screen, there will be an ADD button.
5. Follow what information is needed to create that content for the website in your local development environment.

TIP: Save time by only adding the content needed to fix the issue you are working on.

# Bootstrapping Content
To support quickly adding content for development, we have two automated tools that download data from Jon’s UMD website. 

1. Go into the Docker shell, run `make shell`. If you're on Windows and can't use the Makefile, just type this in instead `docker run -ti -v ${pwd}/db:/code/db -v ${pwd}/media:/code/media --entrypoint=bash`
2. Now, to import pubs, run `python3 manage.py importpubs`
3. To import talks, run `python3 manage.py importtalks`

Alternate commands:
1. To import pubs, run `docker run -ti -v ${pwd}/db:/code/db -v ${pwd}/media:/code/media --entrypoint=python makelab_image manage.py importpubs` for Windows and `docker run -ti -v $(pwd)/db:/code/db -v $(pwd)/media:/code/media --entrypoint=python makelab_image manage.py importpubs` for Mac
2. To import talks, run `docker run -ti -v ${pwd}/db:/code/db -v ${pwd}/media:/code/media --entrypoint=python makelab_image manage.py importtalks` for Windows and `docker run -ti -v $(pwd)/db:/code/db -v $(pwd)/media:/code/media --entrypoint=python makelab_image manage.py importtalks` for Mac

A few notes about this. 
* All publications/talks are downloaded from https://makeabilitylab.cs.washington.edu/ so they must already exist on the official site before being added in this way.
* Authors added using this method are not assigned a position, and so they won’t appear on the People page until one is manually added. However they will be assigned a star wars image.
* The publications will not allow for duplication, so any publications with the same title as an existing one are ignored. This is not true for talks.
* Publications with no PDF are ignored. Talks with no PDF and no slide deck are ignored, however talks with only a slide deck will be converted automatically to PDF’s using unoconv (This takes a long time)
* Projects which are specified in the bibtex/xml by project, will be created if necessary. Anyone who is an author or speaker will be added to associated projects, and any keywords from the paper will also be assigned to the project. The above is true of assigned project_umbrellas as well.
 

Importantly, we will have to revise how we do this bootstrapping because Jon's UMD site is going away and because he no longer wants to maintain his own separate backend from the Makeability Lab website (in other words, the ML website will be the sole source of data thus eliminating the source of the bootstrap content). See Issue https://github.com/jonfroehlich/makeabilitylabwebsite/issues/420.

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
There are two types of Makeability Lab data: (i) uploaded files like PDFs, PowerPoint files, images, etc. and (ii) data that goes into the database (SQLite in local dev, PostgreSQL on production). Although we have both a test (makeability-test.cs) and a production server (makeability.cs), they are linked to the same backend data for both (i) and (ii).

# Makeability Lab API
### What it does
A script in the website automatically serializes some models specified in `serializers.py`. The data, in JSON format, is then rendered into an APIView and displayed in a webpage. The entire api framework is housed under the `/api/` url extension. Currently only publications and talks are serialized.

### How to use
There are two ways to call and retrieve the data:
1.	List: will return all of the model objects in the data serialized into JSON
2.	Detail: will return a specific object based on the primary key

##### Publications:
List: `https://makeabilitylab.cs.washington.edu/api/pubs/`
<br>Detail: `https://makeabilitylab.cs.washington.edu/api/pubs/<pk: int>`

##### Talks:
List: `https://makeabilitylab.cs.washington.edu/api/talks/`
<br>Detail: `https://makeabilitylab.cs.washington.edu/api/talks/<pk: int>`

##### News:
List: `https://makeabilitylab.cs.washington.edu/api/news/`
<br>Detail: `https://makeabilitylab.cs.washington.edu/api/news/<pk: int>`

##### Videos:
List: `https://makeabilitylab.cs.washington.edu/api/video/`
<br>Detail: `https://makeabilitylab.cs.washington.edu/api/video/<pk: int>`

##### People:
List: `https://makeabilitylab.cs.washington.edu/api/people/`
<br>Detail: `https://makeabilitylab.cs.washington.edu/api/people/<pk: int>`

##### Projects:
List: `https://makeabilitylab.cs.washington.edu/api/project/`
<br>Detail: `https://makeabilitylab.cs.washington.edu/api/project/<pk: int>`


###### Sample API Calls
To request the pure json version, append `?format=json` to the end of the url. The data will then be rendered in complete JSON without the apiview.
<br>Sample call to `https://makeabilitylab.cs.washington.edu/api/pubs/` returns the following (below JSON only displays one object in a list of many):
```
[
    {
        "id": 477,
        "title": "Evaluating Angular Accuracy of Wrist-based Haptic Directional Guidance for Hand Movement",
        "pdf_file": "http://makeabilitylab.cs.washington.edu/media/publications/Evaluating_Angular_Accuracy_of_Wrist-based_Haptic_Directional_Guidance_for_Hand_Movement_nIxCCJA.pdf",
        "book_title": "Proceedings of the International Conference on Graphics Interface",
        "book_title_short": "Proceedings of GI 2016",
        "thumbnail": "http://makeabilitylab.cs.washington.edu/media/publications/images/Evaluating_Angular_Accuracy_of_Wrist-based_Haptic_Directional_Guidance_for_Hand_Movement_nIxCCJA.jpg",
        "date": "2016-05-01",
        "num_pages": 6,
        "page_num_start": null,
        "page_num_end": null,
        "official_url": null,
        "geo_location": "Victoria, British Columbia",
        "series": "GI '16",
        "isbn": "tbd",
        "doi": "tbd",
        "publisher": null,
        "publisher_address": "New York, NY, USA",
        "acmid": "tbd",
        "pub_venue_type": "Conference",
        "extended_abstract": null,
        "peer_reviewed": true,
        "total_papers_submitted": null,
        "total_papers_accepted": null,
        "award": null,
        "video": null,
        "talk": null,
        "authors": [
            {
                "id": 395,
                "first_name": "Jonggi",
                "middle_name": "",
                "last_name": "Hong",
                "url_name": "jonggihong",
                "email": "jonggi.hong@gmail.com",
                "personal_website": "http://cs.umd.edu/~jghong",
                "github": "",
                "twitter": "",
                "bio": "",
                "next_position": "",
                "next_position_url": "",
                "image": "http://makeabilitylab.cs.washington.edu/media/person/JonggiHong.jpg",
                "easter_egg": "http://makeabilitylab.cs.washington.edu/media/person/Qui_Gon_Jinn_2014_redesign_XhWAVEz.jpg",
                "cropping": "35,37,717,720",
                "easter_egg_crop": "0,0,800,800"
            },
            {
                "id": 351,
                "first_name": "Lee",
                "middle_name": null,
                "last_name": "Stearns",
                "url_name": "leestearns",
                "email": "lstearns@umd.edu",
                "personal_website": "http://www.leestearns.com",
                "github": null,
                "twitter": null,
                "bio": "",
                "next_position": null,
                "next_position_url": null,
                "image": "http://makeabilitylab.cs.washington.edu/media/person/lee_handsight_v1.png",
                "easter_egg": "http://makeabilitylab.cs.washington.edu/media/person/Chewbacca_2014_T2oHMC4.png",
                "cropping": "314,0,1395,1082",
                "easter_egg_crop": "1,1,434,434"
            },
            {
                "id": 396,
                "first_name": "Tony",
                "middle_name": "",
                "last_name": "Cheng",
                "url_name": "tonycheng",
                "email": "",
                "personal_website": "",
                "github": "",
                "twitter": "",
                "bio": "",
                "next_position": "",
                "next_position_url": "",
                "image": "http://makeabilitylab.cs.washington.edu/media/person/09p0311.jpg",
                "easter_egg": "http://makeabilitylab.cs.washington.edu/media/person/Luke_Skywalker_Hoth_O5MmIZV.png",
                "cropping": "0,300,2848,3145",
                "easter_egg_crop": "0,0,219,219"
            },
            {
                "id": 284,
                "first_name": "Jon",
                "middle_name": "E.",
                "last_name": "Froehlich",
                "url_name": "jonfroehlich",
                "email": "jonf@cs.uw.edu",
                "personal_website": "http://www.cs.umd.edu/~jonf/",
                "github": "https://github.com/jonfroehlich",
                "twitter": "https://twitter.com/jonfroehlich?ref_src=twsrc%5Etfw",
                "bio": "I am an Assistant Professor in the Department of Computer Science at the University of Maryland, College Park with an affiliate appointment in the College of Information Studies. I am also a member of the Human-Computer Interaction Laboratory (HCIL), the Institute for Advanced Computer Studies (UMIACS), and the founder of the new HCIL Hackerspace and HCIL research lablet: the Makeability Lab. Research in the Makeability Lab is funded, in part, by a Google Faculty Research Award, a 3M Faculty Award, Nokia, the NSF, and the Department of Defense's Clinical and Rehabilitative Medicine Research Program.",
                "next_position": "",
                "next_position_url": "",
                "image": "http://makeabilitylab.cs.washington.edu/media/person/IMG_9700_cropped2.jpg",
                "easter_egg": "http://makeabilitylab.cs.washington.edu/media/person/Han2014New.jpg",
                "cropping": "0,307,2439,2748",
                "easter_egg_crop": "0,0,400,400"
            },
            {
                "id": 397,
                "first_name": "David",
                "middle_name": "",
                "last_name": "Ross",
                "url_name": "davidross",
                "email": "",
                "personal_website": "",
                "github": "",
                "twitter": "",
                "bio": "",
                "next_position": "",
                "next_position_url": "",
                "image": "http://makeabilitylab.cs.washington.edu/media/person/davidross.jpg",
                "easter_egg": "http://makeabilitylab.cs.washington.edu/media/person/300px-Ani-helmet_as3dPU0.jpg",
                "cropping": "0,32,268,299",
                "easter_egg_crop": "0,0,226,226"
            },
            {
                "id": 278,
                "first_name": "Leah",
                "middle_name": null,
                "last_name": "Findlater",
                "url_name": "leahfindlater",
                "email": "leahkf@umd.edu",
                "personal_website": "https://terpconnect.umd.edu/~leahkf/",
                "github": null,
                "twitter": null,
                "bio": "",
                "next_position": null,
                "next_position_url": null,
                "image": "http://makeabilitylab.cs.washington.edu/media/person/IMG_5190.jpg",
                "easter_egg": "http://makeabilitylab.cs.washington.edu/media/person/Gold_Leader_9495.png",
                "cropping": "0,0,220,220",
                "easter_egg_crop": "0,0,473,473"
            }
        ],
        "projects": [
            {
                "id": 2,
                "name": "HandSight",
                "short_name": "handsight",
                "start_date": "2013-01-01",
                "end_date": null,
                "gallery_image": "http://makeabilitylab.cs.washington.edu/media/projects/images/IMG_3022.JPG",
                "cropping": "588,0,4908,3456",
                "about": "HandSight augments the sense of touch in order to help people with visual impairments more easily access the physical and digital information they encounter throughout their daily lives. It is still in an early stage, but the envisioned system will consist of tiny CMOS cameras and micro-haptic actuators mounted on one or more fingers, computer vision and machine learning algorithms to support fingertip-based sensing, and a smartwatch for processing, power, and speech output. Potential use-cases include reading or exploring the layout of a newspaper article or other physical document, identifying colors and visual textures when getting dressed in the morning, or even performing taps or gestures on the palm or other surfaces to control a mobile phone.",
                "updated": "2016-08-30",
                "sponsors": [],
                "project_umbrellas": [
                    {
                        "id": 2,
                        "name": "Accessibility",
                        "short_name": "accessibility",
                        "keywords": []
                    }
                ],
                "keywords": [
                    {
                        "id": 334,
                        "keyword": "wearables"
                    },
                    {
                        "id": 335,
                        "keyword": "haptics"
                    },
                    {
                        "id": 336,
                        "keyword": "non-visual directional guidance"
                    },
                    {
                        "id": 337,
                        "keyword": "handsight"
                    },
                    {
                        "id": 338,
                        "keyword": "accessibility"
                    },
                    {
                        "id": 360,
                        "keyword": "computer vision"
                    },
                    {
                        "id": 371,
                        "keyword": "blind"
                    },
                    {
                        "id": 466,
                        "keyword": "visual impairments"
                    },
                    {
                        "id": 467,
                        "keyword": "real-time ocr"
                    },
                    {
                        "id": 468,
                        "keyword": "blind reading"
                    },
                    {
                        "id": 514,
                        "keyword": "text reading for blind"
                    },
                    {
                        "id": 540,
                        "keyword": "finger camera"
                    },
                    {
                        "id": 541,
                        "keyword": "touch vision"
                    }
                ]
            }
        ],
        "project_umbrellas": [
            {
                "id": 2,
                "name": "Accessibility",
                "short_name": "accessibility",
                "keywords": []
            }
        ],
        "keywords": [
            {
                "id": 334,
                "keyword": "wearables"
            },
            {
                "id": 335,
                "keyword": "haptics"
            },
            {
                "id": 336,
                "keyword": "non-visual directional guidance"
            },
            {
                "id": 337,
                "keyword": "handsight"
            }
        ]
    },
    ... ]
```

## Uploaded Files
All data/files uploaded to the Makeability Lab website via the admin interface (e.g., talks, publications) goes into the `/media` folder. Although typically you will not ever need to manually access this folder (except, for example, to view the `debug.log`), you can do so by ssh'ing into recycle.cs.washington.edu and cd to `/cse/web/research/makelab/www`. This files area is being mapped into the `/media` folder. This directory is shared by both https://makeabilitylab-test.cs.washington.edu/ and https://makeabilitylab.cs.washington.edu/.

## Access to Production Database Server
The Makeability Lab website uses PostgreSQL on production, which is running on grabthar.cs.washington.edu. In the (extremely) rare instance that you need to access Postgres directly, you must do so via recycle.cs.washington.edu.

# Manual Installation
We strongly advise running the Docker-based installation since that's what the department mandates and you get an instantly configured dev environment for free. However, if you want the *pain* :) of manually installing all of the required libs, then this is how you should do it. The full step-by-step instructions for installation are [here](https://docs.google.com/document/d/149S_SHOzkJOhNHU4ENMU0YCbk-Vy92y5ZSTeCXG9Bhc/edit) (invite only for now).

## Requirements
* Python 3.51
* Pip 3
* Django 1.9
* ImageMagick
* ghostscript
* django_extensions (pip)
* Pillow (pip)
* Wand (pip)
* bibtex parser (pip)
* xmltodict (pip)
* django-image-cropping (pip)
* easy-thumbnails (pip)
* django-sortedm2m (pip)
* requests (pip)
* sqlite3 (for development)
* postgres (for production)
* gunicorn (for production)

Optional dependencies
* Virtual Env (for encapsulating the projects dependencies)

## Development
1. Install all dependencies. Pip dependencies can be installed using the requirements.txt file `pip install -r requirements.txt` from the project root, once the repository has been cloned.
2. Create the local database. On development we use sqlite. This can be done using `make migrate` if make is installed. Otherwise one must run `python manage.py makemigrations website && python manage.py migrate`
3. Create a super user using `python manage.py createsuperuser` to manage the admin interface.
4. The scripts `python manage.py importpubs` and `python manage.py importtalks` will import from bibtex and xml files located under the import directory respectively. These files are designed for use by the Makeability lab and will import from Jon Froehlich's website cs.umd.edu/~jonf
5. Add a file googleaccount.py in the website directory. This file should contain only the line ANALYTICS_ACCOUNT = 'your_google_analytics_email'. Replace your_google_analytics_email with whatever google account has been set up to track the domain in google analytics.
6. Follow the instructions [here](https://developers.google.com/analytics/devguides/reporting/core/v3/quickstart/service-py) to install google analytics api using pip, and to download the p12 private key from google analytics for authentication. This file should also go in the website directory along with the googleaccount.py file.
7. Run server using `python manage.py runserver`.

# Contributing
We use the following process for contributing code:
1. We use issues to organize tasks. You may choose to either select an existing issue to work on, or add your own. When adding issues, be sure to add tags as necessary. 
2. Assign yourself to an issue and create a branch off `master`. The name of your branch should be descriptive and based off the issue that you are working on. (EX: if you were fixing [this](https://github.com/jonfroehlich/makeabilitylabwebsite/issues/335) issue, an appropriate branch name would be `adding-hover-to-landing-page`). Each branch should address one issue.
3. When you are done working on an issue, submit a pull request. We will do local testing and code reviews before merging it with master.

## Things to keep in mind
Tasks that include changes to the user/admin interface should always include mockups. This is so we can collectively agree on how we want the site to look. A good example is [here](https://github.com/jonfroehlich/makeabilitylabwebsite/issues/287). Pull requests should also include before/after images, when applicable.

# Troubleshooting
## Bind for 0.0.0.0:8000 failed: port is already allocated
This means that there is already some process running at `0.0.0.0:8000`. First, make to close out of any windows that might be running a local server on your computer. If this error is still occuring, there might be a Docker container that is still running. 

To delete the container, do the following steps:
1. Run `docker ps -a`.
2. A table should be displayed. Look for the row that has `0.0.0.0:8000->8000/tcp` under the ports column. Copy the container name (under the `NAMES` column). 
3. Run `docker kill [NAME]`. (EX: `docker kill confident_tereshkova`). 

## Operational Error: Table/Column does not exist
WARNING: This method resets the database. 
1. Run `make dbshell` to enter an interactive terminal to view the current tables. In the interactive terminal, type `.tables` to display all tables that are listed in the database. (If the problem is that a column doesn't exist, type `.schema [table name]` to display the information about a specific table). If the table/column doesn't exist, continue.
2. Create a second docker container that mounts the database using `docker run -ti -v database:/database ubuntu`
3. Move the database. Type: `cd /database` then `mv db.sqlite3 db.sqlite3.backup`. Exit the interactive terminal.
4. Run `make dbshell`. Find the information for the table that is missing (either entirely or just a column) using `.schema [table name]`. Copy this information.

(You should copy something that might look something like this):
```
CREATE TABLE "website_talk_keywords" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "talk_id" integer NOT NULL REFERENCES "website_talk" ("id"), "keyword_id" integer NOT NULL REFERENCES "website_keyword" ("id"));
CREATE UNIQUE INDEX "website_talk_keywords_talk_id_fbb52519_uniq" ON "website_talk_keywords" ("talk_id", "keyword_id");
CREATE INDEX "website_talk_keywords_393ebc1b" ON "website_talk_keywords" ("talk_id");
CREATE INDEX "website_talk_keywords_5c003bba" ON "website_talk_keywords" ("keyword_id");
```
5. Move the copied database back into place using: `mv db.sqlite3.backup db.sqlite3`.
6. Recreate the database. Run `make shell`. In the interactive terminal, type `python manage.py`.
7. Rerun the website with `make run`.
