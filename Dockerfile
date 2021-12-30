# All Dockerfiles must start with a 'FROM' instruction, which specifies a base image
# See: https://docs.docker.com/engine/reference/builder/#format
# Note, some online sources say that you should put FROM django here (e.g., https://runnable.com/docker/python/dockerize-your-django-application)
# but, in fact, you should NOT do this according to the official docs (as this approach has been deprecated). 
# See: https://hub.docker.com/_/django/
FROM python:3.8

# Echo out the start of the Dockerfile
RUN echo "Running the Makeability Lab Dockerfile!"

# Sometimes we get warnings about old pip, so take care of that here
RUN pip install --upgrade pip 

# See: https://www.quora.com/How-does-one-install-pip-in-a-Docker-container-using-a-Dockerfile
RUN apt-get update && apt-get --assume-yes install imagemagick ghostscript sqlite3

# The ENV instruction sets the environment variable <key> to the <value> in ENV <key> <value>. 
# See: https://docs.docker.com/engine/reference/builder/#environment-replacement
# In this case, we are setting the stdout/stderr streams in Python to be unbuffered
ENV PYTHONUNBUFFERED 1

#Create a system user which we'll use later.
#We're using the 'apache' user since that's what we're trying to map
#outside the container -- it could be called anything, but apache is convenient
RUN useradd -u 48 apache
RUN groupmod -g 48 apache

# The RUN instruction will execute any commands in a new layer on top of the current image and commit the results. 
# The resulting committed image will be used for the next step in the Dockerfile.
# See: https://docs.docker.com/engine/reference/builder/#run
RUN mkdir /code

# The WORKDIR instruction sets the working directory for any RUN, CMD, ENTRYPOINT, COPY and ADD instructions 
# that follow it in the Dockerfile. If the WORKDIR doesn’t exist, it will be created even if it’s not used 
# in any subsequent Dockerfile instruction. 
# See: https://docs.docker.com/engine/reference/builder/#workdir
WORKDIR /code

# COPY the requirements.txt into the docker container
# As an fyi: Layering RUN instructions and generating commits conforms to the core concepts 
# of Docker where commits are cheap and containers can be created from any point in an image’s history, much like source control.
# See: https://docs.docker.com/engine/reference/builder/#run
COPY requirements.txt /code/
RUN pip3.8 install -r requirements.txt

## TEMP related to: https://github.com/jonfroehlich/makeabilitylabwebsite/issues/866
#RUN pip install django-ckeditor

# Our local user needs write access to a website and static files
RUN chown -R apache /code/

# Despite the above, still getting permission errors on WSL2
# -- PermissionError: [Errno 13] Permission denied: '/code/static'
# -- PermissionError: [Errno 13] Permission denied: '/code/website/migrations'
# RUN chown apache:apache -R /code/

COPY . /code/

# Copy over the new ImageMagick policy, see:
# https://github.com/makeabilitylab/makeabilitylabwebsite/issues/974
COPY imagemagick-policy.xml /etc/ImageMagick-6/policy.xml

# Run the process as our local user:
USER apache

COPY docker-entrypoint.sh docker-entrypoint.sh
CMD ["/code/docker-entrypoint.sh"] 
