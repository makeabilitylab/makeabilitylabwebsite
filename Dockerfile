# All Dockerfiles must start with a 'FROM' instruction, which specifies a base image
# See: https://docs.docker.com/engine/reference/builder/#format
#
# Note, some online sources say that you should put FROM django here (e.g., https://runnable.com/docker/python/dockerize-your-django-application)
# but, in fact, you should NOT do this according to the official docs (as this approach has been deprecated). 
# See: https://hub.docker.com/_/django/
# 
# So, instead, we start from an official Docker-created base image of Python.
FROM python:3.13.1

RUN echo "Building the Makeability Lab Docker image..."

# The ENV instruction sets environment variables.
# See: https://docs.docker.com/engine/reference/builder/#environment-replacement
#
# PYTHONUNBUFFERED=1: Ensures stdout/stderr streams are unbuffered for real-time logging
# PYTHONDONTWRITEBYTECODE=1: Prevents Python from writing .pyc bytecode files to 
#                            __pycache__ directories, keeping the container cleaner.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Upgrade pip to avoid version warnings during package installation
RUN pip install --upgrade pip 

# Install system dependencies required by the application:
# - imagemagick: Image processing for thumbnails and conversions
# - ghostscript: PDF processing (required by imagemagick for PDFs)
# - sqlite3: Useful for debugging, though we use PostgreSQL in production
#
# We clean up the apt cache afterward to reduce the final image size.
RUN apt-get update \
    && apt-get --assume-yes install --no-install-recommends \
        imagemagick \
        ghostscript \
        sqlite3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a system user for running the application.
# We use 'apache' with UID/GID 48 to match the user mapping on the UW production
# servers. The name is arbitrary but 'apache' is convenient for this purpose.
RUN useradd -u 48 apache && groupmod -g 48 apache

# The WORKDIR instruction sets the working directory for subsequent instructions.
# If the directory doesn't exist, it will be created automatically.
# See: https://docs.docker.com/engine/reference/builder/#workdir
WORKDIR /code

# Copy and install Python dependencies first, before copying the rest of the code.
# This leverages Docker's layer caching: if requirements.txt hasn't changed,
# Docker reuses the cached layer and skips the slow pip install step.
#
# The -r flag tells pip to install all packages listed in the requirements file.
# The --no-cache-dir flag prevents pip from caching downloaded packages,
# reducing the final image size.
# See: https://docs.docker.com/engine/reference/builder/#run
COPY requirements.txt /code/
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the application code into the container.
# This is done after pip install so code changes don't invalidate the
# dependency cache layer.
COPY . /code/

# Copy custom ImageMagick policy to allow PDF processing.
# See: https://github.com/makeabilitylab/makeabilitylabwebsite/issues/974
COPY imagemagick-policy.xml /etc/ImageMagick-6/policy.xml

# Set ownership so the apache user can write to necessary directories
# (static files, migrations, media uploads, etc.)
#
# Note: On WSL2, you may still encounter permission errors. If so, ensure
# you've run the chmod commands from CONTRIBUTING.md before building.
RUN chown -R apache:apache /code/

# Switch to non-root user for security.
# All subsequent commands (and the running container) will use this user.
USER apache

# Start the application via the entrypoint script, which handles
# migrations, static file collection, and starting the dev server.
CMD ["/code/docker-entrypoint.sh"]
