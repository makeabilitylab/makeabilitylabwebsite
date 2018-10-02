# This Dockerfile is based on:
#  1. https://docs.docker.com/compose/django/ (official Docker Django quickstart guide)
#
# To build this Dockerfile:
#   > docker build -t jonfroehlich/makelab_image .
# To run the image:
#   > docker run -p 8000:8000 jonfroehlich/makelab_image:latest
# To stop the server, try ctrl-C in terminal, otherwise:
#   > docker stop $(docker ps -aq) //this will stop all running containers

# All Dockerfiles must start with a 'FROM' instruction, which specifies a base image
# See: https://docs.docker.com/engine/reference/builder/#format
# Note, some online sources say that you should put FROM django here (e.g., https://runnable.com/docker/python/dockerize-your-django-application)
# but, in fact, you should NOT do this according to the official docs (as this approach has been deprecated). 
# See: https://hub.docker.com/_/django/
FROM python:3

# Setup some other prereqs needed:
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

# The ADD instruction copies new files, directories or remote file URLs from <src> and adds them to the
# filesystem of the image at the path <dest>.
# See: https://docs.docker.com/engine/reference/builder/#add
ADD requirements.txt /code/

# As an fyi: Layering RUN instructions and generating commits conforms to the core concepts 
# of Docker where commits are cheap and containers can be created from any point in an image’s history, much like source control.
# See: https://docs.docker.com/engine/reference/builder/#run
RUN pip install -r requirements.txt

# Add the current directory to /code/
ADD . /code/
ADD media /code/

##Our local user needs write access to a website and static files
RUN chown -R apache /code/

# The EXPOSE instruction informs Docker that the container listens on the specified network ports at runtime. 
# You can specify whether the port listens on TCP or UDP, and the default is TCP if the protocol is not specified.
# Note: The EXPOSE instruction does not actually publish the port. To actually publish the port when running the container, 
# use the -p flag on docker run to publish and map one or more ports
# See: https://docs.docker.com/engine/reference/builder/#expose
EXPOSE 8000

# The main purpose of a CMD is to provide defaults for an executing container. These defaults can include an 
# executable, or they can omit the executable, in which case you must specify an ENTRYPOINT instruction as well.
# Note: There can only be one CMD instruction in a Dockerfile. If you list more than one CMD then only the 
# last CMD will take effect.
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

#Run the process as our local user:
USER apache

COPY ./docker-entrypoint.sh /code/
ENTRYPOINT ["/code/docker-entrypoint.sh"]
